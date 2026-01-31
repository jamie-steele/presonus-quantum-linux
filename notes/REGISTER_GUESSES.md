# Register guesses (from Ghidra / reverse-engineering)

Fill in as you identify MMIO offsets from `pae_quantum.sys` or experimentation.

| Offset | Suspected role | Source / notes |
|--------|----------------|----------------|
| 0x04   | (known: 0x01030060 at load) | ID / version / config? |
| 0x08   | (known: 0x00000010 at load) | ? |
| …      | … | … |

Baseline at load: `notes/MMIO_BASELINE.md`. During playback (with `dump_on_trigger=1`): `notes/MMIO_during_playback_*.txt`.
