# Development, staging and promoted releases

Changes flow through **dev -> staging -> master**. Feature PRs target dev;
only dev promotes into staging, and only staging promotes into master.
The GitHub default branch remains master. The signing/deployment control plane
also remains restricted to master; staging never receives the APT signing key.

| Branch | Behavior | APT suite |
| --- | --- | --- |
| dev | Build, unit, native lifecycle and signed-APT checks; no package publication | None |
| staging | Each eligible push builds and tests a uniquely versioned experimental package | experimental |
| master | Promoted source; a separate explicit native workflow dispatch publishes the final package | stable |

Both channels contain an **unmerged experimental RFC driver**. Stable identifies
the promoted package channel, not upstream kernel acceptance, universal hardware
support or production qualification. The sample-rate candidate is not included
merely because channel infrastructure has been added.

## Versions and promotion

`packaging/native/revision` holds the next positive final revision, initially 6.
A staging build uses `N~staging.GITHUB_RUN_ID`; a master release uses `N`.
Debian/RPM prerelease ordering makes the final revision newer than its staging
builds. Every staging push has an immutable identity. GitHub release asset filenames use
`N.staging.BUILD` because GitHub normalizes tildes; the DEB/RPM metadata retains
`N~staging.BUILD`. APT discovery verifies the original checksum and restores the
version spelling locally without changing package bytes. Published checksum entries
use the transport filenames so direct downloads remain verifiable with `sha256sum`. Both candidate and synthetic
next-revision packages pass the full native lifecycle and APT test matrices.

A branch merge never silently publishes a master package. After a reviewed
staging -> master promotion, dispatch `native-packages.yml` on master with the
existing RFC source tag. The publication job also verifies that master contains
the staging branch. Its entire build/lifecycle/APT matrix must pass. Promotion
rebuilds with the final version and retests those bytes; it does not rename a
staging DEB or claim the two packages are byte-identical.

After publishing final N, bump the development revision to N+1 for the next
candidate. A staging N~ build cannot replace an installed final N, and changed
bytes cannot overwrite an existing final release asset.

For a newly pinned RFC whose immutable source tag does not exist yet, dispatch
`rfc-release.yml` on staging with the exact official series ID first. Source
publication remains an experimental RFC snapshot, not a stable driver release.
The default-branch schedule discovers/checks RFCs but does not auto-publish them
or bypass staging promotion.

## Signed APT channels

The public URL and signing fingerprint stay unchanged:
`https://jamie-steele.github.io/presonus-quantum-linux`.
A single master-controlled Pages deployment rebuilds **both** signed suites from
complete, tested release assets. A staging publication cannot erase or populate
the stable index. Staging versions are rejected from stable during discovery and
repository assembly. Published legacy integer revisions remain available as the
bootstrap master baseline and in experimental for existing subscribers.

Download and inspect exactly one source file:

- `quantum-staging.sources`: opt in to experimental staging packages.
- `quantum-stable.sources`: follow promoted master packages.
- `quantum.sources`: backward-compatible alias for experimental; existing users
  continue receiving staging updates without an unexpected channel switch.

Follow the key verification and installation procedure in [RELEASES.md](RELEASES.md),
substituting the selected source file. Install it as the single
`/etc/apt/sources.list.d/quantum.sources` entry; do not leave a second Quantum
source file behind when switching. Both suites are opt-in (`NotAutomatic` with
`ButAutomaticUpgrades`); ordinary upgrades follow the explicitly installed package.
APT does not automatically downgrade a newer installed staging package when
switching to an older stable baseline. Inspect `apt-cache policy quantum-dkms`
and decide separately whether to wait for a newer stable version or explicitly
request a downgrade. No driver/service operation is performed by this policy.

Check each deployed suite without installing anything:

```bash
python3 scripts/release/apt_repository.py verify \
    https://jamie-steele.github.io/presonus-quantum-linux --suite experimental
python3 scripts/release/apt_repository.py verify \
    https://jamie-steele.github.io/presonus-quantum-linux --suite stable
```

GitHub release upload, signed metadata deployment, fresh authenticated client
selection, host installation and physical-audio acceptance are separate results.
Release success must include a fresh client read-back for the intended suite.

## Bootstrap

Bring the existing master fixes into dev through a normal merge, then promote
dev -> staging -> master with the channel tooling. Preserve all branch histories;
never reset/rebase shared branches. The first staging push may finish before
master has the new APT control plane; after the infrastructure promotion, dispatch
the APT workflow on master to publish both suites. Existing master revision 5
provides the stable baseline. A new final revision 6 requires a later explicit
master release dispatch; it is not part of the initial staging publication.
