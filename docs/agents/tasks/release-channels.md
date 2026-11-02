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

## Remaining work

- Offline and hosted lifecycle/channel validation.
- Preserve branch histories while merging feature -> dev -> staging -> master.
- Publish the first tested staging package and deploy both signed suites.
- Independently verify each suite's candidate and authenticated download.
- Record publication/verification evidence; no host audio mutations authorized.
