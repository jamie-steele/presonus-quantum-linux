# Development and research scripts

Run documented commands from the repository root. Scripts are grouped by purpose;
filenames and command-line arguments are unchanged.

| Directory | Purpose | Entry points |
| --- | --- | --- |
| [release/](release/) | RFC detection, packaging, and disposable distro validation | `upstream_release.py`, `build_native.py`, `test-distro.sh` |
| [linux/](linux/) | Linux driver status, audio tests, reload helper, and loopback measurements | `linux_test_driver.sh`, `quantum2626_loopback_soak.py` |
| [windows/](windows/) | Windows device collection, driver extraction, and trace analysis | `windows_capture_quantum.ps1`, `windows_re_strings.ps1` |
| [ghidra/](ghidra/README.md) | Ghidra setup, launchers, and static-analysis scripts | `setup_ghidra_linux.sh`, `run_ghidra_analysis.sh` |
| [experiments/](experiments/) | Historical register probes, LED trials, and speculative driver experiments | Research references; inspect against current source before use. |

For example, the existing offline loopback self-test is now:

```sh
python3 scripts/linux/quantum2626_loopback_soak.py self-test
```

Hardware-facing scripts can reload modules, stop audio services, capture system
state, or write registers. Their presence here does not establish compatibility
with the current upstream backend or authorize execution. `experiments/` retains
historical research tools without presenting them as routine development checks.
Release container scripts may download artifacts and run Docker;
use their documented inputs and boundaries.

See [Contributing](../CONTRIBUTING.md), [Linux testing](../docs/LINUX_TESTING.md),
[continuity testing](../docs/LOOPBACK_CONTINUITY_TESTING.md),
[release tooling](../docs/RELEASES.md), and the
[research index](../research/README.md) for prerequisites and evidence limits.
