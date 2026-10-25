// SPDX-License-Identifier: GPL-2.0-only

#include <linux/delay.h>
#include <linux/dma-mapping.h>
#include <linux/jiffies.h>

#include "quantum.h"

struct quantum_tci_header {
	__le16 length;
	u8 channel;
	u8 code;
	__le16 transaction_id;
	__le16 reserved;
} __packed;

static_assert(sizeof(struct quantum_tci_header) == QUANTUM_TCI_HEADER_SIZE);

static void quantum_tci_free_slots(struct quantum_chip *chip)
{
	u32 i;

	for (i = 0; i < chip->tci_slot_count; i++) {
		if (chip->tci_tx_area[i]) {
			dma_free_coherent(&chip->pci->dev, chip->tci_slot_size,
					  chip->tci_tx_area[i], chip->tci_tx_dma[i]);
			chip->tci_tx_area[i] = NULL;
		}
		if (chip->tci_rx_area[i]) {
			dma_free_coherent(&chip->pci->dev, chip->tci_slot_size,
					  chip->tci_rx_area[i], chip->tci_rx_dma[i]);
			chip->tci_rx_area[i] = NULL;
		}
	}
	chip->tci_slot_count = 0;
	chip->tci_slot_size = 0;
}

static void quantum_tci_clear_registers(struct quantum_chip *chip)
{
	u32 i;

	if (!chip->iobase)
		return;

	writel(0, chip->iobase + QUANTUM_REG_TCI_TX_HOST_POS);
	writel(0, chip->iobase + QUANTUM_REG_TCI_RX_HOST_POS);
	for (i = 0; i < chip->tci_slot_count; i++) {
		writel(0, chip->iobase + QUANTUM_REG_TCI_TX_LENGTH(i));
		writel(0, chip->iobase + QUANTUM_REG_TCI_TX_ADDR_LO(i));
		writel(0, chip->iobase + QUANTUM_REG_TCI_TX_ADDR_HI(i));
		writel(0, chip->iobase + QUANTUM_REG_TCI_RX_ADDR_LO(i));
		writel(0, chip->iobase + QUANTUM_REG_TCI_RX_ADDR_HI(i));
	}

	/* Flush posted writes before coherent slot memory can be released. */
	readl(chip->iobase + QUANTUM_REG_TCI_CONTROL);
}

void quantum_tci_stop(struct quantum_chip *chip)
{
	u32 status;
	bool stopped = true;
	int retries;

	if (chip->tci_started && chip->iobase) {
		writel(0, chip->iobase + QUANTUM_REG_TCI_CONTROL);
		for (retries = 0; retries < 100; retries++) {
			status = readl(chip->iobase + QUANTUM_REG_TCI_STATUS);
			if (!(status & QUANTUM_TCI_STATUS_ACTIVE_MASK))
				break;
			usleep_range(1000, 2000);
		}
		if (retries == 100) {
			stopped = false;
			dev_warn(&chip->pci->dev,
				 "TCI DMA did not stop, status=0x%08x\n", status);
		}
	}
	chip->tci_started = false;
	if (!stopped)
		pci_clear_master(chip->pci);
	quantum_tci_clear_registers(chip);
	quantum_tci_free_slots(chip);
}

int quantum_tci_start(struct quantum_chip *chip)
{
	u32 config, count, size, i;

	config = readl(chip->iobase + QUANTUM_REG_TCI_CONFIG);
	count = config & 0xff;
	size = config >> 16;
	if (!count || count > QUANTUM_TCI_MAX_SLOTS ||
	    size < QUANTUM_TCI_HEADER_SIZE || size > PAGE_SIZE) {
		dev_err(&chip->pci->dev,
			"invalid TCI configuration 0x%08x (slots=%u size=%u)\n",
			config, count, size);
		return -EPROTO;
	}

	chip->tci_slot_count = count;
	chip->tci_slot_size = size;
	for (i = 0; i < count; i++) {
		chip->tci_tx_area[i] = dma_alloc_coherent(&chip->pci->dev, size,
							 &chip->tci_tx_dma[i], GFP_KERNEL);
		if (!chip->tci_tx_area[i])
			goto nomem;
		chip->tci_rx_area[i] = dma_alloc_coherent(&chip->pci->dev, size,
							 &chip->tci_rx_dma[i], GFP_KERNEL);
		if (!chip->tci_rx_area[i])
			goto nomem;

		memset(chip->tci_tx_area[i], 0, size);
		memset(chip->tci_rx_area[i], 0, size);
		writel(lower_32_bits(chip->tci_tx_dma[i]),
		       chip->iobase + QUANTUM_REG_TCI_TX_ADDR_LO(i));
		writel(upper_32_bits(chip->tci_tx_dma[i]),
		       chip->iobase + QUANTUM_REG_TCI_TX_ADDR_HI(i));
		writel(lower_32_bits(chip->tci_rx_dma[i]),
		       chip->iobase + QUANTUM_REG_TCI_RX_ADDR_LO(i));
		writel(upper_32_bits(chip->tci_rx_dma[i]),
		       chip->iobase + QUANTUM_REG_TCI_RX_ADDR_HI(i));
	}

	dma_wmb();
	writel(0, chip->iobase + QUANTUM_REG_TCI_TX_HOST_POS);
	writel(0, chip->iobase + QUANTUM_REG_TCI_RX_HOST_POS);
	writel(QUANTUM_TCI_CONTROL_ENABLE,
	       chip->iobase + QUANTUM_REG_TCI_CONTROL);
	chip->tci_next_transaction_id = 0;
	chip->tci_started = true;
	dev_info(&chip->pci->dev, "TCI mailbox started (%u slots, %u bytes each)\n",
		 count, size);
	return 0;

nomem:
	quantum_tci_clear_registers(chip);
	quantum_tci_free_slots(chip);
	return -ENOMEM;
}

static int quantum_tci_drain_stale_rx(struct quantum_chip *chip)
{
	struct quantum_tci_header *header;
	unsigned long deadline, quiet_deadline;
	u32 device_pos, host_pos, slot, next_pos, message_length;
	unsigned int drained = 0;

	deadline = jiffies + msecs_to_jiffies(QUANTUM_TCI_DRAIN_TIMEOUT_MS);
	quiet_deadline = jiffies +
			 msecs_to_jiffies(QUANTUM_TCI_DRAIN_QUIET_MS);
	for (;;) {
		device_pos = readl(chip->iobase + QUANTUM_REG_TCI_RX_DEVICE_POS);
		host_pos = readl(chip->iobase + QUANTUM_REG_TCI_RX_HOST_POS);
		if (device_pos != host_pos) {
			slot = host_pos % chip->tci_slot_count;
			next_pos = (slot + 1) % chip->tci_slot_count;
			message_length = readl(chip->iobase +
					       QUANTUM_REG_TCI_RX_LENGTH(slot));
			dma_rmb();
			header = chip->tci_rx_area[slot];
			if (message_length >= QUANTUM_TCI_HEADER_SIZE &&
			    message_length <= chip->tci_slot_size &&
			    le16_to_cpu(header->length) >= QUANTUM_TCI_HEADER_SIZE &&
			    le16_to_cpu(header->length) <= message_length)
				dev_info(&chip->pci->dev,
					 "TCI drained stale RX: channel=0x%02x code=0x%02x tid=%u\n",
					 header->channel, header->code,
					 le16_to_cpu(header->transaction_id));
			else
				dev_warn(&chip->pci->dev,
					 "TCI drained malformed stale RX slot %u len=%u\n",
					 slot, message_length);

			writel(QUANTUM_IRQ_TCI_RX,
			       chip->iobase + QUANTUM_REG_IRQ_STATUS);
			writel(next_pos, chip->iobase +
			       QUANTUM_REG_TCI_RX_HOST_POS);
			if (++drained > chip->tci_slot_count) {
				dev_err(&chip->pci->dev,
					"TCI stale RX drain exceeded one ring\n");
				return -EOVERFLOW;
			}
			quiet_deadline = jiffies +
				msecs_to_jiffies(QUANTUM_TCI_DRAIN_QUIET_MS);
			continue;
		}

		if (time_after_eq(jiffies, quiet_deadline)) {
			if (drained)
				dev_info(&chip->pci->dev,
					 "TCI stale RX drain completed: %u messages\n",
					 drained);
			return 0;
		}
		if (time_after_eq(jiffies, deadline)) {
			dev_err(&chip->pci->dev,
				"TCI stale RX drain did not reach a quiet interval\n");
			return -ETIMEDOUT;
		}
		usleep_range(1000, 2000);
	}
}

static int quantum_tci_control_xfer(struct quantum_chip *chip, u8 request_code,
				    const void *request, size_t request_length,
				    u8 response_code, void *response,
				    size_t *response_length)
{
	struct quantum_tci_header *header;
	unsigned long deadline;
	size_t response_capacity = *response_length;
	u32 device_pos, host_pos, slot, next_pos, message_length;
	u16 transaction_id;
	unsigned int skipped_messages = 0;
	int err = 0;

	if (!chip->tci_started)
		return -ENODEV;
	if (request_length > chip->tci_slot_size - QUANTUM_TCI_HEADER_SIZE)
		return -EMSGSIZE;

	mutex_lock(&chip->tci_lock);
	deadline = jiffies + msecs_to_jiffies(QUANTUM_TCI_TIMEOUT_MS);
	for (;;) {
		device_pos = readl(chip->iobase + QUANTUM_REG_TCI_TX_DEVICE_POS);
		host_pos = readl(chip->iobase + QUANTUM_REG_TCI_TX_HOST_POS);
		slot = host_pos % chip->tci_slot_count;
		next_pos = (slot + 1) % chip->tci_slot_count;
		if (next_pos != device_pos % chip->tci_slot_count)
			break;
		if (time_after_eq(jiffies, deadline)) {
			dev_err(&chip->pci->dev,
				"TCI request 0x%02x TX wait timed out: status=0x%08x tx=%u/%u rx=%u/%u\n",
				request_code,
				readl(chip->iobase + QUANTUM_REG_TCI_STATUS),
				device_pos, host_pos,
				readl(chip->iobase + QUANTUM_REG_TCI_RX_DEVICE_POS),
				readl(chip->iobase + QUANTUM_REG_TCI_RX_HOST_POS));
			err = -ETIMEDOUT;
			goto out_unlock;
		}
		usleep_range(1000, 2000);
	}

	header = chip->tci_tx_area[slot];
	memset(header, 0, chip->tci_slot_size);
	transaction_id = chip->tci_next_transaction_id++;
	header->length = cpu_to_le16(QUANTUM_TCI_HEADER_SIZE + request_length);
	header->channel = QUANTUM_TCI_CHANNEL_CONTROL;
	header->code = request_code;
	header->transaction_id = cpu_to_le16(transaction_id);
	if (request_length)
		memcpy(header + 1, request, request_length);

	dma_wmb();
	writel(QUANTUM_TCI_HEADER_SIZE + request_length,
	       chip->iobase + QUANTUM_REG_TCI_TX_LENGTH(slot));
	writel(next_pos, chip->iobase + QUANTUM_REG_TCI_TX_HOST_POS);

	deadline = jiffies + msecs_to_jiffies(QUANTUM_TCI_TIMEOUT_MS);
	for (;;) {
		device_pos = readl(chip->iobase + QUANTUM_REG_TCI_RX_DEVICE_POS);
		host_pos = readl(chip->iobase + QUANTUM_REG_TCI_RX_HOST_POS);
		if (device_pos != host_pos) {
			/* Probe polls before request_irq(), so acknowledge RX here. */
			writel(QUANTUM_IRQ_TCI_RX,
			       chip->iobase + QUANTUM_REG_IRQ_STATUS);
			slot = host_pos % chip->tci_slot_count;
			message_length = readl(chip->iobase +
					       QUANTUM_REG_TCI_RX_LENGTH(slot));
			dma_rmb();
			header = chip->tci_rx_area[slot];
			next_pos = (slot + 1) % chip->tci_slot_count;
			if (message_length < QUANTUM_TCI_HEADER_SIZE ||
			    message_length > chip->tci_slot_size ||
			    le16_to_cpu(header->length) < QUANTUM_TCI_HEADER_SIZE ||
			    le16_to_cpu(header->length) > message_length) {
				writel(next_pos, chip->iobase +
				       QUANTUM_REG_TCI_RX_HOST_POS);
				err = -EPROTO;
				goto out_unlock;
			}
			if (header->channel != QUANTUM_TCI_CHANNEL_CONTROL ||
			    le16_to_cpu(header->transaction_id) != transaction_id) {
				dev_info(&chip->pci->dev,
					 "TCI skipped RX while waiting for 0x%02x: channel=0x%02x code=0x%02x tid=%u expected_tid=%u\n",
					 request_code, header->channel, header->code,
					 le16_to_cpu(header->transaction_id),
					 transaction_id);
				writel(next_pos, chip->iobase +
				       QUANTUM_REG_TCI_RX_HOST_POS);
				if (++skipped_messages > chip->tci_slot_count) {
					dev_err(&chip->pci->dev,
						"TCI request 0x%02x exceeded stale RX drain bound\n",
						request_code);
					err = -EOVERFLOW;
					goto out_unlock;
				}
				deadline = jiffies +
					   msecs_to_jiffies(QUANTUM_TCI_TIMEOUT_MS);
				continue;
			}
			if (header->code != response_code) {
				writel(next_pos, chip->iobase +
				       QUANTUM_REG_TCI_RX_HOST_POS);
				dev_err(&chip->pci->dev,
					"TCI request 0x%02x returned code 0x%02x\n",
					request_code, header->code);
				err = -EPROTO;
				goto out_unlock;
			}

			message_length = le16_to_cpu(header->length) -
					 QUANTUM_TCI_HEADER_SIZE;
			if (message_length > response_capacity) {
				writel(next_pos, chip->iobase +
				       QUANTUM_REG_TCI_RX_HOST_POS);
				err = -EMSGSIZE;
				goto out_unlock;
			}
			if (message_length)
				memcpy(response, header + 1, message_length);
			*response_length = message_length;
			writel(next_pos, chip->iobase +
			       QUANTUM_REG_TCI_RX_HOST_POS);
			goto out_unlock;
		}

		if (time_after_eq(jiffies, deadline)) {
			dev_err(&chip->pci->dev,
				"TCI request 0x%02x RX wait timed out: status=0x%08x tx=%u/%u rx=%u/%u\n",
				request_code,
				readl(chip->iobase + QUANTUM_REG_TCI_STATUS),
				readl(chip->iobase + QUANTUM_REG_TCI_TX_DEVICE_POS),
				readl(chip->iobase + QUANTUM_REG_TCI_TX_HOST_POS),
				device_pos, host_pos);
			err = -ETIMEDOUT;
			goto out_unlock;
		}
		usleep_range(1000, 2000);
	}

out_unlock:
	mutex_unlock(&chip->tci_lock);
	return err;
}

static int quantum_tci_get_sample_rate(struct quantum_chip *chip,
				       u32 clock_source,
				       unsigned int *device_rate,
				       unsigned int *clock_rate)
{
	struct {
		__le32 device_rate;
		__le32 clock_rate;
	} __packed response;
	__le32 request = cpu_to_le32(clock_source);
	size_t response_length = sizeof(response);
	int err;

	err = quantum_tci_control_xfer(chip, QUANTUM_TCI_CTRL_GET_SAMPLE_RATE,
				       &request, sizeof(request),
				       QUANTUM_TCI_CTRL_RSP_SAMPLE_RATE,
				       &response, &response_length);
	if (err)
		return err;
	if (response_length != sizeof(response))
		return -EPROTO;

	*device_rate = quantum_tci_decode_sample_rate(
		le32_to_cpu(response.device_rate));
	*clock_rate = quantum_tci_decode_sample_rate(
		le32_to_cpu(response.clock_rate));
	if (!*device_rate)
		return -EPROTO;

	return 0;
}

int quantum_tci_set_sample_rate(
	struct quantum_chip *chip, const struct quantum_rate_profile *profile)
{
	struct {
		__le32 clock_source;
		__le32 sample_rate;
	} __packed request;
	__le32 response = 0;
	unsigned int clock_rate, device_rate;
	size_t response_length = sizeof(response);
	u32 channels;
	int err, retries;

	if (chip->audio_rate == profile->rate)
		return 0;
	if (chip->clock_source != QUANTUM_TCI_CLOCK_SOURCE_INTERNAL) {
		err = quantum_tci_get_sample_rate(chip, chip->clock_source,
						  &device_rate, &clock_rate);
		if (err)
			return err;
		if (clock_rate != profile->rate) {
			dev_err(&chip->pci->dev,
				"external clock is %u Hz, cannot select %u Hz\n",
				clock_rate, profile->rate);
			return -EINVAL;
		}
	}

	request.clock_source = cpu_to_le32(chip->clock_source);
	request.sample_rate = cpu_to_le32(profile->tci_value);
	err = quantum_tci_control_xfer(chip, QUANTUM_TCI_CTRL_SET_SAMPLE_RATE,
				       &request, sizeof(request),
				       QUANTUM_TCI_CTRL_RSP_STATUS,
				       &response, &response_length);
	if (err)
		return err;
	if (response_length != sizeof(response))
		return -EPROTO;
	if (le32_to_cpu(response)) {
		dev_err(&chip->pci->dev,
			"TCI sample-rate change to %u Hz failed: status=0x%08x\n",
			profile->rate, le32_to_cpu(response));
		return -EIO;
	}

	err = quantum_tci_get_sample_rate(chip, chip->clock_source,
					  &device_rate, &clock_rate);
	if (err)
		return err;
	if (device_rate != profile->rate || clock_rate != profile->rate) {
		dev_err(&chip->pci->dev,
			"TCI sample-rate verification failed: requested=%u clock=%u device=%u\n",
			profile->rate, clock_rate, device_rate);
		return -EIO;
	}

	for (retries = 0; retries < 100; retries++) {
		channels = readl(chip->iobase + QUANTUM_REG_AUDIO_CHANNELS);
		if ((channels & 0xff) == profile->channels &&
		    ((channels >> 8) & 0xff) == profile->channels)
			break;
		usleep_range(1000, 2000);
	}
	if (retries == 100) {
		dev_err(&chip->pci->dev,
			"sample-rate channel transition timed out: rate=%u channels=0x%08x\n",
			profile->rate, channels);
		return -ETIMEDOUT;
	}

	chip->audio_rate = profile->rate;
	chip->audio_channels = profile->channels;
	dev_info(&chip->pci->dev,
		 "TCI sample rate changed: rate=%u Hz channels=%u\n",
		 chip->audio_rate, chip->audio_channels);
	return 0;
}

int quantum_tci_probe_control(struct quantum_chip *chip)
{
	const struct quantum_rate_profile *profile;
	__le32 power_response = 0;
	__le32 clock_response = 0;
	size_t response_length;
	u32 channels, power, clock, clock_rate, device_rate;
	int err;

	err = quantum_tci_drain_stale_rx(chip);
	if (err)
		return err;

	response_length = sizeof(power_response);
	err = quantum_tci_control_xfer(chip, QUANTUM_TCI_CTRL_GET_POWER_STATE,
				       NULL, 0,
				       QUANTUM_TCI_CTRL_RSP_POWER_STATE,
				       &power_response, &response_length);
	if (err)
		return err;
	if (response_length != sizeof(power_response))
		return -EPROTO;
	power = le32_to_cpu(power_response);
	if (power > 1)
		return -EPROTO;

	response_length = sizeof(clock_response);
	err = quantum_tci_control_xfer(chip, QUANTUM_TCI_CTRL_GET_CLOCK_SOURCE,
				       NULL, 0,
				       QUANTUM_TCI_CTRL_RSP_CLOCK_SOURCE,
				       &clock_response, &response_length);
	if (err)
		return err;
	if (response_length != sizeof(clock_response))
		return -EPROTO;
	clock = le32_to_cpu(clock_response);

	err = quantum_tci_get_sample_rate(chip, clock, &device_rate,
					  &clock_rate);
	if (err)
		return err;
	profile = quantum_rate_profile_for_rate(device_rate);
	if (!profile)
		return -EPROTO;
	channels = readl(chip->iobase + QUANTUM_REG_AUDIO_CHANNELS);
	if ((channels & 0xff) != profile->channels ||
	    ((channels >> 8) & 0xff) != profile->channels) {
		dev_err(&chip->pci->dev,
			"rate/channel profile mismatch: rate=%u channels=0x%08x\n",
			device_rate, channels);
		return -EPROTO;
	}
	chip->clock_source = clock;
	chip->audio_rate = device_rate;
	chip->audio_channels = profile->channels;

	dev_info(&chip->pci->dev,
		 "TCI ready: power=%s clock_source=%u clock_rate=%u Hz device_rate=%u Hz channels=%u\n",
		 power ? "on" : "off", clock, clock_rate, device_rate,
		 chip->audio_channels);
	return 0;
}
