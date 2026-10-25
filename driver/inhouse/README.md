# In-house research fallback

This directory builds `snd-quantum2626.ko`, the earlier experimental driver.
Nicholas Johnson's pinned upstream RFC remains the default backend. Build the
fallback from the repository root with:

```sh
make -C driver QUANTUM_DRIVER=inhouse W=1
```

The module is written to `build/driver/inhouse/snd-quantum2626.ko`, with all
intermediate output under that same directory. Source files here stay clean.

The former `driver/snd-quantum2626.c` is split by responsibility:

| Component | Responsibility |
| --- | --- |
| `rates.c`, `rates.h` | Immutable rate/channel profiles and protocol-value lookup; no PCI, ALSA, or MMIO dependencies. |
| `tci.c` | Mailbox DMA rings, request/response transactions, clock discovery, and sample-rate control. |
| `dma.c` | Audio page-table allocation, population, programming, and engine stop. |
| `pcm.c` | ALSA constraints and callbacks; coordinates rate selection and duplex DMA resources. |
| `irq.c` | IRQ acknowledgement, late-stream alignment, and period notifications. |
| `pci.c` | Module identity and parameters, PCI acquisition/unwind, card registration, and retained diagnostics. |
| `registers.h` | Named device registers and protocol constants with their original evidence labels. |
| `quantum.h` | Shared device state, audio geometry, and internal component contracts. |
| `Kbuild` | Single composite-module definition, also used by the disposable migration fixture. |

Rate profiles are the hardware-independent policy. ALSA adapts that policy to
PCM constraints, while PCI, mailbox, DMA, and interrupt components own their
kernel/hardware boundaries. Helpers remain file-local unless another component
actually calls them. Internal cross-file functions are not exported kernel APIs.
Fallible operations retain Linux errno returns and the existing unwind paths.

The shared `quantum_chip` remains the per-card aggregate. Its layout, mutexes,
IRQ spinlock, DMA ownership, and substream lifetimes are preserved by the source
split. In particular, PCM and IRQ paths still coordinate through `audio_lock`,
and duplex parameter/resource changes through `audio_mutex`. Splitting files
does not authorize a change in those concurrency contracts.

The module name, supported PCI ID, module parameters, and native commands are
unchanged. Migration and cleanup tests stage all source files and headers using
the same Kbuild object list, rather than copying a single source file or generated
objects. The upstream cache
and its source layout remain separate.

Compilation and source-preservation checks do not establish live audio safety.
Read [current status](../../research/notes/CURRENT_STATUS.md) and the
[driver development guide](../../docs/agents/driver-development.md) before changes.
