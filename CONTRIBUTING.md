# Contributing

The main kernel backend is Nicholas Johnson's `snd-quantum` RFC. Start with the
[original RFC](https://lore.kernel.org/all/20260820083646.11383-2-nicholas.johnson-opensource@outlook.com.au/)
and read its current mailing-list discussion. Our research, packaging, test tools,
and UCM/WirePlumber integration remain maintained in this repository.

## Collaborating on the driver

[EMATech/quantum](https://github.com/EMATech/quantum) is an **unofficial contributor
collaboration repository**, providing an editable out-of-tree adaptation of Nicholas's
RFC for shared development and local review. It is not the official RFC source or
publication channel; our release monitor follows the official mailing-list submission.
Record the exact base commit and separate driver changes from local build files.
A GitHub pull request there is collaboration, not submission to the Linux kernel.
Do not describe an unreviewed collaboration-branch commit as a new upstream RFC.

For upstream submission, apply the original series in a Linux kernel checkout
(for example with `b4 am MESSAGE_ID` and `git am`), then port your changes under
`sound/pci/quantum/`. Preserve original authorship and SPDX notices. A flattened
out-of-tree patch must be rebased to kernel paths; excluding a root Makefile alone
does not make such a patch applicable to the kernel tree.

1. Make focused commits with a problem description, fix, limitations, and your
   own `Signed-off-by` when you can attest to the Developer Certificate of Origin.
2. Build the affected driver, run `scripts/checkpatch.pl` on the patches, and run
   sparse where available. Report hardware tests separately from compilation.
3. Generate patches against the stated base with `git format-patch --cover-letter
   --base=<base-commit> <base-commit>..HEAD`. Use an RFC subject prefix for work
   seeking design feedback and include a revision changelog for later versions.
4. Run `scripts/get_maintainer.pl` from that kernel tree on the resulting patches.
   Check its current recipients and the RFC thread. Include Nicholas Johnson
   (`nicholas.johnson-opensource@outlook.com.au`) and the relevant sound list,
   currently `linux-sound@vger.kernel.org`, rather than hard-coding a stale
   maintainer roster.
5. Inspect `git send-email --dry-run` with those recipients, then send the reviewed
   series with `git send-email`. Link the original RFC and describe what changed.
   Send review/test feedback as a plain-text reply to the relevant RFC message;
   keep quoted context trimmed and avoid top-posting.

Coordinate with Nicholas before presenting a full replacement series as his next
revision. Your own follow-up patches should clearly identify their author and base.
Do not invent `Tested-by`, `Reviewed-by`, or another contributor's sign-off.

The authoritative procedure is the kernel's
[submitting-patches guide](https://docs.kernel.org/process/submitting-patches.html).
Its commands and the current maintainer tree take precedence over examples here.

## ALSA profiles and desktop integration

Send repository UCM/WirePlumber fixes here first with exact driver revision,
alsa-lib/PipeWire/WirePlumber versions, parsed endpoints, and any physical test
results. Preserve the 48 kHz desktop baseline unless a new profile is independently
validated. Both `snd-quantum` and legacy `snd-quantum2626` selectors must work.

UCM is a userspace contribution to
[alsa-project/alsa-ucm-conf](https://github.com/alsa-project/alsa-ucm-conf), separate
from the kernel RFC. Prepare a focused change against that repository's current
layout, run its current validation tools, and include a sanitized ALSA report and
model-specific matching. Read its contribution instructions before opening a PR.
WirePlumber policy belongs in a separate change; it is not part of an ALSA kernel
patch. Existing local profile preparation is not evidence of upstream acceptance.

## Research and releases

Keep observed hardware behavior separate from source analysis and hypotheses.
Put durable conclusions in `notes/CURRENT_STATUS.md` or the relevant protocol note.
Do not upload vendor binaries, bulk traces, generated analysis state, or host IDs.

Release tooling and distro coverage are described in [RELEASES.md](docs/RELEASES.md).
Run `python3 -m unittest discover -s tests -v` for release logic and use the
disposable distro checks for DKMS and packaging. None of these checks load a
module or prove physical audio behavior.
