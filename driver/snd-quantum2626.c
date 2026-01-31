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
#include <linux/module.h>
#include <linux/pci.h>
#include <linux/slab.h>
#include <linux/dma-mapping.h>
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

MODULE_AUTHOR("Quantum2626 Linux driver project");
MODULE_LICENSE("GPL");
MODULE_DESCRIPTION("PreSonus Quantum 2626 (and family) ALSA PCI driver (skeleton)");

struct quantum_chip {
	struct snd_card *card;
	struct pci_dev *pci;
	void __iomem *iobase;	/* BAR 0, 1 MiB from lspci */
	int irq;
	struct snd_pcm *pcm;
};

/* ----- Stub PCM ops (no hardware I/O yet) ----- */

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

static int quantum_pcm_open(struct snd_pcm_substream *substream)
{
	struct snd_pcm_runtime *runtime = substream->runtime;

	runtime->hw = quantum_pcm_hw;
	return 0;
}

static int quantum_pcm_close(struct snd_pcm_substream *substream)
{
	(void)substream;
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
	(void)substream;
	return 0;
}

static int quantum_pcm_trigger(struct snd_pcm_substream *substream, int cmd)
{
	(void)substream;
	(void)cmd;
	return 0;
}

static snd_pcm_uframes_t quantum_pcm_pointer(struct snd_pcm_substream *substream)
{
	(void)substream;
	return 0;
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

	if (chip->iobase)
		pci_iounmap(chip->pci, chip->iobase);
	pci_release_regions(chip->pci);
	pci_disable_device(chip->pci);
}

/* ----- Create chip: enable PCI, claim BAR, optional IRQ ----- */

static int snd_quantum_create(struct snd_card *card, struct pci_dev *pci)
{
	struct quantum_chip *chip = card->private_data;
	int err;

	chip->card = card;
	chip->pci = pci;
	chip->irq = -1;

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

	/* IRQ: request when we have a real handler (reverse-engineer from pae_quantum.sys) */
	if (pci->irq)
		card->sync_irq = pci->irq;

	err = snd_quantum_pcm_new(chip);
	if (err < 0)
		goto fail_pcm;

	return 0;

fail_pcm:
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
