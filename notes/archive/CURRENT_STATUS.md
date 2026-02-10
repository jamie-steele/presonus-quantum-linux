# Quantum 2626 Linux Driver — Current Status

**Last updated:** 2026-02-05 (session end)  
**TL;DR:** Driver skeleton works (PCI, MMIO, ALSA, buffers, init/stream writes). Device never reports “ready” (blue LED stays blinking, no audio). Possible firmware/Thunderbolt lock-down or missing init path; no proof either way. Safe to park and pick up later.

---

## Goal

PreSonus Quantum 2626 (PCIe via Thunderbolt 3, PCI ID 1c67:0104). Get it working on Linux: ALSA card, playback/capture, solid blue LED = device initialized.

---

## What Works

- **Driver loads:** `snd_quantum2626.ko` probes, claims BAR0, maps MMIO, requests IRQ (MSI or legacy).
- **ALSA card:** Card and PCM show up; `aplay`/`arecord` can open the device (when card index is correct).
- **MMIO access:** Reads at 0x0, 0x4, 0x8, 0x10, 0x14, 0x104; writes at 0x8, 0x100, optional 0x4/0x10. Buffer registers 0x10300 / 0x10304 get DMA addresses on prepare.
- **Stream path:** prepare() programs buffer addresses and CONTROL 0x100 (and optional STATUS2/STATUS3); trigger start/stop writes 0x100 = value / 0.
- **Scripts:** Reload, listen test, init LED test, Ghidra trace (stream-start + init) all run. Card auto-detect in scripts. Samples folder for WAV tests.

---

## What Was Reverse-Engineered (Ghidra)

- **Init (FUN_140003d60):** Reads 0x0, 0x4, 0x8, 0x10, 0x14, 0x104, 0x10300, 0x10304. Trace found many writes in that function; most look like structure (device context), not MMIO. Only **0x8 = 0x8** and **0x100 = ?** are in our confirmed-MMIO set with known value.
- **Stream start (FUN_140002e30):** Writes 0x100 = 0x8; also 0x8 and 0x10 (values unknown). Output in `stream_start_writes.txt` (filtered to known MMIO).
- **Register map:** See `REGISTER_GUESSES.md`, `GHIDRA_FINDINGS_SUMMARY.md`. Confirmed MMIO: 0x0 (version), 0x4/0x8/0x10/0x14 (status), 0x100 (control), 0x104 (status5), 0x10300/0x10304 (buffers).

---

## What Was Tried (No Solid LED / No Audio)

1. **Init sequence**
   - 0x100 = 0 then 0x8.
   - 0x4 = 0, 0x8 = 0, 0x10 = 0 then 0x100 = 0, 0x8.
   - Full trace-derived list (many offsets in 0x0–0x300) — still blinking.
   - Minimal: 0x8 = 0x8, 0x100 = 0, 0x100 = 0x8; plus 20 ms delay after init.
2. **Control value sweep**
   - `init_control_value` (at probe) and `control_value` (at stream start): 0x8, 0x88, 0x10, 0x9, 0x80, 0x18, 0x1, 0x20, 0x40 tried via `init_led_test.sh` (one value at a time, 8 s to watch LED). No value produced solid LED.
3. **Stream path**
   - Optional `reg_status2_value` / `reg_status3_value` (0x8, 0x10) on prepare; tried 0 and 1. No audio.
4. **Observation**
   - Register 0x100 often reads back **0xffffffff** (write-only or ignored until “unlocked”).

---

## Where Things Stand

- **Working:** Skeleton, scripts, Ghidra workflow, register map, init/stream writes in code.
- **Not working:** Device never enters “ready” state (blue LED solid, audio). We never confirmed the hardware is accepting our sequences.
- **Possible causes (unproven):**
  - Thunderbolt / security (only “authorized” host/driver).
  - Firmware or multi-step handshake we don’t have.
  - Init or enable path outside the single `pae_quantum.sys` we analyzed (other driver, user-mode, service).
  - Correct sequence in the same driver but in a path we didn’t trace (e.g. different function or data-driven values).

---

## Repo Layout (Quick Reference)

| Path | Purpose |
|------|--------|
| `driver/snd-quantum2626.c` | ALSA PCI driver; init table, stream writes, module params. |
| `scripts/reload_quantum_driver.sh` | Release card, rmmod, insmod (optional MODPARAMS), unmask audio. |
| `scripts/linux_test_quantum.sh` | Reload, play WAV or silence, capture dmesg to `notes/`. |
| `scripts/linux_test_quantum_listen.sh` | Multiple param combos; plays `samples/*.wav` (e.g. snare). |
| `scripts/init_led_test.sh` | One `init_control_value` at a time, 8 s each, to watch LED. |
| `scripts/run_ghidra_analysis.sh` | Headless Ghidra + Python; default `trace_stream_start_writes.py`. |
| `scripts/run_ghidra_analysis.sh trace_init_writes.py` | Trace init (FUN_140003d60) writes → `init_writes.txt`, `init_writes_likely.txt`. |
| `scripts/ghidra/trace_*.py` | Stream-start and init MMIO write tracers. |
| `notes/REGISTER_GUESSES.md` | Register table and notes. |
| `notes/GHIDRA_FINDINGS_SUMMARY.md` | Confirmed offsets and next steps. |

---

## Module Params (Handy for Later)

- `do_init_sequence=0|1` — run init writes at probe (default 1).
- `init_control_value=-1|0x8|0x88|...` — value for final 0x100 write at init (-1 = 0x8).
- `control_value=-1|0x8|...` — value for 0x100 on stream start/trigger.
- `reg_status2_value=-1|0|1|...` — if ≥ 0, write to 0x8 on prepare.
- `reg_status3_value=-1|0|1|...` — if ≥ 0, write to 0x10 on prepare.
- `dump_on_trigger=1` — dump MMIO in dmesg at prepare/trigger.
- `reg_scan=1` — one-time MMIO dump 0x00–0xff at probe.

Example:  
`MODPARAMS="init_control_value=0x88" ./scripts/reload_quantum_driver.sh`

---

## If You Pick This Up Later

1. **Documentation:** This file + `REGISTER_GUESSES.md` + `GHIDRA_FINDINGS_SUMMARY.md` are the main status and register docs.
2. **Narrow the question:** e.g. On Windows, does the LED go solid before any user-mode or other driver loads? Any other driver/service that always loads with the Quantum?
3. **Community:** ALSA list, linux-sound, or PreSonus/audio reverse-engineering forums — short summary (no copyrighted content), ask if anyone has seen similar “never ready” on this chip or Thunderbolt audio.
4. **Driver code:** Init sequence is in `quantum_init_writes[]` in `snd-quantum2626.c`; you can replace or extend it from `init_writes_likely.txt` after re-running the init trace.

No wrong answer: park it, do one more targeted check, or ask the community and then park. The work is in a good state to resume or hand off.
