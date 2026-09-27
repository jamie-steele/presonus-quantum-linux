# PreSonus Quantum Linux Agent Router

PreSonus Quantum Linux is a discovery, research, desktop-integration, and experimental release
project. Nicholas Johnson's upstream RFC `snd-quantum` is the default driver; the in-house
`snd-quantum2626` is a research fallback. Only Quantum 2626 is enabled and hardware-tested,
with separate evidence for each backend. This file is the small, always-loaded router;
durable guidance lives under `docs/agents/`.

## Loading Protocol

1. Read this file.
2. Read `docs/agents/index.yml`.
3. Load only the entries whose `load_when` conditions match the task.
4. For substantial or multi-session work, check `docs/agents/tasks/index.yml` before creating or
   resuming a task record. Follow its `archives` route to `closed/index.yml` for completed work
   and check both indexes before assigning a new task ID.
5. Expand context only when repository evidence or a linked dependency requires it.

## Non-Negotiable Rules

- Run `git status --short` before editing and preserve unrelated user changes, generated files, and
  local reverse-engineering artifacts.
- Treat repository evidence as authoritative. Distinguish confirmed hardware observations, static
  reverse-engineering findings, hypotheses, and stale documentation.
- Read `notes/CURRENT_STATUS.md` before relying on older summaries. Verify upstream claims
  against the source identified by `driver/upstream.lock` and fallback claims against
  `driver/snd-quantum2626.c`; never transfer one backend's hardware acceptance to the other.
- Never add proprietary driver binaries, large traces, credentials, host identifiers, or generated
  Ghidra/build state. Respect `.gitignore` and keep temporary captures outside the repository unless
  the user asks to preserve a sanitized result.
- Do not run `sudo`, load or unload kernel modules, stop audio services, write MMIO registers, or
  perform hardware sweeps unless the user explicitly requests live hardware testing. Static
  inspection and ordinary compilation do not authorize live device mutation.
- Keep experimental register writes narrowly scoped and reversible. Do not turn an inferred offset
  into a broad probe or claim it is confirmed without recorded evidence.
- Update the relevant canonical note when a register, initialization, DMA, IRQ, or device-readiness
  conclusion materially changes; do not leave the conclusion only in chat or a transient log.

## Work And Verification

- Use the narrowest relevant check first. Driver compilation depends on headers for the running
  kernel and is not proof that a hardware path is safe or functional.
- Keep code changes separate from live load/playback/capture tests when the latter were not
  explicitly authorized.
- Report files changed, checks run, skipped live tests, and whether conclusions are observed or
  inferred.

## Entry Points

- Documentation contract: `docs/agents/README.md`
- Repository and source-of-truth map: `docs/agents/repository.md`
- Driver changes: `docs/agents/driver-development.md`
- Reverse engineering: `docs/agents/reverse-engineering.md`
- Live Linux/device testing: `docs/agents/hardware-testing.md`
- ALSA/PipeWire/JACK integration: `docs/agents/desktop-audio.md`
- Durable tasks: `docs/agents/tasks/index.yml`
