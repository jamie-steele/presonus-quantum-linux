/* SPDX-License-Identifier: GPL-2.0-only */

#ifndef QUANTUM2626_INTERNAL_H
#define QUANTUM2626_INTERNAL_H

#include <linux/interrupt.h>
#include <linux/kernel.h>
#include <linux/mutex.h>
#include <linux/pci.h>
#include <linux/spinlock.h>
#include <sound/core.h>
#include <sound/pcm.h>

#include "rates.h"
#include "registers.h"

#define DRV_NAME "snd-quantum2626"
#define QUANTUM_NAMELONG "PreSonus Quantum 2626"

/* PreSonus PCI vendor ID (from research/windows/pae_quantum.inf) */
#define PCI_VENDOR_ID_PRESONUS	0x1c67
#define PCI_DEVICE_ID_QUANTUM2626	0x0104

#define QUANTUM_AUDIO_MIN_CHANNELS	8
#define QUANTUM_AUDIO_MAX_CHANNELS	26
#define QUANTUM_AUDIO_PERIOD_FRAMES	128
#define QUANTUM_AUDIO_MIN_PERIODS	2
#define QUANTUM_AUDIO_MAX_PERIODS	64
#define QUANTUM_AUDIO_BYTES_PER_SAMPLE	4
#define QUANTUM_AUDIO_CPU_LATENCY_US	2
#define QUANTUM_AUDIO_MAX_BUFFER_BYTES \
	(QUANTUM_AUDIO_MAX_CHANNELS * QUANTUM_AUDIO_BYTES_PER_SAMPLE * \
	 QUANTUM_AUDIO_PERIOD_FRAMES * \
	 QUANTUM_AUDIO_MAX_PERIODS)
#define QUANTUM_STREAM_PLAYBACK	BIT(0)
#define QUANTUM_STREAM_CAPTURE	BIT(1)

struct quantum_dma_table {
	void *area;
	dma_addr_t dma;
	size_t bytes;
	u32 addresses_per_segment;
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
	/* Fixed PCM buffers and their page tables stay valid until card release. */
	size_t audio_buffer_bytes;
	u32 audio_params;
	u32 audio_prepared;
	u32 audio_running;
	u32 audio_pending;
	bool audio_engine_running;
	u32 irq_mask;
	u64 audio_irq_count;
	u32 audio_start_position;
	u32 audio_last_irq_position;
	u32 audio_last_irq_status;
};

/* tci.c */
void quantum_tci_stop(struct quantum_chip *chip);
int quantum_tci_start(struct quantum_chip *chip);
int quantum_tci_set_sample_rate(
	struct quantum_chip *chip, const struct quantum_rate_profile *profile);
int quantum_tci_probe_control(struct quantum_chip *chip);

/* dma.c */
void quantum_audio_set_prepared(struct quantum_chip *chip, u32 prepared);
void quantum_audio_free_resources(struct quantum_chip *chip);
int quantum_audio_stop(struct quantum_chip *chip);
int quantum_audio_program_resources(struct quantum_chip *chip);
int quantum_audio_configure_resources(struct quantum_chip *chip,
					     size_t bytes);

/* pcm.c */
int snd_quantum_pcm_new(struct quantum_chip *chip);

/* irq.c */
irqreturn_t snd_quantum_interrupt(int irq, void *dev_id);

#endif /* QUANTUM2626_INTERNAL_H */
