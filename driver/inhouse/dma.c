// SPDX-License-Identifier: GPL-2.0-only

#include <linux/delay.h>
#include <linux/dma-mapping.h>

#include "quantum.h"

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
	table->addresses_per_segment = 0;
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

void quantum_audio_set_prepared(struct quantum_chip *chip, u32 prepared)
{
	unsigned long flags;

	spin_lock_irqsave(&chip->audio_lock, flags);
	chip->audio_prepared = prepared;
	spin_unlock_irqrestore(&chip->audio_lock, flags);
}

void quantum_audio_free_resources(struct quantum_chip *chip)
{
	quantum_audio_clear_registers(chip);
	quantum_dma_table_free(chip, &chip->capture_table);
	quantum_dma_table_free(chip, &chip->playback_table);
	chip->audio_buffer_bytes = 0;
	quantum_audio_set_prepared(chip, 0);
}

static int quantum_dma_table_allocate(struct quantum_chip *chip,
				      struct quantum_dma_table *table,
				      u32 addresses_per_segment)
{
	unsigned int pages, segments;

	if (!addresses_per_segment || addresses_per_segment >= PAGE_SIZE / sizeof(__le64))
		return -EPROTO;
	if (table->area)
		return table->addresses_per_segment == addresses_per_segment ?
			0 : -EPROTO;

	pages = DIV_ROUND_UP(QUANTUM_AUDIO_MAX_BUFFER_BYTES, PAGE_SIZE);
	segments = DIV_ROUND_UP(pages, addresses_per_segment);
	table->bytes = segments * PAGE_SIZE;
	table->addresses_per_segment = addresses_per_segment;
	table->area = dma_alloc_coherent(&chip->pci->dev, table->bytes,
					 &table->dma, GFP_KERNEL);
	if (!table->area) {
		table->bytes = 0;
		table->addresses_per_segment = 0;
		return -ENOMEM;
	}
	if (!IS_ALIGNED(table->dma, PAGE_SIZE)) {
		dev_err(&chip->pci->dev, "audio DMA table is not page aligned: %pad\n",
			&table->dma);
		quantum_dma_table_free(chip, table);
		return -EINVAL;
	}
	memset(table->area, 0, table->bytes);

	return 0;
}

static int quantum_dma_table_populate(struct quantum_chip *chip,
				      struct quantum_dma_table *table,
				      dma_addr_t buffer_dma,
				      size_t buffer_bytes)
{
	unsigned int pages, segments, segment, page = 0;
	u32 addresses_per_segment = table->addresses_per_segment;

	if (!table->area || !addresses_per_segment || !buffer_bytes ||
	    buffer_bytes > QUANTUM_AUDIO_MAX_BUFFER_BYTES)
		return -EINVAL;
	if (!IS_ALIGNED(buffer_dma, PAGE_SIZE)) {
		dev_err(&chip->pci->dev, "audio DMA buffer is not page aligned: %pad\n",
			&buffer_dma);
		return -EINVAL;
	}

	pages = DIV_ROUND_UP(buffer_bytes, PAGE_SIZE);
	segments = DIV_ROUND_UP(pages, addresses_per_segment);
	if (segments * PAGE_SIZE > table->bytes)
		return -ENOMEM;

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
	dma_wmb();

	return 0;
}

int quantum_audio_stop(struct quantum_chip *chip)
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
	chip->audio_pending = 0;
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

int quantum_audio_program_resources(struct quantum_chip *chip)
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

int quantum_audio_configure_resources(struct quantum_chip *chip,
					     size_t bytes)
{
	struct snd_pcm_substream *playback =
		chip->pcm->streams[SNDRV_PCM_STREAM_PLAYBACK].substream;
	struct snd_pcm_substream *capture =
		chip->pcm->streams[SNDRV_PCM_STREAM_CAPTURE].substream;
	dma_addr_t playback_dma, capture_dma;
	u32 capture_addresses, playback_addresses;
	int err;

	if (!playback || !capture || !playback->dma_buffer.area ||
	    !capture->dma_buffer.area ||
	    playback->dma_buffer.bytes < QUANTUM_AUDIO_MAX_BUFFER_BYTES ||
	    capture->dma_buffer.bytes < QUANTUM_AUDIO_MAX_BUFFER_BYTES ||
	    bytes > QUANTUM_AUDIO_MAX_BUFFER_BYTES)
		return -ENOMEM;

	playback_dma = playback->dma_buffer.addr;
	capture_dma = capture->dma_buffer.addr;

	capture_addresses = readl(chip->iobase +
				  QUANTUM_REG_REC_ADDRS_PER_SEGMENT);
	playback_addresses = readl(chip->iobase +
				   QUANTUM_REG_PLAY_ADDRS_PER_SEGMENT);
	err = quantum_dma_table_allocate(chip, &chip->capture_table,
					 capture_addresses);
	if (err)
		goto fail;
	err = quantum_dma_table_allocate(chip, &chip->playback_table,
					 playback_addresses);
	if (err)
		goto fail;
	err = quantum_dma_table_populate(chip, &chip->capture_table,
					 capture_dma, bytes);
	if (err)
		goto fail;
	err = quantum_dma_table_populate(chip, &chip->playback_table,
					 playback_dma, bytes);
	if (err)
		goto fail;
	chip->audio_buffer_bytes = bytes;

	return 0;

fail:
	quantum_audio_free_resources(chip);
	return err;
}
