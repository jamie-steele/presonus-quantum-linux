# Live Hardware Testing

Live tests can unload kernel modules, interrupt desktop audio, write device registers, and create
misleading results when the host, firmware, or module parameters are not recorded. Do not cross this
boundary unless the user explicitly asks for a live device test.

## Before Running

1. Confirm the Quantum 2626 is connected and the intended host/session can tolerate audio service
   interruption.
2. Inspect the selected script before execution; scripts may invoke `sudo`, stop PipeWire services,
   unload modules, or write MMIO registers.
3. Record the current commit, kernel version, PCI identity, module path/hash, and exact module
   parameters.
4. Choose one bounded hypothesis and its expected observation. Do not combine unrelated register
   changes into one trial.

Start with `docs/LINUX_TESTING_GUIDE.md` and the narrowest relevant helper under `scripts/`. Prefer
card discovery from repository helpers over assuming a fixed ALSA card number.

## Evidence To Retain

- Exact command or script and parameters.
- Whether module load, ALSA enumeration, IRQ activity, LED state, playback/capture, and cleanup each
  succeeded.
- Relevant dmesg excerpts with timestamps and an explanation of what they establish.
- Unexpected host state, timeouts, xruns, or fallback paths.

Keep raw or large captures outside Git. Promote concise findings to `notes/CURRENT_STATUS.md`,
`notes/REGISTER_GUESSES.md`, or another existing canonical note.

## Stop Conditions

Stop and report rather than widening the experiment when the device identity differs, the module
cannot unload cleanly, the expected audio session cannot be restored, a register target is not the
one reviewed, or a result would require a broad undocumented write sweep.

