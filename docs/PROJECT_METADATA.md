# Repository metadata

Suggested GitHub About description:

> PreSonus Quantum Linux research, desktop integration, and experimental releases
> of Nicholas Johnson's upstream RFC driver

Suggested topics: `linux-driver`, `alsa`, `audio-driver`, `thunderbolt`, `presonus`,
`audio-interface`, `kernel-module`, `reverse-engineering`, `ghidra`, `pci-driver`,
`low-latency`, `music-production`, `professional-audio`, `daw`, `audio-recording`,
`linux-audio`, `out-of-tree-module`, `driver-development`, `hardware-programming`.

The audience includes Linux audio users, musicians, driver contributors, and
reverse-engineering researchers. Search terms may describe PreSonus Quantum 2626
Linux, ALSA Thunderbolt audio, PipeWire, and out-of-tree PCI drivers.

Keep metadata consistent with the [project overview](../README.md) and
[current status](../research/notes/CURRENT_STATUS.md):

- Credit Nicholas Johnson for the official `snd-quantum` RFC; EMATech is an
  unofficial collaboration adaptation, not the RFC publisher.
- Only Quantum 2626 is enabled and hardware-tested. Full-family support is a goal;
  Quantum ES/HD USB devices require separate transport investigation.
- Distinguish upstream RFC implementation, in-house hardware observations, and
  unproven behavior. The desktop profile is fixed at 48 kHz, 26-channel S32_LE.
- Do not turn advertised hardware specifications into Linux acceptance claims.
  High rates, physical digital I/O, sustained stability, and hot removal need
  their own evidence. Do not advertise a latency result without measurement.

This page consolidates the former `docs/_META/` description, topics, and search
metadata drafts. Repository settings are maintained separately from source files.
