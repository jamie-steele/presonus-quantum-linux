# TASK-018 APT Metadata Renewal Recovery

## Status

Active (public feed recovered; permanent workflow change awaits publication)

## Objective

Restore authenticated APT updates and prevent a stale Pages deployment from
blocking all later metadata renewals. GitHub issue #29 follows the report in #22.

## Evidence And Discoveries

Observed on 2026-10-23:

- Public InRelease was dated October 6 with Valid-Until October 20. The daily
  renewal schedule already existed; it was not missing.
- Run `37511559403` completed signing on October 6 but its Pages deployment was
  still waiting. Workflow concurrency used `cancel-in-progress: false`; later
  renewals accumulated as cancelled pending runs behind that active run.
- The Pages environment allowed only master, with no required reviewers or wait
  timer returned by the API. The original reason for its stuck wait is unknown.
  No environment policy, secret, key, or package asset was changed.
- Cancelled only that stale APT run and dispatched the existing workflow on master
  as `40011960548`. The already-pending run `39993721479` was released and completed
  successfully, restoring the feed. Cancelled the redundant additional dispatch
  while it was still queued after live recovery verification.
- Public metadata signature verified with repository public key
  `5F839BAB8E48F6572044A442D98AC6B03628D7BE`; renewed validity ends
  `2026-11-06T19:30:47+00:00`.

## Changes

- Supersede old eligible APT runs, including waiting deployments. Unsuccessful,
  foreign, or non-default-branch triggers use separate concurrency identities so
  they cannot cancel legitimate publication.
- Bound signing/deployment execution and verify the live feed after deployment,
  using the public key retained in Git and requiring over seven days of validity.
- Document recovery, GitHub schedule limits, and independent signing-key expiry.
- Retain the 14-day metadata expiry and all existing APT authentication checks.

## Validation

- `python3 -m unittest discover -s tests -v`: 27 tests passed, including freshness
  boundaries, malformed date fields, and signature failure before metadata parsing.
- Live `apt_repository.py verify` passed against the pinned repository public key.
- Isolated HTTPS `apt-get update`, candidate selection, and authenticated package
  download passed for `20260820.rfc1.s1148921-2`. Temporary APT state only; no host
  install, kernel operation, or audio-service change.
- Workflow YAML parsed and `git diff --check` passed. Hosted execution of the
  modified workflow remains unverified until publication.

## Remaining Work

- Commit/review/publish the permanent change to master and verify its hosted run.
- Issue #29 remains open; no public reply was posted.
- Signing-key renewal before 2027-09-27 remains required; metadata renewal cannot
  extend key validity. No change claims Ubuntu 26.04 or physical audio acceptance.
