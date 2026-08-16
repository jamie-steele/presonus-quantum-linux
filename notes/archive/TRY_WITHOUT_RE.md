# Try to Get It Working Without Reverse Engineering

We already have the PCI identity (1c67:0104). This is a “for shits” attempt: add that ID to an existing kernel sound driver at runtime and see if anything works.

## What we’re doing

- The kernel can add a **dynamic PCI ID** to a driver via `/sys/bus/pci/drivers/<driver>/new_id`.
- We try adding **1c67 0104** (PreSonus Quantum 2626) to **snd_hda_intel** (the common HD Audio driver).
- If the device speaks HD Audio behind the Thunderbolt bridge, the driver might probe and create an ALSA card. If not, the probe will fail and we’re no worse off.

**Caveat:** The Quantum shows up as PCI class **0401** (Multimedia controller), not **0403** (HD Audio). So it might not be HD Audio at all, and this try may fail. Some kernels or drivers also reject `new_id` for non-Intel vendor IDs (e.g. “Invalid argument”) — then we’re out of luck without a real driver or reverse engineering.

## Run it

From the repo (with the Quantum 2626 connected):

```bash
sudo ./scripts/try_quantum_hda.sh
```

Then:

- `aplay -l` and `arecord -l` — see if a new card appeared.
- `dmesg | tail -30` — if it failed, the probe often logs why.

If a card appears, you’re done. If not, the script removes the dynamic ID; the next step would be real driver work or reverse engineering (e.g. Stage 2 on Windows).
