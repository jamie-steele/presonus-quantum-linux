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

/* Register access for reverse engineering */
static int reg_read_offset = -1;
module_param(reg_read_offset, int, 0644);
MODULE_PARM_DESC(reg_read_offset, "MMIO offset to read (hex, -1 to disable). Result in dmesg.");

static int reg_write_offset = -1;
module_param(reg_write_offset, int, 0644);
MODULE_PARM_DESC(reg_write_offset, "MMIO offset to write (hex, -1 to disable).");

static int reg_write_value = 0;
module_param(reg_write_value, int, 0644);
MODULE_PARM_DESC(reg_write_value, "Value to write to reg_write_offset (hex).");

static bool reg_scan;
module_param(reg_scan, bool, 0644);
MODULE_PARM_DESC(reg_scan, "Scan and dump first 256 bytes of MMIO (0x00-0xff).");

MODULE_AUTHOR("Quantum2626 Linux driver project");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("PreSonus Quantum 2626 (and family) ALSA PCI driver (skeleton)");

/* Register offsets (from Ghidra analysis) */
#define QUANTUM_REG_VERSION	0x0000	/* Version/ID register */
#define QUANTUM_REG_STATUS1	0x0004	/* Status/Control */
#define QUANTUM_REG_STATUS2	0x0008	/* Status/Control */
#define QUANTUM_REG_STATUS3	0x0010	/* Status/Control */
#define QUANTUM_REG_STATUS4	0x0014	/* Status/Control */
#define QUANTUM_REG_CONTROL	0x0100	/* Control register (write 0x8) */
#define QUANTUM_REG_STATUS5	0x0104	/* Status/Control */
#define QUANTUM_REG_BUFFER0	0x10300	/* Buffer/Channel register (DMA buffer address) */
#define QUANTUM_REG_BUFFER1	0x10304	/* Buffer/Channel register (DMA buffer address) */

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
	
	/* Hardware state */
	dma_addr_t playback_dma_addr;
	dma_addr_t capture_dma_addr;
	size_t playback_buffer_size;
	size_t capture_buffer_size;
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
	struct quantum_chip *chip = substream->pcm->private_data;
	struct snd_pcm_runtime *runtime = substream->runtime;
	
	/* Store buffer size for later use in prepare() */
	if (substream->stream == SNDRV_PCM_STREAM_PLAYBACK)
		chip->playback_buffer_size = params_buffer_bytes(hw_params);
	else
		chip->capture_buffer_size = params_buffer_bytes(hw_params);
	
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
	struct snd_pcm_runtime *runtime = substream->runtime;
	dma_addr_t dma_addr;
	size_t buffer_size;
	int i;
	u32 val;

	if (qr)
		qr->position = 0;

	if (!chip->iobase)
		return -EIO;

	/* Get DMA address and buffer size */
	if (substream->stream == SNDRV_PCM_STREAM_PLAYBACK) {
		dma_addr = runtime->dma_addr;
		buffer_size = chip->playback_buffer_size;
		chip->playback_dma_addr = dma_addr;
	} else {
		dma_addr = runtime->dma_addr;
		buffer_size = chip->capture_buffer_size;
		chip->capture_dma_addr = dma_addr;
	}

	/* Program DMA buffer address to hardware */
	/* Based on Ghidra analysis: 0x10300 and 0x10304 are buffer registers */
	if (substream->stream == SNDRV_PCM_STREAM_PLAYBACK) {
		/* Write buffer address (lower 32 bits) */
		writel((u32)(dma_addr & 0xffffffff), chip->iobase + QUANTUM_REG_BUFFER0);
		/* Write buffer address (upper 32 bits if 64-bit) */
		/* Note: May need adjustment based on actual hardware */
	} else {
		/* Capture buffer */
		writel((u32)(dma_addr & 0xffffffff), chip->iobase + QUANTUM_REG_BUFFER1);
	}

	/* Read initial status registers (from Ghidra: reads 0x0, 0x4, 0x8, 0x10, 0x14, 0x104) */
	val = readl(chip->iobase + QUANTUM_REG_VERSION);
	dev_dbg(&chip->pci->dev, "Version reg (0x%04x): 0x%08x\n", QUANTUM_REG_VERSION, val);
	
	val = readl(chip->iobase + QUANTUM_REG_STATUS1);
	dev_dbg(&chip->pci->dev, "Status1 (0x%04x): 0x%08x\n", QUANTUM_REG_STATUS1, val);
	
	val = readl(chip->iobase + QUANTUM_REG_STATUS5);
	dev_dbg(&chip->pci->dev, "Status5 (0x%04x): 0x%08x\n", QUANTUM_REG_STATUS5, val);

	/* Write control register (from Ghidra: 0x100 = 0x8) */
	writel(0x8, chip->iobase + QUANTUM_REG_CONTROL);
	dev_dbg(&chip->pci->dev, "Control reg (0x%04x) = 0x08\n", QUANTUM_REG_CONTROL);

	if (dump_on_trigger) {
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
	u32 control_val;
	int i;

	if (!qr)
		return -EINVAL;

	if (!chip->iobase)
		return -EIO;

	switch (cmd) {
	case SNDRV_PCM_TRIGGER_START:
		if (dump_on_trigger) {
			dev_info(&chip->pci->dev, "MMIO at trigger START:");
			for (i = 0; i < 64; i += 4)
				dev_info(&chip->pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));
		}

		/* Start hardware stream */
		/* Based on Ghidra: control register at 0x100 controls stream */
		control_val = readl(chip->iobase + QUANTUM_REG_CONTROL);
		/* Set stream start bit (exact bit needs experimentation) */
		/* For now, ensure control register is set */
		writel(0x8, chip->iobase + QUANTUM_REG_CONTROL);
		dev_dbg(&chip->pci->dev, "Started %s stream\n",
			substream->stream == SNDRV_PCM_STREAM_PLAYBACK ? "playback" : "capture");

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
	case SNDRV_PCM_TRIGGER_SUSPEND:
	case SNDRV_PCM_TRIGGER_PAUSE_PUSH:
		if (dump_on_trigger) {
			dev_info(&chip->pci->dev, "MMIO at trigger STOP:");
			for (i = 0; i < 64; i += 4)
				dev_info(&chip->pci->dev, "MMIO+0x%02x: 0x%08x\n", i, readl(chip->iobase + i));
		}

		/* Stop hardware stream */
		control_val = readl(chip->iobase + QUANTUM_REG_CONTROL);
		/* Clear stream start bit */
		/* For now, just clear control register */
		writel(0x0, chip->iobase + QUANTUM_REG_CONTROL);
		dev_dbg(&chip->pci->dev, "Stopped %s stream\n",
			substream->stream == SNDRV_PCM_STREAM_PLAYBACK ? "playback" : "capture");

		qr->running = false;
		if (substream->stream == SNDRV_PCM_STREAM_PLAYBACK)
			chip->playback_substream = NULL;
		else
			chip->capture_substream = NULL;
		timer_delete_sync(&qr->timer);
		break;

	case SNDRV_PCM_TRIGGER_RESUME:
	case SNDRV_PCM_TRIGGER_PAUSE_RELEASE:
		/* Resume stream - same as START */
		control_val = readl(chip->iobase + QUANTUM_REG_CONTROL);
		writel(0x8, chip->iobase + QUANTUM_REG_CONTROL);
		qr->running = true;
		if (!chip->irq_requested) {
			period_msec = (runtime->period_size * 1000) / runtime->rate;
			if (period_msec < 1)
				period_msec = 1;
			mod_timer(&qr->timer, jiffies + msecs_to_jiffies(period_msec));
		}
		break;

	default:
		return -EINVAL;
	}
	return 0;
}

static snd_pcm_uframes_t quantum_pcm_pointer(struct snd_pcm_substream *substream)
{
	struct quantum_chip *chip = substream->pcm->private_data;
	struct quantum_runtime *qr = substream->runtime->private_data;
	struct snd_pcm_runtime *runtime = substream->runtime;
	unsigned long flags;
	snd_pcm_uframes_t pos = 0;
	u32 hw_pos;

	if (!qr)
		return 0;

	/* Try to read hardware position from MMIO */
	/* Based on Ghidra: status registers may contain position info */
	if (chip->iobase) {
		/* Read status register that might contain position */
		/* This is a guess - actual position register needs experimentation */
		hw_pos = readl(chip->iobase + QUANTUM_REG_STATUS5);
		
		/* If hardware position is available, use it */
		/* For now, fall back to software position */
		spin_lock_irqsave(&qr->lock, flags);
		pos = qr->position;
		spin_unlock_irqrestore(&qr->lock, flags);
	} else {
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
	u32 status;
	irqreturn_t handled = IRQ_NONE;

	if (!chip->iobase)
		return IRQ_NONE;

	/* Read interrupt status register */
	/* Based on Ghidra: status registers at 0x4, 0x8, 0x10, 0x14, 0x104 */
	/* Check which one is the interrupt status (needs experimentation) */
	status = readl(chip->iobase + QUANTUM_REG_STATUS1);
	
	/* If no interrupt pending, return */
	/* For now, assume any non-zero status means interrupt */
	if (status == 0)
		return IRQ_NONE;

	/* Acknowledge interrupt (write to status register to clear) */
	/* Exact acknowledgment method needs experimentation */
	writel(status, chip->iobase + QUANTUM_REG_STATUS1);

	/* Handle playback */
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

	/* Handle capture */
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
	chip->playback_dma_addr = 0;
	chip->capture_dma_addr = 0;
	chip->playback_buffer_size = 0;
	chip->capture_buffer_size = 0;

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
