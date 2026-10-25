// SPDX-License-Identifier: GPL-2.0-only

#include <linux/dma-mapping.h>

#include "quantum.h"

/* ----- Interrupt: signal period elapsed for active substreams ----- */

irqreturn_t snd_quantum_interrupt(int irq, void *dev_id)
{
	struct quantum_chip *chip = dev_id;
	struct snd_pcm_substream *playback = NULL;
	struct snd_pcm_substream *capture = NULL;
	unsigned long flags;
	u32 position = 0, previous_position, promoted = 0;
	u32 raw_status, status;

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
		previous_position = chip->audio_last_irq_position;
		chip->audio_last_irq_status = raw_status;
		chip->audio_last_irq_position = position;
		if (chip->audio_engine_running) {
			u32 buffer_frames = chip->audio_buffer_bytes /
				(chip->audio_channels *
				 QUANTUM_AUDIO_BYTES_PER_SAMPLE);

			if (chip->audio_pending && buffer_frames) {
				u32 frame =
					(position & GENMASK(19, 0)) % buffer_frames;
				u32 previous_frame =
					(previous_position & GENMASK(19, 0)) %
					buffer_frames;

				if (frame < previous_frame) {
					/* The hardware and late ALSA ring are aligned. */
					promoted = chip->audio_pending;
					chip->audio_running |= promoted;
					chip->audio_pending = 0;
				}
			}
			chip->audio_irq_count++;
			/* Its first elapsed period is the one after alignment. */
			if ((chip->audio_running & ~promoted) &
			    QUANTUM_STREAM_PLAYBACK)
				playback = chip->playback_substream;
			if ((chip->audio_running & ~promoted) &
			    QUANTUM_STREAM_CAPTURE)
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
