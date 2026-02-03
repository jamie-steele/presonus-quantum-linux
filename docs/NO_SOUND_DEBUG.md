# No sound – things to check

After running `aplay -D plughw:4,0 ...` with wireplumber stopped, if the stream runs but you hear nothing:

## 1. Confirm what the driver is doing

Reload with the updated driver (it now logs prepare/trigger to dmesg), then:

```bash
sudo dmesg -C
systemctl --user stop wireplumber pipewire-pulse
aplay -D plughw:4,0 -r 48000 -f S16_LE -c 2 /usr/share/sounds/alsa/Front_Center.wav
sudo dmesg | grep -E "quantum|prepare|trigger|CONTROL|dma_addr"
```

You should see:

- `prepare playback: dma_addr=0x... buffer_size=...` – DMA address and size we program
- `prepare: CONTROL 0x100 = 0x8 (rate=48000 format=16)`
- `trigger START playback: CONTROL 0x100 was 0x... now 0x8`
- `trigger STOP playback: CONTROL 0x100 was 0x... now 0x0`

If those appear, the driver path is running; the problem is likely register meaning or missing setup.

## 2. Likely causes

- **Wrong buffer register** – Ghidra gave 0x10300/0x10304; the real DMA buffer registers might be elsewhere. Search the Windows driver for other MMIO writes with a buffer-like address.
- **Missing buffer size / period** – The device may need buffer length or period size in another register; we don’t program that yet.
- **Missing sample rate / format** – The device may need rate (e.g. 48000) or format (16-bit) in a register; we don’t program that yet.
- **Wrong control value** – 0x8 might not be “start playback”. Try other values (e.g. 0x1, 0x9) in Ghidra or by changing the driver and testing.
- **Physical output** – The Quantum has many outputs; make sure the cable/monitor is on the output the hardware uses for “main” or “playback 1/2”. Check the unit’s mixer or manual.

## 3. Dump MMIO during playback

Load with `dump_on_trigger=1` and capture the first 64 bytes at prepare and trigger:

```bash
sudo modprobe snd-quantum2626 dump_on_trigger=1
# stop wireplumber, run aplay, then:
sudo dmesg | grep -E "MMIO|prepare|trigger" | tail -80 > notes/MMIO_during_playback.txt
```

Compare with `notes/MMIO_BASELINE.md` to see which registers change when we start/stop.

## 4. Next RE steps

- In Ghidra: find where the Windows driver **writes** buffer address, buffer size, sample rate, and stream start/stop. Confirm offsets and values.
- Update `notes/REGISTER_GUESSES.md` and the driver’s `QUANTUM_REG_*` defines accordingly.
