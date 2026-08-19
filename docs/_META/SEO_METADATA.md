# Repository Metadata Guidance

Discovery metadata may describe the full-family goal, but must distinguish that
roadmap from the Linux driver that exists today. Do not advertise the vendor
hardware's maximum specification as implemented Linux support.

## Accurate Search Terms

- PreSonus Quantum 2626 Linux
- PreSonus Quantum Linux
- PreSonus Quantum family Linux support
- Linux ALSA Thunderbolt audio driver
- Quantum 2626 PipeWire
- out-of-tree ALSA PCI driver
- 48 kHz multichannel duplex audio

## Accuracy Boundaries

- State that playback and capture work on tested hardware.
- State that full Quantum family support is a goal, while the Quantum 2626 is
  currently the only enabled and hardware-tested model.
- Do not imply that the Thunderbolt driver supports the USB-C Quantum ES or HD
  models; those models require separate transport investigation.
- Describe the currently supported Linux contract as fixed 48 kHz, 26-channel,
  S32_LE duplex audio.
- Do not advertise 96 or 192 kHz Linux support until sample-rate switching is
  implemented and live-proven.
- Do not claim a sub-1 ms Linux round-trip latency result without a repeatable
  measurement.
- Describe the macOS DriverKit extension as the primary source for the working
  TCI, DMA, IRQ, and channel-layout implementation.
- Keep limitations visible: physical S/PDIF/ADAT routing, mixer controls, MIDI,
  high-rate profiles, and hot removal still need work.

Use `docs/_META/PROJECT_DESCRIPTION.md` for the GitHub About text and
`docs/_META/GITHUB_TOPICS.md` for suggested repository topics. The root
`README.md` and `notes/CURRENT_STATUS.md` remain authoritative for public and
technical status respectively.
