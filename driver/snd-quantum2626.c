// SPDX-License-Identifier: GPL-2.0-only
/*
 * Experimental ALSA PCI driver for PreSonus Quantum 2626.
 * PCI ID 1c67:0104.
 *
 * The TCI control mailbox is implemented from static analysis of the vendor's
 * macOS DriverKit extension. PCM rate and channel profiles follow the
 * statically recovered Quantum 2626 model table.
 *
 */

#include <linux/init.h>
#include <linux/interrupt.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/dma-mapping.h>
#include <linux/jiffies.h>
#include <linux/delay.h>
#include <linux/mutex.h>
#include <sound/core.h>
#include <sound/initval.h>
#include <sound/pcm.h>
#include <sound/pcm_params.h>

#define DRV_NAME "snd-quantum2626"
#define QUANTUM_NAMELONG "PreSonus Quantum 2626"

/* PreSonus PCI vendor ID (from driver-reference/pae_quantum.inf) */
#define PCI_VENDOR_ID_PRESONUS	0x1c67
#define PCI_DEVICE_ID_QUANTUM2626	0x0104

static int index[SNDRV_CARDS] = SNDRV_DEFAULT_IDX;
static char *id[SNDRV_CARDS] = SNDRV_DEFAULT_STR;
static bool enable[SNDRV_CARDS] = SNDRV_DEFAULT_ENABLE_PNP;

module_param_array(index, int, NULL, 0444);
MODULE_PARM_DESC(index, "Index value for PreSonus Quantum card.");
module_param_array(id, charp, NULL, 0444);
MODULE_PARM_DESC(id, "ID string for PreSonus Quantum card.");
module_param_array(enable, bool, NULL, 0444);
MODULE_PARM_DESC(enable, "Enable PreSonus Quantum card.");

/* Register access for reverse engineering */
static int reg_read_offset = -1;
module_param(reg_read_offset, int, 0644);
MODULE_PARM_DESC(reg_read_offset, "MMIO offset to read (hex, -1 to disable). Result in dmesg.");

static int reg_write_offset = -1;
module_param(reg_write_offset, int, 0644);
MODULE_PARM_DESC(reg_write_offset, "MMIO offset to write (hex, -1 to disable).");

static int reg_write_value;
module_param(reg_write_value, int, 0644);
MODULE_PARM_DESC(reg_write_value, "Value to write to reg_write_offset (hex).");

static bool reg_scan;
module_param(reg_scan, bool, 0644);
MODULE_PARM_DESC(reg_scan, "Scan and dump first 256 bytes of MMIO (0x00-0xff).");

MODULE_AUTHOR("Quantum2626 Linux driver project");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("Experimental PreSonus Quantum 2626 ALSA PCI driver");

/* Read-only identity/status registers. */
#define QUANTUM_REG_VERSION	0x0000	/* Version/ID register */
#define QUANTUM_REG_STATUS1	0x0004	/* Status/Control */
#define QUANTUM_REG_STATUS2	0x0008	/* Status/Control */
#define QUANTUM_REG_STATUS3	0x0010	/* Status/Control */
#define QUANTUM_REG_STATUS4	0x0014	/* Status/Control */
#define QUANTUM_REG_STATUS5	0x0104	/* Status/Control */
#define QUANTUM_REG_REC_ADDRS_PER_SEGMENT	0x10300
#define QUANTUM_REG_PLAY_ADDRS_PER_SEGMENT	0x10304

/* Audio DMA engine, established by static analysis of the macOS DEXT. */
#define QUANTUM_REG_AUDIO_STOP_STATUS	0x10000
#define QUANTUM_REG_AUDIO_POSITION	0x10104
#define QUANTUM_REG_AUDIO_CHANNELS	0x10200
#define QUANTUM_REG_AUDIO_PAGE_STATUS	0x10308
#define QUANTUM_REG_AUDIO_CONTROL	0x11000
#define QUANTUM_REG_REC_TABLE_LO	0x11100
#define QUANTUM_REG_REC_TABLE_HI	0x11104
#define QUANTUM_REG_REC_BUFFER_FRAMES	0x11108
#define QUANTUM_REG_REC_BLOCK_FRAMES	0x1110c
#define QUANTUM_REG_PLAY_TABLE_LO	0x11110
#define QUANTUM_REG_PLAY_TABLE_HI	0x11114
#define QUANTUM_REG_PLAY_BUFFER_FRAMES	0x11118
#define QUANTUM_REG_PLAY_BLOCK_FRAMES	0x1111c

#define QUANTUM_AUDIO_CONTROL_RUN	0x3
#define QUANTUM_AUDIO_STOPPED_MASK	0x3
#define QUANTUM_AUDIO_MIN_CHANNELS	8
#define QUANTUM_AUDIO_MAX_CHANNELS	26
#define QUANTUM_AUDIO_PERIOD_FRAMES	128
#define QUANTUM_AUDIO_MIN_PERIODS	2
#define QUANTUM_AUDIO_MAX_PERIODS	64
#define QUANTUM_AUDIO_BYTES_PER_SAMPLE	4
#define QUANTUM_AUDIO_MAX_BUFFER_BYTES \
	(QUANTUM_AUDIO_MAX_CHANNELS * QUANTUM_AUDIO_BYTES_PER_SAMPLE * \
	 QUANTUM_AUDIO_PERIOD_FRAMES * \
	 QUANTUM_AUDIO_MAX_PERIODS)
#define QUANTUM_STREAM_PLAYBACK	BIT(0)
#define QUANTUM_STREAM_CAPTURE	BIT(1)

/* TCI command mailbox, established by static analysis of the macOS DEXT. */
#define QUANTUM_REG_TCI_STATUS		0x0070
#define QUANTUM_REG_TCI_TX_DEVICE_POS	0x0074
#define QUANTUM_REG_TCI_RX_DEVICE_POS	0x0078
#define QUANTUM_REG_TCI_CONFIG		0x007c
#define QUANTUM_REG_TCI_RX_LENGTH(n)	(0x0080 + ((n) * 4))
#define QUANTUM_REG_TCI_CONTROL		0x1000
#define QUANTUM_REG_TCI_TX_HOST_POS	0x1004
#define QUANTUM_REG_TCI_RX_HOST_POS	0x1008
#define QUANTUM_REG_TCI_TX_ADDR_LO(n)	(0x1010 + ((n) * 8))
#define QUANTUM_REG_TCI_TX_ADDR_HI(n)	(0x1014 + ((n) * 8))
#define QUANTUM_REG_TCI_TX_LENGTH(n)	(0x1090 + ((n) * 4))
#define QUANTUM_REG_TCI_RX_ADDR_LO(n)	(0x10d0 + ((n) * 8))
#define QUANTUM_REG_TCI_RX_ADDR_HI(n)	(0x10d4 + ((n) * 8))

#define QUANTUM_REG_IRQ_STATUS		0x10004
#define QUANTUM_REG_IRQ_MASK		0x11004
#define QUANTUM_IRQ_AUDIO		BIT(8)
#define QUANTUM_IRQ_TCI_RX		BIT(31)

#define QUANTUM_TCI_CONTROL_ENABLE	0x101
#define QUANTUM_TCI_STATUS_ACTIVE_MASK	0x10001
#define QUANTUM_TCI_HEADER_SIZE		8
#define QUANTUM_TCI_MAX_SLOTS		16
#define QUANTUM_TCI_TIMEOUT_MS		250
#define QUANTUM_TCI_DRAIN_QUIET_MS	250
#define QUANTUM_TCI_DRAIN_TIMEOUT_MS	1000

#define QUANTUM_TCI_CHANNEL_CONTROL	0x31
#define QUANTUM_TCI_CTRL_GET_SAMPLE_RATE	0x31
#define QUANTUM_TCI_CTRL_SET_SAMPLE_RATE	0x32
#define QUANTUM_TCI_CTRL_RSP_SAMPLE_RATE	0x35
#define QUANTUM_TCI_CTRL_RSP_STATUS	0x01
#define QUANTUM_TCI_CTRL_GET_CLOCK_SOURCE 0x33
#define QUANTUM_TCI_CTRL_RSP_CLOCK_SOURCE 0x36
#define QUANTUM_TCI_CTRL_GET_POWER_STATE	0x3b
#define QUANTUM_TCI_CTRL_RSP_POWER_STATE	0x3c
#define QUANTUM_TCI_CLOCK_SOURCE_INTERNAL	1

struct quantum_tci_header {
	__le16 length;
	u8 channel;
	u8 code;
	__le16 transaction_id;
	__le16 reserved;
} __packed;

static_assert(sizeof(struct quantum_tci_header) == QUANTUM_TCI_HEADER_SIZE);

struct quantum_dma_table {
	void *area;
	dma_addr_t dma;
	size_t bytes;
};

struct quantum_chip {
	struct snd_card *card;
	struct pci_dev *pci;
	void __iomem *iobase;	/* BAR 0, 1 MiB from lspci */
	int irq;
	bool irq_requested;
	bool msi_allocated;	/* true if pci_alloc_irq_vectors(MSI) succeeded */
	/* TCI uses one coherent DMA buffer per hardware-owned ring slot. */
	struct mutex tci_lock;
	void *tci_tx_area[QUANTUM_TCI_MAX_SLOTS];
	dma_addr_t tci_tx_dma[QUANTUM_TCI_MAX_SLOTS];
	void *tci_rx_area[QUANTUM_TCI_MAX_SLOTS];
	dma_addr_t tci_rx_dma[QUANTUM_TCI_MAX_SLOTS];
	u32 tci_slot_count;
	u32 tci_slot_size;
	u16 tci_next_transaction_id;
	bool tci_started;
	u32 clock_source;
	unsigned int audio_rate;
	unsigned int audio_channels;
	struct snd_pcm *pcm;
	/* Serializes duplex parameter, prepare, and resource changes. */
	struct mutex audio_mutex;
	struct snd_pcm_substream *playback_params_substream;
	struct snd_pcm_substream *capture_params_substream;
	struct snd_pcm_substream *playback_substream;
	struct snd_pcm_substream *capture_substream;
	/* Protects IRQ-visible duplex engine state and substream pointers. */
	spinlock_t audio_lock;
	struct quantum_dma_table playback_table;
	struct quantum_dma_table capture_table;
	void *playback_silence_area;
	dma_addr_t playback_silence_dma;
	void *capture_sink_area;
	dma_addr_t capture_sink_dma;
	size_t audio_buffer_bytes;
	u32 audio_params;
	u32 audio_prepared;
	u32 audio_running;
	bool audio_engine_running;
	u32 irq_mask;
	u64 audio_irq_count;
	u32 audio_start_position;
	u32 audio_last_irq_position;
	u32 audio_last_irq_status;
};

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

static void quantum_tci_stop(struct quantum_chip *chip)
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

static int quantum_tci_start(struct quantum_chip *chip)
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

struct quantum_rate_profile {
	unsigned int rate;
	unsigned int channels;
	u32 tci_value;
};

static const struct quantum_rate_profile quantum_rate_profiles[] = {
	{ 44100,  26, 1 },
	{ 48000,  26, 2 },
	{ 88200,  18, 3 },
	{ 96000,  18, 4 },
	{ 176400,  8, 5 },
	{ 192000,  8, 6 },
};

static const struct quantum_rate_profile *
quantum_rate_profile_for_rate(unsigned int rate)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(quantum_rate_profiles); i++)
		if (quantum_rate_profiles[i].rate == rate)
			return &quantum_rate_profiles[i];

	return NULL;
}

static unsigned int quantum_tci_decode_sample_rate(u32 value)
{
	unsigned int i;

	for (i = 0; i < ARRAY_SIZE(quantum_rate_profiles); i++)
		if (quantum_rate_profiles[i].tci_value == value)
			return quantum_rate_profiles[i].rate;

	return 0;
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

static int quantum_tci_set_sample_rate(
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

static int quantum_tci_probe_control(struct quantum_chip *chip)
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

/* ----- Duplex ALSA and audio DMA page tables ----- */

static void quantum_dma_table_free(struct quantum_chip *chip,
				   struct quantum_dma_table *table)
{
	if (!table->area)
		return;

	dma_free_coherent(&chip->pci->dev, table->bytes, table->area,
			  table->dma);
	table->area = NULL;
	table->dma = 0;
	table->bytes = 0;
}

static void quantum_audio_clear_registers(struct quantum_chip *chip)
{
	if (!chip->iobase)
		return;

	writel(0, chip->iobase + QUANTUM_REG_AUDIO_CONTROL);
	writel(0, chip->iobase + QUANTUM_REG_PLAY_TABLE_LO);
	writel(0, chip->iobase + QUANTUM_REG_PLAY_TABLE_HI);
	writel(0, chip->iobase + QUANTUM_REG_PLAY_BUFFER_FRAMES);
	writel(0, chip->iobase + QUANTUM_REG_PLAY_BLOCK_FRAMES);
	writel(0, chip->iobase + QUANTUM_REG_REC_TABLE_LO);
	writel(0, chip->iobase + QUANTUM_REG_REC_TABLE_HI);
	writel(0, chip->iobase + QUANTUM_REG_REC_BUFFER_FRAMES);
	writel(0, chip->iobase + QUANTUM_REG_REC_BLOCK_FRAMES);

	/* Flush posted writes before coherent table memory can be released. */
	readl(chip->iobase + QUANTUM_REG_AUDIO_CONTROL);
}

static void quantum_audio_set_prepared(struct quantum_chip *chip, u32 prepared)
{
	unsigned long flags;

	spin_lock_irqsave(&chip->audio_lock, flags);
	chip->audio_prepared = prepared;
	spin_unlock_irqrestore(&chip->audio_lock, flags);
}

static void quantum_audio_free_resources(struct quantum_chip *chip)
{
	quantum_audio_clear_registers(chip);
	quantum_dma_table_free(chip, &chip->capture_table);
	quantum_dma_table_free(chip, &chip->playback_table);
	if (chip->playback_silence_area) {
		dma_free_coherent(&chip->pci->dev, chip->audio_buffer_bytes,
				  chip->playback_silence_area,
				  chip->playback_silence_dma);
		chip->playback_silence_area = NULL;
		chip->playback_silence_dma = 0;
	}
	if (chip->capture_sink_area) {
		dma_free_coherent(&chip->pci->dev, chip->audio_buffer_bytes,
				  chip->capture_sink_area,
				  chip->capture_sink_dma);
		chip->capture_sink_area = NULL;
		chip->capture_sink_dma = 0;
	}
	chip->audio_buffer_bytes = 0;
	quantum_audio_set_prepared(chip, 0);
}

static int quantum_dma_table_build(struct quantum_chip *chip,
				   struct quantum_dma_table *table,
				   dma_addr_t buffer_dma, size_t buffer_bytes,
				   u32 addresses_per_segment)
{
	unsigned int pages, segments, segment, page = 0;

	if (!addresses_per_segment || addresses_per_segment >= PAGE_SIZE / sizeof(__le64))
		return -EPROTO;
	if (!IS_ALIGNED(buffer_dma, PAGE_SIZE)) {
		dev_err(&chip->pci->dev, "audio DMA buffer is not page aligned: %pad\n",
			&buffer_dma);
		return -EINVAL;
	}

	pages = DIV_ROUND_UP(buffer_bytes, PAGE_SIZE);
	segments = DIV_ROUND_UP(pages, addresses_per_segment);
	table->bytes = segments * PAGE_SIZE;
	table->area = dma_alloc_coherent(&chip->pci->dev, table->bytes,
					 &table->dma, GFP_KERNEL);
	if (!table->area)
		return -ENOMEM;
	if (!IS_ALIGNED(table->dma, PAGE_SIZE)) {
		dev_err(&chip->pci->dev, "audio DMA table is not page aligned: %pad\n",
			&table->dma);
		quantum_dma_table_free(chip, table);
		return -EINVAL;
	}

	memset(table->area, 0, table->bytes);
	for (segment = 0; segment < segments; segment++) {
		__le64 *entries = table->area + segment * PAGE_SIZE;
		unsigned int entry;

		for (entry = 0;
		     entry < addresses_per_segment && page < pages;
		     entry++, page++)
			entries[entry] = cpu_to_le64((buffer_dma +
							 page * PAGE_SIZE) | 1ULL);

		if (segment + 1 < segments)
			entries[entry] = cpu_to_le64((table->dma +
							 (segment + 1) * PAGE_SIZE) | 1ULL);
	}

	return 0;
}

static int quantum_audio_stop(struct quantum_chip *chip)
{
	unsigned long flags;
	u32 irq_position, irq_status, position, status = 0;
	u64 irq_count;
	bool was_running;
	int retries;

	spin_lock_irqsave(&chip->audio_lock, flags);
	was_running = chip->audio_engine_running;
	chip->irq_mask &= ~QUANTUM_IRQ_AUDIO;
	writel(chip->irq_mask, chip->iobase + QUANTUM_REG_IRQ_MASK);
	spin_unlock_irqrestore(&chip->audio_lock, flags);
	if (!was_running)
		return 0;

	writel(0, chip->iobase + QUANTUM_REG_AUDIO_CONTROL);
	for (retries = 0; retries < 100; retries++) {
		status = readl(chip->iobase + QUANTUM_REG_AUDIO_STOP_STATUS);
		if (!(status & QUANTUM_AUDIO_STOPPED_MASK))
			break;
		udelay(10);
	}

	spin_lock_irqsave(&chip->audio_lock, flags);
	chip->audio_engine_running = false;
	chip->audio_running = 0;
	chip->playback_substream = NULL;
	chip->capture_substream = NULL;
	irq_count = chip->audio_irq_count;
	irq_position = chip->audio_last_irq_position;
	irq_status = chip->audio_last_irq_status;
	spin_unlock_irqrestore(&chip->audio_lock, flags);
	position = readl(chip->iobase + QUANTUM_REG_AUDIO_POSITION);
	if (retries == 100) {
		dev_err(&chip->pci->dev,
			"audio DMA did not stop, status=0x%08x; disabling bus mastering\n",
			status);
		pci_clear_master(chip->pci);
		return -ETIMEDOUT;
	}
	dev_info(&chip->pci->dev,
		 "audio DMA stopped: interrupts=%llu irq_status=0x%08x position=0x%08x->0x%08x->0x%08x\n",
		 irq_count, irq_status, chip->audio_start_position,
		 irq_position, position);

	return 0;
}

static int quantum_audio_wait_page_tables(struct quantum_chip *chip)
{
	u32 status = 0;
	int retries;

	for (retries = 0; retries < 100; retries++) {
		status = readl(chip->iobase + QUANTUM_REG_AUDIO_PAGE_STATUS);
		if ((status & 0xff) && (status & 0xff00))
			return 0;
		usleep_range(1000, 2000);
	}

	dev_err(&chip->pci->dev,
		"audio DMA page-table fetch timed out, status=0x%08x\n", status);
	return -ETIMEDOUT;
}

static int quantum_audio_program_resources(struct quantum_chip *chip)
{
	u32 buffer_frames;
	int err;

	if (!chip->capture_table.area || !chip->playback_table.area ||
	    !chip->audio_channels)
		return -EINVAL;
	buffer_frames = chip->audio_buffer_bytes /
		(chip->audio_channels * QUANTUM_AUDIO_BYTES_PER_SAMPLE);
	if (!buffer_frames || buffer_frames > GENMASK(19, 0))
		return -EINVAL;

	quantum_audio_set_prepared(chip, 0);
	dma_wmb();

	/* Match the DEXT: stop, program playback first, then record. */
	writel(0, chip->iobase + QUANTUM_REG_AUDIO_CONTROL);
	writel(buffer_frames,
	       chip->iobase + QUANTUM_REG_PLAY_BUFFER_FRAMES);
	writel(QUANTUM_AUDIO_PERIOD_FRAMES,
	       chip->iobase + QUANTUM_REG_PLAY_BLOCK_FRAMES);
	writel(upper_32_bits(chip->playback_table.dma),
	       chip->iobase + QUANTUM_REG_PLAY_TABLE_HI);
	writel(lower_32_bits(chip->playback_table.dma),
	       chip->iobase + QUANTUM_REG_PLAY_TABLE_LO);

	writel(buffer_frames,
	       chip->iobase + QUANTUM_REG_REC_BUFFER_FRAMES);
	writel(QUANTUM_AUDIO_PERIOD_FRAMES,
	       chip->iobase + QUANTUM_REG_REC_BLOCK_FRAMES);
	writel(upper_32_bits(chip->capture_table.dma),
	       chip->iobase + QUANTUM_REG_REC_TABLE_HI);
	writel(lower_32_bits(chip->capture_table.dma),
	       chip->iobase + QUANTUM_REG_REC_TABLE_LO);

	err = quantum_audio_wait_page_tables(chip);
	if (err)
		return err;
	quantum_audio_set_prepared(chip, chip->audio_params);
	dev_info(&chip->pci->dev,
		 "audio DMA prepared: directions=0x%x bytes=%zu buffer_frames=%u block_frames=%u page_status=0x%08x\n",
		 chip->audio_params, chip->audio_buffer_bytes, buffer_frames,
		 QUANTUM_AUDIO_PERIOD_FRAMES,
		 readl(chip->iobase + QUANTUM_REG_AUDIO_PAGE_STATUS));

	return 0;
}

static void quantum_audio_snapshot_running(
	struct quantum_chip *chip, u32 *running,
	struct snd_pcm_substream **playback,
	struct snd_pcm_substream **capture)
{
	unsigned long flags;

	spin_lock_irqsave(&chip->audio_lock, flags);
	*running = chip->audio_running;
	*playback = chip->playback_substream;
	*capture = chip->capture_substream;
	spin_unlock_irqrestore(&chip->audio_lock, flags);
}

static int quantum_audio_restore_running(
	struct quantum_chip *chip, u32 running,
	struct snd_pcm_substream *playback,
	struct snd_pcm_substream *capture)
{
	unsigned long flags;
	u32 start_position;

	if (!running)
		return 0;
	if ((READ_ONCE(chip->audio_prepared) & running) != running)
		return -EIO;

	start_position = readl(chip->iobase + QUANTUM_REG_AUDIO_POSITION);
	spin_lock_irqsave(&chip->audio_lock, flags);
	chip->playback_substream = playback;
	chip->capture_substream = capture;
	chip->audio_running = running;
	chip->audio_engine_running = true;
	chip->audio_start_position = start_position;
	chip->audio_irq_count = 0;
	chip->audio_last_irq_position = start_position;
	chip->audio_last_irq_status = 0;
	spin_unlock_irqrestore(&chip->audio_lock, flags);

	dma_wmb();
	writel(QUANTUM_IRQ_AUDIO, chip->iobase + QUANTUM_REG_IRQ_STATUS);
	spin_lock_irqsave(&chip->audio_lock, flags);
	chip->irq_mask |= QUANTUM_IRQ_AUDIO;
	writel(chip->irq_mask, chip->iobase + QUANTUM_REG_IRQ_MASK);
	spin_unlock_irqrestore(&chip->audio_lock, flags);
	writel(QUANTUM_AUDIO_CONTROL_RUN,
	       chip->iobase + QUANTUM_REG_AUDIO_CONTROL);
	dev_info(&chip->pci->dev,
		 "audio DMA resumed after duplex reconfiguration: directions=0x%x\n",
		 running);

	return 0;
}

static const struct snd_pcm_hardware quantum_pcm_hw = {
	.info = SNDRV_PCM_INFO_MMAP |
		SNDRV_PCM_INFO_MMAP_VALID |
		SNDRV_PCM_INFO_INTERLEAVED |
		SNDRV_PCM_INFO_BLOCK_TRANSFER |
		SNDRV_PCM_INFO_JOINT_DUPLEX,
	.formats = SNDRV_PCM_FMTBIT_S32_LE,
	.rates = SNDRV_PCM_RATE_44100 |
		 SNDRV_PCM_RATE_48000 |
		 SNDRV_PCM_RATE_88200 |
		 SNDRV_PCM_RATE_96000 |
		 SNDRV_PCM_RATE_176400 |
		 SNDRV_PCM_RATE_192000,
	.rate_min = 44100,
	.rate_max = 192000,
	.channels_min = QUANTUM_AUDIO_MIN_CHANNELS,
	.channels_max = QUANTUM_AUDIO_MAX_CHANNELS,
	.buffer_bytes_max = QUANTUM_AUDIO_MAX_BUFFER_BYTES,
	.period_bytes_min = QUANTUM_AUDIO_MIN_CHANNELS *
		QUANTUM_AUDIO_BYTES_PER_SAMPLE * QUANTUM_AUDIO_PERIOD_FRAMES,
	.period_bytes_max = QUANTUM_AUDIO_MAX_CHANNELS *
		QUANTUM_AUDIO_BYTES_PER_SAMPLE * QUANTUM_AUDIO_PERIOD_FRAMES,
	.periods_min = QUANTUM_AUDIO_MIN_PERIODS,
	.periods_max = QUANTUM_AUDIO_MAX_PERIODS,
};

static const unsigned int quantum_rates[] = {
	44100, 48000, 88200, 96000, 176400, 192000,
};

static const struct snd_pcm_hw_constraint_list quantum_rate_constraints = {
	.count = ARRAY_SIZE(quantum_rates),
	.list = quantum_rates,
};

static const unsigned int quantum_channel_counts[] = { 8, 18, 26 };

static const struct snd_pcm_hw_constraint_list quantum_channel_constraints = {
	.count = ARRAY_SIZE(quantum_channel_counts),
	.list = quantum_channel_counts,
};

static int quantum_pcm_channels_for_rate_rule(struct snd_pcm_hw_params *params,
					      struct snd_pcm_hw_rule *rule)
{
	const struct snd_interval *rate =
		hw_param_interval_c(params, SNDRV_PCM_HW_PARAM_RATE);
	struct snd_interval allowed = {
		.min = UINT_MAX,
		.max = 0,
		.integer = 1,
	};
	unsigned int i;

	(void)rule;
	for (i = 0; i < ARRAY_SIZE(quantum_rate_profiles); i++) {
		if (!snd_interval_test(rate, quantum_rate_profiles[i].rate))
			continue;
		allowed.min = min(allowed.min,
				  quantum_rate_profiles[i].channels);
		allowed.max = max(allowed.max,
				  quantum_rate_profiles[i].channels);
	}
	if (!allowed.max)
		return -EINVAL;

	return snd_interval_refine(
		hw_param_interval(params, SNDRV_PCM_HW_PARAM_CHANNELS), &allowed);
}

static int quantum_pcm_rates_for_channels_rule(struct snd_pcm_hw_params *params,
					       struct snd_pcm_hw_rule *rule)
{
	const struct snd_interval *channels =
		hw_param_interval_c(params, SNDRV_PCM_HW_PARAM_CHANNELS);
	struct snd_interval allowed = {
		.min = UINT_MAX,
		.max = 0,
		.integer = 1,
	};
	unsigned int i;

	(void)rule;
	for (i = 0; i < ARRAY_SIZE(quantum_rate_profiles); i++) {
		if (!snd_interval_test(channels,
				       quantum_rate_profiles[i].channels))
			continue;
		allowed.min = min(allowed.min, quantum_rate_profiles[i].rate);
		allowed.max = max(allowed.max, quantum_rate_profiles[i].rate);
	}
	if (!allowed.max)
		return -EINVAL;

	return snd_interval_refine(
		hw_param_interval(params, SNDRV_PCM_HW_PARAM_RATE), &allowed);
}

static u32 quantum_stream_mask(const struct snd_pcm_substream *substream)
{
	return substream->stream == SNDRV_PCM_STREAM_PLAYBACK ?
		QUANTUM_STREAM_PLAYBACK : QUANTUM_STREAM_CAPTURE;
}

static int quantum_pcm_open(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	u32 channels = readl(chip->iobase + QUANTUM_REG_AUDIO_CHANNELS);
	int err;

	if ((channels & 0xff) != chip->audio_channels ||
	    ((channels >> 8) & 0xff) != chip->audio_channels)
		return -ENODEV;

	substream->runtime->hw = quantum_pcm_hw;
	err = snd_pcm_hw_constraint_list(substream->runtime, 0,
					 SNDRV_PCM_HW_PARAM_RATE,
					 &quantum_rate_constraints);
	if (err)
		return err;
	err = snd_pcm_hw_constraint_list(substream->runtime, 0,
					 SNDRV_PCM_HW_PARAM_CHANNELS,
					 &quantum_channel_constraints);
	if (err)
		return err;
	err = snd_pcm_hw_constraint_integer(substream->runtime,
					    SNDRV_PCM_HW_PARAM_PERIODS);
	if (err)
		return err;
	err = snd_pcm_hw_rule_add(substream->runtime, 0,
				  SNDRV_PCM_HW_PARAM_CHANNELS,
				  quantum_pcm_channels_for_rate_rule, NULL,
				  SNDRV_PCM_HW_PARAM_RATE, -1);
	if (err)
		return err;

	return snd_pcm_hw_rule_add(substream->runtime, 0,
				   SNDRV_PCM_HW_PARAM_RATE,
				   quantum_pcm_rates_for_channels_rule, NULL,
				   SNDRV_PCM_HW_PARAM_CHANNELS, -1);
}

static int quantum_pcm_close(struct snd_pcm_substream *substream)
{
	return 0;
}

static int quantum_audio_build_resources(struct quantum_chip *chip, size_t bytes)
{
	dma_addr_t playback_dma, capture_dma;
	u32 capture_addresses, playback_addresses;
	int err;

	quantum_audio_free_resources(chip);
	chip->audio_buffer_bytes = bytes;

	if (chip->audio_params & QUANTUM_STREAM_PLAYBACK) {
		playback_dma = chip->playback_params_substream->runtime->dma_addr;
	} else {
		chip->playback_silence_area =
			dma_alloc_coherent(&chip->pci->dev, bytes,
					   &chip->playback_silence_dma,
					   GFP_KERNEL);
		if (!chip->playback_silence_area) {
			err = -ENOMEM;
			goto fail;
		}
		memset(chip->playback_silence_area, 0, bytes);
		playback_dma = chip->playback_silence_dma;
	}

	if (chip->audio_params & QUANTUM_STREAM_CAPTURE) {
		capture_dma = chip->capture_params_substream->runtime->dma_addr;
	} else {
		chip->capture_sink_area =
			dma_alloc_coherent(&chip->pci->dev, bytes,
					   &chip->capture_sink_dma, GFP_KERNEL);
		if (!chip->capture_sink_area) {
			err = -ENOMEM;
			goto fail;
		}
		memset(chip->capture_sink_area, 0, bytes);
		capture_dma = chip->capture_sink_dma;
	}

	dma_wmb();
	capture_addresses = readl(chip->iobase +
				  QUANTUM_REG_REC_ADDRS_PER_SEGMENT);
	playback_addresses = readl(chip->iobase +
				   QUANTUM_REG_PLAY_ADDRS_PER_SEGMENT);
	err = quantum_dma_table_build(chip, &chip->capture_table,
				      capture_dma, bytes, capture_addresses);
	if (err)
		goto fail;
	err = quantum_dma_table_build(chip, &chip->playback_table,
				      playback_dma, bytes, playback_addresses);
	if (err)
		goto fail;

	return 0;

fail:
	quantum_audio_free_resources(chip);
	return err;
}

static int quantum_pcm_hw_params(struct snd_pcm_substream *substream,
				 struct snd_pcm_hw_params *params)
{
	const struct quantum_rate_profile *profile =
		quantum_rate_profile_for_rate(params_rate(params));
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	struct snd_pcm_substream **params_substream;
	struct snd_pcm_substream *other, *running_playback, *running_capture;
	size_t bytes = params_buffer_bytes(params);
	u32 mask = quantum_stream_mask(substream), running;
	bool changing_rate;
	int err;

	if (!profile || params_channels(params) != profile->channels ||
	    params_format(params) != SNDRV_PCM_FORMAT_S32_LE ||
	    params_period_size(params) != QUANTUM_AUDIO_PERIOD_FRAMES)
		return -EINVAL;

	mutex_lock(&chip->audio_mutex);
	other = mask == QUANTUM_STREAM_PLAYBACK ?
		chip->capture_params_substream : chip->playback_params_substream;
	if (other &&
	    (other->runtime->rate != params_rate(params) ||
	     other->runtime->channels != params_channels(params) ||
	     other->runtime->period_size != params_period_size(params) ||
	     other->runtime->buffer_size != params_buffer_size(params))) {
		err = -EINVAL;
		goto unlock;
	}
	quantum_audio_snapshot_running(chip, &running, &running_playback,
				       &running_capture);
	changing_rate = chip->audio_rate != profile->rate;
	if (changing_rate && running) {
		err = -EBUSY;
		goto unlock;
	}
	if (running) {
		err = quantum_audio_stop(chip);
		if (err)
			goto unlock;
		if (chip->irq_requested)
			synchronize_irq(chip->irq);
	}
	if (changing_rate) {
		/* Match the vendor sequence: no live DMA resources during a switch. */
		quantum_audio_free_resources(chip);
		err = quantum_tci_set_sample_rate(chip, profile);
		if (err)
			goto unlock;
	}

	params_substream = mask == QUANTUM_STREAM_PLAYBACK ?
		&chip->playback_params_substream : &chip->capture_params_substream;
	*params_substream = substream;
	chip->audio_params |= mask;
	quantum_audio_set_prepared(chip, 0);
	err = quantum_audio_build_resources(chip, bytes);
	if (err) {
		chip->audio_params &= ~mask;
		*params_substream = NULL;
		goto unlock;
	}
	if (running) {
		/* The joint engine reads playback even before that stream starts. */
		if (mask == QUANTUM_STREAM_PLAYBACK)
			memset(substream->runtime->dma_area, 0, bytes);
		err = quantum_audio_program_resources(chip);
		if (!err)
			err = quantum_audio_restore_running(chip, running,
							    running_playback,
							    running_capture);
	}

unlock:
	mutex_unlock(&chip->audio_mutex);
	return err;
}

static int quantum_pcm_hw_free(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	struct snd_pcm_substream **params_substream;
	struct snd_pcm_substream *running_playback, *running_capture;
	u32 mask = quantum_stream_mask(substream), running;
	size_t remaining_bytes = 0;
	int err = 0;

	mutex_lock(&chip->audio_mutex);
	quantum_audio_snapshot_running(chip, &running, &running_playback,
				       &running_capture);
	if (running & mask) {
		err = -EBUSY;
		goto unlock;
	}
	if (running) {
		err = quantum_audio_stop(chip);
		if (err)
			goto unlock;
	}
	if (chip->irq_requested)
		synchronize_irq(chip->irq);
	params_substream = mask == QUANTUM_STREAM_PLAYBACK ?
		&chip->playback_params_substream : &chip->capture_params_substream;
	*params_substream = NULL;
	chip->audio_params &= ~mask;
	quantum_audio_free_resources(chip);
	if (chip->audio_params) {
		struct snd_pcm_substream *remaining =
			chip->playback_params_substream ?:
			chip->capture_params_substream;

		remaining_bytes = frames_to_bytes(remaining->runtime,
						  remaining->runtime->buffer_size);
		err = quantum_audio_build_resources(chip, remaining_bytes);
		if (!err && running) {
			err = quantum_audio_program_resources(chip);
			if (!err)
				err = quantum_audio_restore_running(
					chip, running, running_playback,
					running_capture);
		}
	}

unlock:
	mutex_unlock(&chip->audio_mutex);
	return err;
}

static int quantum_pcm_prepare(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	u32 mask = quantum_stream_mask(substream);
	int err;

	mutex_lock(&chip->audio_mutex);
	if (!(chip->audio_params & mask) || !chip->capture_table.area ||
	    !chip->playback_table.area ||
	    substream->runtime->dma_bytes < chip->audio_buffer_bytes) {
		err = -EINVAL;
		goto unlock;
	}
	if (READ_ONCE(chip->audio_engine_running)) {
		err = (READ_ONCE(chip->audio_prepared) & mask) ? 0 : -EBUSY;
		goto unlock;
	}
	quantum_audio_set_prepared(chip, 0);
	memset(substream->runtime->dma_area, 0, chip->audio_buffer_bytes);
	if (chip->playback_silence_area)
		memset(chip->playback_silence_area, 0,
		       chip->audio_buffer_bytes);
	if (chip->capture_sink_area)
		memset(chip->capture_sink_area, 0, chip->audio_buffer_bytes);
	err = quantum_audio_program_resources(chip);

unlock:
	mutex_unlock(&chip->audio_mutex);
	return err;
}

static int quantum_pcm_trigger(struct snd_pcm_substream *substream, int cmd)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	u32 mask = quantum_stream_mask(substream), running, start_position;
	unsigned long flags;
	bool first, last;

	switch (cmd) {
	case SNDRV_PCM_TRIGGER_START:
		start_position = readl(chip->iobase +
					       QUANTUM_REG_AUDIO_POSITION);
		spin_lock_irqsave(&chip->audio_lock, flags);
		if (!(chip->audio_prepared & mask)) {
			spin_unlock_irqrestore(&chip->audio_lock, flags);
			return -EIO;
		}
		first = !chip->audio_engine_running;
		if (mask == QUANTUM_STREAM_PLAYBACK)
			chip->playback_substream = substream;
		else
			chip->capture_substream = substream;
		chip->audio_running |= mask;
		chip->audio_engine_running = true;
		running = chip->audio_running;
		if (first) {
			chip->audio_start_position = start_position;
			chip->audio_irq_count = 0;
			chip->audio_last_irq_position = chip->audio_start_position;
			chip->audio_last_irq_status = 0;
		}
		spin_unlock_irqrestore(&chip->audio_lock, flags);
		if (!first)
			return 0;
		dma_wmb();
		writel(QUANTUM_IRQ_AUDIO,
		       chip->iobase + QUANTUM_REG_IRQ_STATUS);
		spin_lock_irqsave(&chip->audio_lock, flags);
		chip->irq_mask |= QUANTUM_IRQ_AUDIO;
		writel(chip->irq_mask, chip->iobase + QUANTUM_REG_IRQ_MASK);
		spin_unlock_irqrestore(&chip->audio_lock, flags);
		writel(QUANTUM_AUDIO_CONTROL_RUN,
		       chip->iobase + QUANTUM_REG_AUDIO_CONTROL);
		dev_info(&chip->pci->dev,
			 "audio DMA started: directions=0x%x\n", running);
		return 0;
	case SNDRV_PCM_TRIGGER_STOP:
	case SNDRV_PCM_TRIGGER_SUSPEND:
		spin_lock_irqsave(&chip->audio_lock, flags);
		chip->audio_running &= ~mask;
		if (mask == QUANTUM_STREAM_PLAYBACK)
			chip->playback_substream = NULL;
		else
			chip->capture_substream = NULL;
		last = chip->audio_engine_running && !chip->audio_running;
		spin_unlock_irqrestore(&chip->audio_lock, flags);
		return last ? quantum_audio_stop(chip) : 0;
	default:
		return -EINVAL;
	}
}

static snd_pcm_uframes_t quantum_pcm_pointer(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	u32 position = readl(chip->iobase + QUANTUM_REG_AUDIO_POSITION);

	return (position & GENMASK(19, 0)) % substream->runtime->buffer_size;
}

static const struct snd_pcm_ops quantum_pcm_ops = {
	.open = quantum_pcm_open,
	.close = quantum_pcm_close,
	.ioctl = snd_pcm_lib_ioctl,
	.hw_params = quantum_pcm_hw_params,
	.hw_free = quantum_pcm_hw_free,
	.prepare = quantum_pcm_prepare,
	.trigger = quantum_pcm_trigger,
	.pointer = quantum_pcm_pointer,
};

static int snd_quantum_pcm_new(struct quantum_chip *chip)
{
	int err;

	err = snd_pcm_new(chip->card, QUANTUM_NAMELONG, 0, 1, 1, &chip->pcm);
	if (err < 0)
		return err;
	chip->pcm->private_data = chip;
	strscpy(chip->pcm->name, QUANTUM_NAMELONG, sizeof(chip->pcm->name));
	snd_pcm_set_ops(chip->pcm, SNDRV_PCM_STREAM_PLAYBACK,
			&quantum_pcm_ops);
	snd_pcm_set_ops(chip->pcm, SNDRV_PCM_STREAM_CAPTURE, &quantum_pcm_ops);

	return snd_pcm_set_managed_buffer_all(chip->pcm, SNDRV_DMA_TYPE_DEV,
					      &chip->pci->dev,
					      0,
					      QUANTUM_AUDIO_MAX_BUFFER_BYTES);
}

/* ----- Resource release ----- */

static void snd_quantum_free(struct snd_card *card)
{
	struct quantum_chip *chip = card->private_data;

	quantum_audio_stop(chip);
	if (chip->irq_requested && chip->irq >= 0) {
		free_irq(chip->irq, chip);
		chip->irq_requested = false;
	}
	quantum_audio_free_resources(chip);
	if (chip->msi_allocated)
		pci_free_irq_vectors(chip->pci);
	quantum_tci_stop(chip);
	if (chip->iobase)
		pci_iounmap(chip->pci, chip->iobase);
	pci_clear_master(chip->pci);
	pci_release_regions(chip->pci);
	pci_disable_device(chip->pci);
}

/* ----- Interrupt: signal period elapsed for active substreams ----- */

static irqreturn_t snd_quantum_interrupt(int irq, void *dev_id)
{
	struct quantum_chip *chip = dev_id;
	struct snd_pcm_substream *playback = NULL;
	struct snd_pcm_substream *capture = NULL;
	unsigned long flags;
	u32 position = 0, raw_status, status;

	if (!chip->iobase)
		return IRQ_NONE;

	raw_status = readl(chip->iobase + QUANTUM_REG_IRQ_STATUS);
	status = raw_status & (QUANTUM_IRQ_AUDIO | QUANTUM_IRQ_TCI_RX);
	if (!status)
		return IRQ_NONE;

	/* The DEXT acknowledges asserted sources by writing one bits back. */
	writel(status, chip->iobase + QUANTUM_REG_IRQ_STATUS);
	if (status & QUANTUM_IRQ_AUDIO) {
		position = readl(chip->iobase + QUANTUM_REG_AUDIO_POSITION);
		spin_lock_irqsave(&chip->audio_lock, flags);
		chip->audio_last_irq_status = raw_status;
		chip->audio_last_irq_position = position;
		if (chip->audio_engine_running) {
			chip->audio_irq_count++;
			if (chip->audio_running & QUANTUM_STREAM_PLAYBACK)
				playback = chip->playback_substream;
			if (chip->audio_running & QUANTUM_STREAM_CAPTURE)
				capture = chip->capture_substream;
		}
		spin_unlock_irqrestore(&chip->audio_lock, flags);
		if (playback)
			snd_pcm_period_elapsed(playback);
		if (capture) {
			dma_rmb();
			snd_pcm_period_elapsed(capture);
		}
	}
	return IRQ_HANDLED;
}

/* ----- Read-only device identification ----- */

static void quantum_log_device_info(struct quantum_chip *chip)
{
	struct pci_dev *pci = chip->pci;
	void __iomem *iobase = chip->iobase;

	dev_info(&pci->dev, "Device: version 0x00=0x%08x status 0x04=0x%08x 0x08=0x%08x\n",
		 readl(iobase + QUANTUM_REG_VERSION),
		 readl(iobase + QUANTUM_REG_STATUS1),
		 readl(iobase + QUANTUM_REG_STATUS2));
	dev_info(&pci->dev, "Device: status 0x10=0x%08x 0x14=0x%08x 0x104=0x%08x\n",
		 readl(iobase + QUANTUM_REG_STATUS3),
		 readl(iobase + QUANTUM_REG_STATUS4),
		 readl(iobase + QUANTUM_REG_STATUS5));
	dev_info(&pci->dev, "Device: record/play addresses per segment=%u/%u\n",
		 readl(iobase + QUANTUM_REG_REC_ADDRS_PER_SEGMENT),
		 readl(iobase + QUANTUM_REG_PLAY_ADDRS_PER_SEGMENT));
	dev_info(&pci->dev, "Device: capture/playback channels=%u/%u\n",
		 readl(iobase + QUANTUM_REG_AUDIO_CHANNELS) & 0xff,
		 (readl(iobase + QUANTUM_REG_AUDIO_CHANNELS) >> 8) & 0xff);
}

/* ----- Create chip: enable PCI, claim BAR, IRQ, MMIO probe ----- */

static int snd_quantum_create(struct snd_card *card, struct pci_dev *pci)
{
	struct quantum_chip *chip = card->private_data;
	int err;
	int i;

	chip->card = card;
	chip->pci = pci;
	chip->irq = pci->irq;
	chip->irq_requested = false;
	chip->msi_allocated = false;
	mutex_init(&chip->tci_lock);
	mutex_init(&chip->audio_mutex);
	spin_lock_init(&chip->audio_lock);

	err = pci_enable_device(pci);
	if (err < 0)
		return err;

	if (dma_set_mask_and_coherent(&pci->dev, DMA_BIT_MASK(64)) < 0 &&
	    dma_set_mask_and_coherent(&pci->dev, DMA_BIT_MASK(32)) < 0) {
		pci_disable_device(pci);
		return -ENXIO;
	}
	pci_set_master(pci);

	err = pci_request_regions(pci, DRV_NAME);
	if (err < 0) {
		pci_clear_master(pci);
		pci_disable_device(pci);
		return err;
	}

	chip->iobase = pci_iomap(pci, 0, 0);
	if (!chip->iobase) {
		err = -ENOMEM;
		goto fail_regions;
	}

	/* The DEXT never reads this mask and maintains a zero-based shadow. */
	chip->irq_mask = 0;
	writel(chip->irq_mask, chip->iobase + QUANTUM_REG_IRQ_MASK);
	writel(QUANTUM_IRQ_AUDIO | QUANTUM_IRQ_TCI_RX,
	       chip->iobase + QUANTUM_REG_IRQ_STATUS);

	/* Log first 64 bytes of BAR 0 for reverse-engineering (word-aligned) */
	for (i = 0; i < 64; i += 4)
		dev_info(&pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));

	quantum_log_device_info(chip);
	err = quantum_tci_start(chip);
	if (err < 0)
		goto fail_iomap;
	err = quantum_tci_probe_control(chip);
	if (err < 0) {
		dev_err(&pci->dev, "TCI control probe failed: %d\n", err);
		goto fail_tci;
	}

	/* Register access for reverse engineering */
	if (reg_scan) {
		dev_info(&pci->dev, "=== MMIO Scan (0x00-0xff) ===");
		for (i = 0; i < 256; i += 4)
			dev_info(&pci->dev, "MMIO+0x%02x: 0x%08x", i, readl(chip->iobase + i));
		reg_scan = false; /* Clear after one scan */
	}

	if (reg_read_offset >= 0 && reg_read_offset < (1024 * 1024)) {
		u32 val = readl(chip->iobase + reg_read_offset);

		dev_info(&pci->dev, "MMIO+0x%03x READ: 0x%08x", reg_read_offset, val);
		reg_read_offset = -1; /* Clear after read */
	}

	if (reg_write_offset >= 0 && reg_write_offset < (1024 * 1024)) {
		writel(reg_write_value, chip->iobase + reg_write_offset);
		dev_info(&pci->dev, "MMIO+0x%03x WRITE: 0x%08x (old: 0x%08x)",
			 reg_write_offset, reg_write_value,
			 readl(chip->iobase + reg_write_offset));
		reg_write_offset = -1; /* Clear after write */
		reg_write_value = 0;
	}

	/* Prefer MSI (Thunderbolt PCIe often has legacy IRQ 0); fall back to legacy if valid */
	if (pci_alloc_irq_vectors(pci, 1, 1, PCI_IRQ_MSI) == 1) {
		chip->irq = pci_irq_vector(pci, 0);
		chip->msi_allocated = true;
	} else {
		pci_free_irq_vectors(pci);
		chip->irq = pci->irq;
	}
	/* Only request if we have a usable IRQ (legacy IRQ 0 is the PIT on x86, not our device) */
	if (chip->irq > 0) {
		err = request_irq(chip->irq, snd_quantum_interrupt,
				  chip->msi_allocated ? 0 : IRQF_SHARED,
				  DRV_NAME, chip);
		if (err == 0) {
			chip->irq_requested = true;
			card->sync_irq = chip->irq;
		} else {
			dev_warn(&pci->dev, "cannot request irq %d: %d\n",
				 chip->irq, err);
		}
	} else if (chip->irq == 0) {
		dev_info(&pci->dev, "legacy irq 0 is not usable\n");
	}
	if (!chip->irq_requested && chip->msi_allocated) {
		pci_free_irq_vectors(pci);
		chip->msi_allocated = false;
	}

	return 0;
fail_tci:
	quantum_tci_stop(chip);
fail_iomap:
	pci_iounmap(pci, chip->iobase);
	chip->iobase = NULL;
fail_regions:
	pci_release_regions(pci);
	pci_clear_master(pci);
	pci_disable_device(pci);
	return err;
}

/* ----- PCI table: intentionally scoped to the tested Quantum 2626 ----- */

static const struct pci_device_id snd_quantum_ids[] = {
	{ PCI_DEVICE(PCI_VENDOR_ID_PRESONUS, PCI_DEVICE_ID_QUANTUM2626) },
	{ 0, }
};
MODULE_DEVICE_TABLE(pci, snd_quantum_ids);

/* ----- Probe / remove ----- */

static int snd_quantum_probe(struct pci_dev *pci, const struct pci_device_id *pci_id)
{
	static int dev;
	struct snd_card *card;
	struct quantum_chip *chip;
	int err;

	if (dev >= SNDRV_CARDS)
		return -ENODEV;
	if (!enable[dev]) {
		dev++;
		return -ENOENT;
	}

	err = snd_devm_card_new(&pci->dev, index[dev], id[dev], THIS_MODULE,
				sizeof(struct quantum_chip), &card);
	if (err < 0)
		return err;
	chip = card->private_data;
	chip->irq = -1;

	err = snd_quantum_create(card, pci);
	if (err < 0)
		return err;
	card->private_free = snd_quantum_free;
	if (chip->irq_requested) {
		err = snd_quantum_pcm_new(chip);
		if (err < 0)
			return err;
	} else {
		dev_warn(&pci->dev, "audio disabled because no IRQ is available\n");
	}

	strscpy(card->driver, DRV_NAME, sizeof(card->driver));
	strscpy(card->shortname, QUANTUM_NAMELONG, sizeof(card->shortname));
	snprintf(card->longname, sizeof(card->longname), "%s at %s irq %i",
		 card->shortname, pci_name(chip->pci), chip->irq);

	err = snd_card_register(card);
	if (err < 0)
		return err;

	pci_set_drvdata(pci, card);
	dev++;
	return 0;
}

static void snd_quantum_remove(struct pci_dev *pci)
{
	snd_card_free(pci_get_drvdata(pci));
}

static struct pci_driver quantum_driver = {
	.name = DRV_NAME,
	.id_table = snd_quantum_ids,
	.probe = snd_quantum_probe,
	.remove = snd_quantum_remove,
};

module_pci_driver(quantum_driver);
