/*
 * ALSA PCI driver skeleton for PreSonus Quantum 2626 (and family)
 * PCI ID 1c67:0104 (Quantum 2626); 0101, 0102, 0103, 0105 from Windows INF.
 *
 * Based on: kernel Documentation/sound/kernel-api/writing-an-alsa-driver.rst
 * and sound/pci/ens1370.c structure. No hardware access yet — BAR mapped,
 * card + stub PCM only. Real PCM/IRQ behavior needs reverse engineering.
 *
 * SPDX-License-Identifier: GPL-2.0-only
 */

#include <linux/init.h>
#include <linux/interrupt.h>
#include <linux/kernel.h>
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/slab.h>
#include <linux/dma-mapping.h>
#include <linux/timer.h>
#include <linux/jiffies.h>
#include <sound/core.h>
#include <sound/initval.h>
#include <sound/pcm.h>
#include <sound/pcm_params.h>

#define DRV_NAME "snd-quantum2626"
#define QUANTUM_NAMELONG "PreSonus Quantum 2626"

/* PreSonus PCI vendor ID (from driver-reference/pae_quantum.inf) */
#define PCI_VENDOR_ID_PRESONUS	0x1c67
#define PCI_DEVICE_ID_QUANTUM	0x0101
#define PCI_DEVICE_ID_QUANTUM2	0x0102
#define PCI_DEVICE_ID_QUANTUM4848	0x0103
#define PCI_DEVICE_ID_QUANTUM2626	0x0104
#define PCI_DEVICE_ID_QUANTUM_MOBILE	0x0105

static int index[SNDRV_CARDS] = SNDRV_DEFAULT_IDX;
static char *id[SNDRV_CARDS] = SNDRV_DEFAULT_STR;
static bool enable[SNDRV_CARDS] = SNDRV_DEFAULT_ENABLE_PNP;

module_param_array(index, int, NULL, 0444);
MODULE_PARM_DESC(index, "Index value for PreSonus Quantum card.");
module_param_array(id, charp, NULL, 0444);
MODULE_PARM_DESC(id, "ID string for PreSonus Quantum card.");
module_param_array(enable, bool, NULL, 0444);
MODULE_PARM_DESC(enable, "Enable PreSonus Quantum card.");

static bool dump_on_trigger;
module_param(dump_on_trigger, bool, 0444);
MODULE_PARM_DESC(dump_on_trigger, "Dump MMIO at prepare/trigger for reverse-engineering (default off).");

MODULE_AUTHOR("Quantum2626 Linux driver project");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("PreSonus Quantum 2626 (and family) ALSA PCI driver (skeleton)");

struct quantum_chip {
	struct snd_card *card;
	struct pci_dev *pci;
	void __iomem *iobase;	/* BAR 0, 1 MiB from lspci */
	int irq;
	bool irq_requested;
	bool msi_allocated;	/* true if pci_alloc_irq_vectors(MSI) succeeded */
	struct snd_pcm *pcm;
	struct snd_pcm_substream *playback_substream;
	struct snd_pcm_substream *capture_substream;
};

/* Per-substream: fake hw pointer so stream runs (timer-driven until we have real IRQ) */
struct quantum_runtime {
	spinlock_t lock;
	snd_pcm_uframes_t position;
	struct timer_list timer;
	struct snd_pcm_substream *substream;
	bool running;
};

/* ----- PCM ops: timer-driven fake pointer so aplay/arecord can run ----- */

static const struct snd_pcm_hardware quantum_pcm_hw = {
	.info = SNDRV_PCM_INFO_MMAP | SNDRV_PCM_INFO_INTERLEAVED |
		SNDRV_PCM_INFO_BLOCK_TRANSFER | SNDRV_PCM_INFO_MMAP_VALID,
	.formats = SNDRV_PCM_FMTBIT_S16_LE,
	.rates = SNDRV_PCM_RATE_44100 | SNDRV_PCM_RATE_48000 |
		 SNDRV_PCM_RATE_88200 | SNDRV_PCM_RATE_96000 |
		 SNDRV_PCM_RATE_176400 | SNDRV_PCM_RATE_192000,
	.rate_min = 44100,
	.rate_max = 192000,
	.channels_min = 2,
	.channels_max = 2,
	.buffer_bytes_max = 256 * 1024,
	.period_bytes_min = 256,
	.period_bytes_max = 256 * 1024,
	.periods_min = 2,
	.periods_max = 1024,
};

static void quantum_period_elapsed(struct timer_list *t)
{
	struct quantum_runtime *qr = container_of(t, struct quantum_runtime, timer);
	struct snd_pcm_substream *substream = qr->substream;
	struct snd_pcm_runtime *runtime = substream->runtime;
	snd_pcm_uframes_t period_frames = runtime->period_size;
	snd_pcm_uframes_t buf_frames = runtime->buffer_size;
	unsigned long flags;

	if (!qr->running)
		return;
	spin_lock_irqsave(&qr->lock, flags);
	qr->position += period_frames;
	if (qr->position >= buf_frames)
		qr->position -= buf_frames;
	spin_unlock_irqrestore(&qr->lock, flags);
	snd_pcm_period_elapsed(substream);
	mod_timer(&qr->timer, jiffies + msecs_to_jiffies((period_frames * 1000) / runtime->rate));
}

static int quantum_pcm_open(struct snd_pcm_substream *substream)
{
	struct quantum_runtime *qr;

	qr = kzalloc(sizeof(*qr), GFP_KERNEL);
	if (!qr)
		return -ENOMEM;
	spin_lock_init(&qr->lock);
	qr->substream = substream;
	timer_setup(&qr->timer, quantum_period_elapsed, 0);
	substream->runtime->private_data = qr;
	substream->runtime->hw = quantum_pcm_hw;
	return 0;
}

static int quantum_pcm_close(struct snd_pcm_substream *substream)
{
	struct quantum_runtime *qr = substream->runtime->private_data;

	if (qr) {
		qr->running = false;
		timer_delete_sync(&qr->timer);
		kfree(qr);
		substream->runtime->private_data = NULL;
	}
	return 0;
}

static int quantum_pcm_hw_params(struct snd_pcm_substream *substream,
				 struct snd_pcm_hw_params *hw_params)
{
	(void)substream;
	(void)hw_params;
	return 0;
}

static int quantum_pcm_hw_free(struct snd_pcm_substream *substream)
{
	(void)substream;
	return 0;
}

static int quantum_pcm_prepare(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = substream->pcm->private_data;
	struct quantum_runtime *qr = substream->runtime->private_data;
	int i;

	if (qr)
		qr->position = 0;
	if (dump_on_trigger && chip->iobase) {
		dev_info(&chip->pci->dev, "MMIO at prepare:");
		for (i = 0; i < 64; i += 4)
			dev_info(&chip->pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));
	}
	return 0;
}

static int quantum_pcm_trigger(struct snd_pcm_substream *substream, int cmd)
{
	struct quantum_chip *chip = substream->pcm->private_data;
	struct quantum_runtime *qr = substream->runtime->private_data;
	struct snd_pcm_runtime *runtime = substream->runtime;
	unsigned long period_msec;
	int i;

	if (!qr)
		return -EINVAL;
	switch (cmd) {
	case SNDRV_PCM_TRIGGER_START:
		if (dump_on_trigger && chip->iobase) {
			dev_info(&chip->pci->dev, "MMIO at trigger START:");
			for (i = 0; i < 64; i += 4)
				dev_info(&chip->pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));
		}
		qr->running = true;
		qr->position = 0;
		if (substream->stream == SNDRV_PCM_STREAM_PLAYBACK)
			chip->playback_substream = substream;
		else
			chip->capture_substream = substream;
		/* Use timer only if we didn't get an IRQ (fallback) */
		if (!chip->irq_requested) {
			period_msec = (runtime->period_size * 1000) / runtime->rate;
			if (period_msec < 1)
				period_msec = 1;
			mod_timer(&qr->timer, jiffies + msecs_to_jiffies(period_msec));
		}
		break;
	case SNDRV_PCM_TRIGGER_STOP:
		if (dump_on_trigger && chip->iobase) {
			dev_info(&chip->pci->dev, "MMIO at trigger STOP:");
			for (i = 0; i < 64; i += 4)
				dev_info(&chip->pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));
		}
		qr->running = false;
		if (substream->stream == SNDRV_PCM_STREAM_PLAYBACK)
			chip->playback_substream = NULL;
		else
			chip->capture_substream = NULL;
		timer_delete_sync(&qr->timer);
		break;
	default:
		return -EINVAL;
	}
	return 0;
}

static snd_pcm_uframes_t quantum_pcm_pointer(struct snd_pcm_substream *substream)
{
	struct quantum_runtime *qr = substream->runtime->private_data;
	unsigned long flags;
	snd_pcm_uframes_t pos = 0;

	if (qr) {
		spin_lock_irqsave(&qr->lock, flags);
		pos = qr->position;
		spin_unlock_irqrestore(&qr->lock, flags);
	}
	return pos;
}

static const struct snd_pcm_ops quantum_pcm_ops = {
	.open = quantum_pcm_open,
	.close = quantum_pcm_close,
	.hw_params = quantum_pcm_hw_params,
	.hw_free = quantum_pcm_hw_free,
	.prepare = quantum_pcm_prepare,
	.trigger = quantum_pcm_trigger,
	.pointer = quantum_pcm_pointer,
};

static int snd_quantum_pcm_new(struct quantum_chip *chip)
{
	struct snd_pcm *pcm;
	int err;

	err = snd_pcm_new(chip->card, "Quantum2626", 0, 1, 1, &pcm);
	if (err < 0)
		return err;
	pcm->private_data = chip;
	strscpy(pcm->name, QUANTUM_NAMELONG, sizeof(pcm->name));
	chip->pcm = pcm;
	snd_pcm_set_ops(pcm, SNDRV_PCM_STREAM_PLAYBACK, &quantum_pcm_ops);
	snd_pcm_set_ops(pcm, SNDRV_PCM_STREAM_CAPTURE, &quantum_pcm_ops);
	snd_pcm_set_managed_buffer_all(pcm, SNDRV_DMA_TYPE_DEV, &chip->pci->dev, 64 * 1024, 256 * 1024);
	return 0;
}

/* ----- Resource release ----- */

static void snd_quantum_free(struct snd_card *card)
{
	struct quantum_chip *chip = card->private_data;

	if (chip->irq_requested && chip->irq >= 0)
		free_irq(chip->irq, chip);
	if (chip->msi_allocated)
		pci_free_irq_vectors(chip->pci);
	if (chip->iobase)
		pci_iounmap(chip->pci, chip->iobase);
	pci_release_regions(chip->pci);
	pci_disable_device(chip->pci);
}

/* ----- Interrupt: signal period elapsed for active substreams ----- */

static irqreturn_t snd_quantum_interrupt(int irq, void *dev_id)
{
	struct quantum_chip *chip = dev_id;
	struct snd_pcm_substream *s;
	struct quantum_runtime *qr;
	unsigned long flags;
	snd_pcm_uframes_t period_frames, buf_frames;
	irqreturn_t handled = IRQ_NONE;

	s = chip->playback_substream;
	if (s && snd_pcm_running(s)) {
		qr = s->runtime->private_data;
		if (qr) {
			period_frames = s->runtime->period_size;
			buf_frames = s->runtime->buffer_size;
			spin_lock_irqsave(&qr->lock, flags);
			qr->position += period_frames;
			if (qr->position >= buf_frames)
				qr->position -= buf_frames;
			spin_unlock_irqrestore(&qr->lock, flags);
			snd_pcm_period_elapsed(s);
			handled = IRQ_HANDLED;
		}
	}
	s = chip->capture_substream;
	if (s && snd_pcm_running(s)) {
		qr = s->runtime->private_data;
		if (qr) {
			period_frames = s->runtime->period_size;
			buf_frames = s->runtime->buffer_size;
			spin_lock_irqsave(&qr->lock, flags);
			qr->position += period_frames;
			if (qr->position >= buf_frames)
				qr->position -= buf_frames;
			spin_unlock_irqrestore(&qr->lock, flags);
			snd_pcm_period_elapsed(s);
			handled = IRQ_HANDLED;
		}
	}
	return handled;
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
	chip->playback_substream = NULL;
	chip->capture_substream = NULL;

	err = pci_enable_device(pci);
	if (err < 0)
		return err;

	if (dma_set_mask_and_coherent(&pci->dev, DMA_BIT_MASK(32)) < 0) {
		pci_disable_device(pci);
		return -ENXIO;
	}

	err = pci_request_regions(pci, DRV_NAME);
	if (err < 0) {
		pci_disable_device(pci);
		return err;
	}

	chip->iobase = pci_iomap(pci, 0, 0);
	if (!chip->iobase) {
		err = -ENOMEM;
		goto fail_regions;
	}

	/* Log first 64 bytes of BAR 0 for reverse-engineering (word-aligned) */
	for (i = 0; i < 64; i += 4)
		dev_info(&pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));

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
		err = request_irq(chip->irq, snd_quantum_interrupt, IRQF_SHARED,
				  DRV_NAME, chip);
		if (err == 0) {
			chip->irq_requested = true;
			card->sync_irq = chip->irq;
		} else {
			dev_warn(&pci->dev, "cannot request irq %d, using timer fallback: %d\n",
				 chip->irq, err);
		}
	} else if (chip->irq == 0) {
		dev_info(&pci->dev, "legacy irq 0 (invalid), using timer fallback\n");
	}
	if (!chip->irq_requested && chip->msi_allocated) {
		pci_free_irq_vectors(pci);
		chip->msi_allocated = false;
	}

	err = snd_quantum_pcm_new(chip);
	if (err < 0)
		goto fail_pcm;

	return 0;

fail_pcm:
	if (chip->irq_requested) {
		free_irq(chip->irq, chip);
		chip->irq_requested = false;
	}
	if (chip->msi_allocated) {
		pci_free_irq_vectors(pci);
		chip->msi_allocated = false;
	}
	pci_iounmap(pci, chip->iobase);
	chip->iobase = NULL;
fail_regions:
	pci_release_regions(pci);
	pci_disable_device(pci);
	return err;
}

/* ----- PCI table (from pae_quantum.inf) ----- */

static const struct pci_device_id snd_quantum_ids[] = {
	{ PCI_DEVICE(PCI_VENDOR_ID_PRESONUS, PCI_DEVICE_ID_QUANTUM) },
	{ PCI_DEVICE(PCI_VENDOR_ID_PRESONUS, PCI_DEVICE_ID_QUANTUM2) },
	{ PCI_DEVICE(PCI_VENDOR_ID_PRESONUS, PCI_DEVICE_ID_QUANTUM4848) },
	{ PCI_DEVICE(PCI_VENDOR_ID_PRESONUS, PCI_DEVICE_ID_QUANTUM2626) },
	{ PCI_DEVICE(PCI_VENDOR_ID_PRESONUS, PCI_DEVICE_ID_QUANTUM_MOBILE) },
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

	card->private_free = snd_quantum_free;

	err = snd_quantum_create(card, pci);
	if (err < 0)
		return err;

	strscpy(card->driver, DRV_NAME, sizeof(card->driver));
	strscpy(card->shortname, QUANTUM_NAMELONG, sizeof(card->shortname));
	snprintf(card->longname, sizeof(card->longname), "%s at 0x%px irq %i",
		 card->shortname, chip->iobase, chip->pci->irq);

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
