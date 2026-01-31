# Next: Building a Driver for 1c67:0104

The “try without reverse engineering” path is closed: `new_id` with snd_hda_intel is rejected for this device. Next is Windows profiling (Stage 2) and then driver work.

## Where we are

- **Linux:** Device visible as PCI 09:00.0 **1c67:0104** (PreSonus), class 0401 (Multimedia audio controller). No driver bound; no ALSA card.
- **Windows:** You’ll run Stage 2 and fill `notes/windows_profile.txt` (driver name, .sys file, resources, IDs).

## What we need from Stage 2 (Windows)

- Confirm **vendor:device** matches (1c67:0104).
- **Driver filename** (e.g. `presonus_quantum.sys`) and provider — tells us whether it’s custom or based on a known chip.
- **Resources** (IRQ, memory range / BARs) — compare with Linux `lspci -vv` and `/proc/iomem`.
- Optional: any public SDK, datasheet, or similar for the chip.

## Driver options after Stage 2

1. **Extend an existing driver**  
   If the Windows driver or chip name points to a known PCI audio chip (e.g. same as another interface that already has Linux support), add **1c67:0104** (and any quirks) to that driver’s PCI table and submit upstream or carry as a patch.

2. **New minimal ALSA PCI driver**  
   If the hardware is custom or undocumented:
   - Write a small kernel module that claims 1c67:0104 and registers an ALSA PCI driver.
   - Map the device’s BAR (we already have Region 0: 1 MiB at 0x64000000), implement probe/remove and basic PCM ops (or a minimal layout to get sound in/out).
   - This usually requires reverse engineering the Windows driver or the device (protocol, register layout, buffer layout).

3. **Out-of-tree module**  
   Same as (2), but kept in this repo or a separate tree until it’s ready for upstream.

## Repo layout for driver work

When you’re ready to code:

- **notes/windows_profile.txt** — Filled from Stage 2; source of truth for IDs and resources.
- **notes/DIAGNOSIS_RESULT.md** — Linux PCI details and BAR.
- Kernel docs: [Writing an ALSA Driver](https://docs.kernel.org/sound/kernel-api/writing-an-alsa-driver.html), [PCI drivers](https://docs.kernel.org/PCI/pci.html).

Once Windows profiling is done, we can use `windows_profile.txt` and this doc to sketch the actual driver (e.g. skeleton ALSA PCI driver and where to plug in 1c67:0104 and the BAR).
