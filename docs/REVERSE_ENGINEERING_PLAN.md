# Reverse-Engineering Plan: Quantum 2626 → Real Audio

Goal: identify the device’s MMIO register layout and DMA/buffer behavior so the Linux driver can program playback and capture and move real audio.

---

## Phase 1: Gather artifacts (Windows + Linux)

### 1.1 Windows – next run

Run on a Windows machine with the Quantum 2626 and the PreSonus driver installed.

1. **Extract driver strings**  
   Run (from the repo `scripts/` folder):
   ```powershell
   cd path\to\Quantum2626\scripts
   .\windows_re_next_run.ps1
   ```
   That finds `pae_quantum.sys`, runs string extraction, and writes:
   - `../driver-reference/strings_pae_quantum.txt` (all strings, for search/grep)
   - `../driver-reference/strings_interesting.txt` (filtered: offsets, PCI, buffer, etc.)

2. **Copy driver binary to repo**  
   Ensure `pae_quantum.sys` is in `driver-reference/` (or in a local folder you keep for Ghidra). The script reports the source path.

3. **Optional: full driver copy**  
   Re-run or use existing:
   ```powershell
   .\windows_collect_all.ps1
   ```
   Copies driver + INF + resources to Desktop; move `strings_*.txt` and any new files into the repo.

### 1.2 Linux – baseline and “during playback” dumps

1. **Capture MMIO at load**  
   After loading the driver:
   ```bash
   ./scripts/capture_mmio_baseline.sh
   ```
   Saves current MMIO lines from dmesg to `notes/MMIO_baseline_<date>.txt`.

2. **Capture MMIO at prepare/trigger** (optional, needs `dump_on_trigger=1`)  
   With the driver built with dump-on-trigger support:
   ```bash
   sudo modprobe snd_quantum2626 dump_on_trigger=1
   # Stop wireplumber so nothing else uses the card:
   systemctl --user stop wireplumber
   aplay -D plughw:4,0 -r 48000 -f S16_LE -c 2 /dev/zero &
   sleep 3
   sudo dmesg | grep -E "MMIO|quantum" | tail -80 > notes/MMIO_during_playback.txt
   kill %1 2>/dev/null
   systemctl --user start wireplumber
   ```
   Compare `MMIO_during_playback.txt` with `MMIO_baseline_*.txt` to see which registers change when the stream starts/stops.

---

## Phase 2: Static analysis (Ghidra / IDA)

1. **Load** `pae_quantum.sys` in Ghidra (or IDA).  
   - Format: PE kernel driver (Windows x64).  
   - Use the strings files to find likely register names, offsets (e.g. `0x10`, `buffer`, `control`).

2. **Find MMIO usage**  
   - Search for patterns: base address + offset, or constants that match BAR 0 offsets (0x00, 0x04, 0x08, …).  
   - Our baseline: 0x04 = 0x01030060, 0x08 = 0x00000010; 0x0c+ often 0xffffffff.  
   - Look for read/write of a mapped base (e.g. from `MmMapIoSpace` or similar) and all additive offsets.

3. **Map likely roles**  
   - Buffer base / size  
   - Format (sample rate, bits, channels)  
   - Start/stop / enable bits  
   - Position or “period done” / interrupt status  
   - DMA descriptors if present  

4. **Document**  
   - Add a short “Register guesses” section to `notes/MMIO_BASELINE.md` or a new `notes/REGISTER_GUESSES.md` with offset → suspected role and source (e.g. “Ghidra: write 1 to 0x?? before starting”).

---

## Phase 3: Driver changes (Linux)

1. **Implement prepare**  
   - From Phase 2, program buffer address(es), format, sample rate, period size into the right MMIO offsets.  
   - Use `runtime->dma_addr`, `runtime->period_size`, `runtime->rate`, etc.

2. **Implement trigger**  
   - Start: set “enable” or “start” bit(s) in the mapped register(s).  
   - Stop: clear those bits (and optionally reset position).

3. **Implement pointer**  
   - Either read a position register and convert to frames, or keep using the existing IRQ + period_elapsed and (optionally) refine with a position read.

4. **Refine IRQ handler**  
   - If you find an interrupt status/ack register, read it in the handler and only call `snd_pcm_period_elapsed()` when the device reports a period (and ack the interrupt).

5. **Test**  
   - `aplay -D plughw:CARD,0 ...` and `arecord -D plughw:CARD,0 ...` with real files; check for sound and xruns.

---

## Scripts and files

| Item | Purpose |
|------|--------|
| `scripts/windows_re_strings.ps1` | Extract all + interesting strings from pae_quantum.sys → driver-reference/ |
| `scripts/windows_re_next_run.ps1` | Full “next run”: run strings, print copy + Ghidra checklist |
| `scripts/capture_mmio_baseline.sh` | Save dmesg MMIO lines to notes/MMIO_baseline_YYYYMMDD_HHMM.txt |
| `scripts/probe_during_playback.sh` | Run aplay, capture dmesg to notes/ (use with dump_on_trigger=1) |
| `notes/MMIO_BASELINE.md` | Known BAR 0 values at load (update as you find more) |
| `notes/REGISTER_GUESSES.md` | You create: offset → suspected role from Ghidra |

---

## Optional: dump-on-trigger in the driver

The driver can support a module parameter `dump_on_trigger`. When set, it logs the same MMIO region in `prepare` and in `trigger(START/STOP)`. That gives you “at rest”, “at prepare”, “at start”, “at stop” snapshots without implementing real programming yet. See driver README and the param in `snd-quantum2626.c`.
