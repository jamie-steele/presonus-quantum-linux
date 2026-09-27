# No sound diagnostics

Start with [the current testing guide](LINUX_TESTING.md) and
[current evidence](../notes/CURRENT_STATUS.md). The default driver is
`snd-quantum`; old `snd-quantum2626` register parameters do not apply to it.

1. Inspect `lspci -nnk -d 1c67:0104` and `/proc/asound/cards`. No PCI function
   suggests a Thunderbolt authorization/connection issue. No ALSA card despite a
   bound function needs the corresponding kernel probe logs.
2. Check the kernel matches the installed module and headers. For releases, use
   `dkms status` and `modinfo snd-quantum`; inspect module-signing failures under
   Secure Boot. A file on disk does not prove that version is loaded.
3. Check `wpctl status` and the selected profile/default sink. The 48 kHz UCM
   profile should expose 13 stereo outputs and 26 mono inputs. One generic
   multichannel pair suggests UCM selection/configuration trouble.
4. Confirm the installed selector matches ALSA driver name `snd-quantum` and that
   the WirePlumber file format matches 0.4 (Lua) or 0.5 (SPA-JSON). The correct UCM
   profile can be parsed even when the live desktop graph has failed.
5. Inspect bounded kernel and user-service logs for DMA/IOMMU errors, allocation
   timeouts, or adapter activation failures. Stop playback/recovery experiments
   on these faults and retain sanitized evidence before changing state.

Do not clear kernel logs or use arbitrary MMIO writes to diagnose ordinary audio
configuration. A service restart or driver reload is a separate live operation
that can interrupt audio and trigger known discovery faults.

[Old register-probing notes](historical/INHOUSE_NO_SOUND_DEBUG.md) remain available
as historical research, not current operating instructions.
