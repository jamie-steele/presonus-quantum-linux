# Repository Description

## Short Description (for GitHub About section)

PreSonus Quantum Linux research, desktop integration, and experimental releases of Nicholas Johnson's upstream RFC driver

## Detailed Description

This repository develops discovery/research, desktop integration, and experimental
distribution around Nicholas Johnson's official `snd-quantum` RFC. The RFC is the
default backend, with the earlier in-house driver retained for research and recovery.
Only Quantum 2626 is enabled and hardware-tested. EMATech/quantum is an unofficial
collaboration adaptation; official RFC submissions drive release detection.

### Key Features

- Pinned official RFC source with experimental DKMS releases and distro build checks
- Fixed 48 kHz, 26-channel, S32_LE desktop profile
- ALSA UCM profile with 13 stereo output sinks and 26 independent mono inputs
- Hardware DMA page tables, interrupts, and position tracking
- Protocol discovery and hardware evidence, including the earlier in-house implementation

### Target Audience

- Linux audio professionals and enthusiasts
- Music producers using Linux DAWs
- Audio engineers requiring professional interfaces on Linux
- Developers interested in hardware driver development
- Reverse engineering researchers

### Project Status

Experimental. In-house playback/capture results and mixed RFC hardware evidence are
reported separately. The RFC implements rate/clock controls, MIDI, and removal handling;
sustained stability, high rates, and physical digital-I/O validation remain incomplete.

### Website/Homepage (if applicable)

https://github.com/jamie-steele/presonus-quantum2626-linux
