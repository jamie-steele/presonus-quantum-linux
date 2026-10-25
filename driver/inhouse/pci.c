// SPDX-License-Identifier: GPL-2.0-only

#include <linux/dma-mapping.h>
#include <linux/module.h>
#include <sound/initval.h>

#include "quantum.h"

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
