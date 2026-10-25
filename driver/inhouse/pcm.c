// SPDX-License-Identifier: GPL-2.0-only

#include <linux/dma-mapping.h>
#include <linux/pm_qos.h>
#include <sound/pcm_params.h>

#include "quantum.h"

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

static int quantum_pcm_hw_params(struct snd_pcm_substream *substream,
				 struct snd_pcm_hw_params *params)
{
	const struct quantum_rate_profile *profile =
		quantum_rate_profile_for_rate(params_rate(params));
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	struct snd_pcm_substream **params_substream;
	struct snd_pcm_substream *other;
	size_t bytes = params_buffer_bytes(params);
	u32 mask = quantum_stream_mask(substream);
	bool changing_rate;
	int err = 0;

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
	changing_rate = chip->audio_rate != profile->rate;
	if (changing_rate && READ_ONCE(chip->audio_engine_running)) {
		err = -EBUSY;
		goto unlock;
	}
	if (changing_rate) {
		/* The engine is stopped; fixed DMA mappings remain valid. */
		err = quantum_tci_set_sample_rate(chip, profile);
		if (err)
			goto unlock;
	}

	params_substream = mask == QUANTUM_STREAM_PLAYBACK ?
		&chip->playback_params_substream : &chip->capture_params_substream;
	*params_substream = substream;
	chip->audio_params |= mask;
	quantum_audio_set_prepared(chip,
				   READ_ONCE(chip->audio_prepared) & ~mask);
	if (!chip->capture_table.area || !chip->playback_table.area ||
	    chip->audio_buffer_bytes != bytes) {
		if (READ_ONCE(chip->audio_engine_running)) {
			err = -EBUSY;
			goto clear_params;
		}
		err = quantum_audio_configure_resources(chip, bytes);
		if (err)
			goto clear_params;
	}
	goto unlock;

clear_params:
	chip->audio_params &= ~mask;
	*params_substream = NULL;

unlock:
	mutex_unlock(&chip->audio_mutex);
	return err;
}

static int quantum_pcm_hw_free(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	struct snd_pcm_substream **params_substream;
	u32 mask = quantum_stream_mask(substream);
	int err = 0;

	mutex_lock(&chip->audio_mutex);
	if ((READ_ONCE(chip->audio_running) |
	     READ_ONCE(chip->audio_pending)) & mask) {
		err = -EBUSY;
		goto unlock;
	}
	if (chip->irq_requested)
		synchronize_irq(chip->irq);
	params_substream = mask == QUANTUM_STREAM_PLAYBACK ?
		&chip->playback_params_substream : &chip->capture_params_substream;
	*params_substream = NULL;
	chip->audio_params &= ~mask;
	quantum_audio_set_prepared(chip,
				   READ_ONCE(chip->audio_prepared) & ~mask);
	if (mask == QUANTUM_STREAM_PLAYBACK &&
	    substream->dma_buffer.area && chip->audio_buffer_bytes)
		memset(substream->dma_buffer.area, 0, chip->audio_buffer_bytes);
	/*
	 * The fixed ALSA buffers outlive hw_free.  Keep both page tables and
	 * their MMIO addresses valid as well: the device can issue a final DMA
	 * transaction after its stop-status bits clear.
	 */

unlock:
	mutex_unlock(&chip->audio_mutex);
	return err;
}

static void quantum_pcm_apply_latency_qos(struct snd_pcm_substream *substream)
{
	struct pm_qos_request *request = &substream->latency_pm_qos_req;

	/* The generic period-duration request still permits disruptive deep idle. */
	if (cpu_latency_qos_request_active(request))
		cpu_latency_qos_update_request(request,
					       QUANTUM_AUDIO_CPU_LATENCY_US);
	else
		cpu_latency_qos_add_request(request,
					    QUANTUM_AUDIO_CPU_LATENCY_US);
}

static int quantum_pcm_prepare(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	struct snd_pcm_substream *playback =
		chip->pcm->streams[SNDRV_PCM_STREAM_PLAYBACK].substream;
	struct snd_pcm_substream *capture =
		chip->pcm->streams[SNDRV_PCM_STREAM_CAPTURE].substream;
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
		memset(substream->runtime->dma_area, 0,
		       chip->audio_buffer_bytes);
		dma_wmb();
		quantum_audio_set_prepared(chip,
					   READ_ONCE(chip->audio_prepared) |
					   mask);
		err = 0;
		goto unlock;
	}
	quantum_audio_set_prepared(chip, 0);
	memset(playback->dma_buffer.area, 0, chip->audio_buffer_bytes);
	memset(capture->dma_buffer.area, 0, chip->audio_buffer_bytes);
	err = quantum_audio_program_resources(chip);

unlock:
	mutex_unlock(&chip->audio_mutex);
	if (!err)
		quantum_pcm_apply_latency_qos(substream);
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
		if (first)
			chip->audio_running |= mask;
		else
			chip->audio_pending |= mask;
		chip->audio_engine_running = true;
		running = chip->audio_running | chip->audio_pending;
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
		chip->audio_pending &= ~mask;
		if (mask == QUANTUM_STREAM_PLAYBACK)
			chip->playback_substream = NULL;
		else
			chip->capture_substream = NULL;
		last = chip->audio_engine_running && !chip->audio_running &&
		       !chip->audio_pending;
		spin_unlock_irqrestore(&chip->audio_lock, flags);
		return last ? quantum_audio_stop(chip) : 0;
	default:
		return -EINVAL;
	}
}

static snd_pcm_uframes_t quantum_pcm_pointer(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = snd_pcm_substream_chip(substream);
	u32 mask = quantum_stream_mask(substream);
	u32 position = readl(chip->iobase + QUANTUM_REG_AUDIO_POSITION);

	if (!(READ_ONCE(chip->audio_running) & mask))
		return 0;
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

int snd_quantum_pcm_new(struct quantum_chip *chip)
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
					      QUANTUM_AUDIO_MAX_BUFFER_BYTES,
					      0);
}
