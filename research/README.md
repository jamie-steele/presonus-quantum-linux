# Research and evidence

This directory groups protocol findings, historical observations, and Windows
reference material away from the native driver and release tooling.

| Path | Purpose |
| --- | --- |
| [notes/CURRENT_STATUS.md](notes/CURRENT_STATUS.md) | Consolidated status; read before relying on older findings. |
| [notes/TCI_PROTOCOL.md](notes/TCI_PROTOCOL.md) | Recovered mailbox and audio transport protocol. |
| [notes/CHANNEL_ROUTING.md](notes/CHANNEL_ROUTING.md) | Channel layout and observed routing. |
| [notes/REGISTER_GUESSES.md](notes/REGISTER_GUESSES.md) | Register hypotheses and confidence. |
| [notes/GHIDRA_FINDINGS_SUMMARY.md](notes/GHIDRA_FINDINGS_SUMMARY.md) | Consolidated static Windows analysis. |
| [notes/analysis/](notes/analysis/README.md) | Selected retained logs and analysis outputs. |
| [notes/archive/](notes/archive/README.md) | Earlier session summaries and superseded approaches. |
| [windows/](windows/README.md) | Windows collection metadata; proprietary inputs stay local and ignored. |

The former top-level `notes/` and `driver-reference/` directories now live at
`research/notes/` and `research/windows/`. Dates, hashes, and hardware observations
remain historical evidence, not new acceptance. Audio fixtures moved from
`samples/` to `tests/fixtures/audio/`.

Repeatable analysis scripts remain in `scripts/ghidra/`; installed Ghidra tools
remain local under ignored `tools/`. Generated Ghidra projects and databases do
not belong in Git. Preserve unique findings in a concise note instead.
