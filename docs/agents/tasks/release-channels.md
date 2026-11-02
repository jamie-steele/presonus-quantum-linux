# TASK-028 Development staging and promoted APT channels

## Status

Active

## Objective and authority

User requested dev -> staging -> master, staging experimental releases and APT
opt-in, and explicitly selected separate staging/master APT suites. Preserve the
sample-rate candidate as offline/unpublished work. TASK-027 is reserved for that
local candidate and must not be reused.

## Design

See [release-channel contract](../../RELEASE_CHANNELS.md). Staging builds use
N~staging.RUN_ID, master uses final N. Master alone signs and deploys both suites;
no signing environment access is added to staging. Existing experimental clients
retain their channel, and master revision 5 bootstraps the stable suite. Publishing
new final revision 6 remains an explicit later master dispatch.

## Verification and publication evidence

- 70 local tests passed; all six native lifecycle and four signed-APT jobs passed.
- PR #42 feature -> dev, PR #43 dev -> staging, PR #44 staging -> master merged.
- Staging publication run 41399433188 uploaded revision 6~staging.41399433188.
- Public readback found GitHub normalizes tilde asset filenames to dots, causing
  APT discovery to skip the uploaded candidate. Correct discovery/checksum mapping
  and explicit retry-safe transport filenames before accepting public channels.
- Sample-rate candidate remains offline and excluded; no host audio mutation.

## Remaining work

- Offline and hosted lifecycle/channel validation.
- Preserve branch histories while merging feature -> dev -> staging -> master.
- Publish the first tested staging package and deploy both signed suites.
- Independently verify each suite's candidate and authenticated download.
- Record publication/verification evidence; no host audio mutations authorized.
