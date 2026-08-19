# Repository Description

## Short Description (for GitHub About section)

Experimental PreSonus Quantum family Linux support; Quantum 2626 playback, capture, and PipeWire integration are live-proven

## Detailed Description

This repository aims to provide community-developed Linux audio support for the
full PreSonus Quantum family. Today, its experimental Linux ALSA PCI driver is
enabled and hardware-tested only for the Quantum 2626 Thunderbolt 3 interface.
On owned hardware, the current driver reaches the solid-blue ready state and
provides live-proven playback, capture, and bounded duplex operation through
direct ALSA and PipeWire.

### Key Features

- Out-of-tree ALSA PCI driver for Linux
- Fixed 48 kHz, 26-channel, S32_LE duplex transport
- ALSA UCM profile with 13 stereo output sinks and 26 independent mono inputs
- Hardware DMA page tables, interrupts, and position tracking
- TCI initialization and channel routing recovered primarily from the macOS DriverKit extension

### Target Audience

- Linux audio professionals and enthusiasts
- Music producers using Linux DAWs
- Audio engineers requiring professional interfaces on Linux
- Developers interested in hardware driver development
- Reverse engineering researchers

### Project Status

Active development. Audio works at the fixed, live-proven 48 kHz profile.
Sample-rate switching, mixer controls, MIDI, hot removal, and physical digital-I/O
validation are not implemented or proven yet.

### Website/Homepage (if applicable)

https://github.com/jamie-steele/presonus-quantum-linux
