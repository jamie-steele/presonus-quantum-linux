# Agent Documentation Contract

`AGENTS.md` is the concise router. This directory holds focused, durable guidance that helps an
agent choose the minimum useful context without duplicating the project's canonical technical
documentation.

## Index Contract

`docs/agents/index.yml` is the machine-readable entrypoint. Each entry has:

- a stable `id`;
- a repository-relative `path`;
- a short `summary`;
- concrete `load_when` conditions;
- related entry IDs where useful; and
- a `status` of `current`, `proposed`, or `historical`.

An index is a routing map, not a reading checklist. Add a focused document only when it owns a
distinct concern. Link to source documents instead of copying large sections from them.

## Sources Of Truth

- Product and project status belongs in the root `README.md` and focused files under `notes/`.
- Driver behavior belongs in `driver/snd-quantum2626.c`, with build usage in `driver/README.md`.
- Repeatable operator procedures belong under `docs/` and `scripts/`.
- `docs/agents/` records routing, safety boundaries, source precedence, and task state. It must not
  become a competing hardware or register reference.

When sources disagree, verify behavior against source code and fresh evidence, then reconcile the
stale canonical document as part of the same change when it is in scope.

## Maintenance

- Keep paths repository-relative and verify every indexed path exists.
- Prefer target-independent wording and skill IDs; do not add tool-specific routing keys.
- Keep temporary logs, generated analysis, and machine-specific state out of this directory.
- Update `docs/agents/tasks/index.yml` whenever a durable task is created, expanded, moved, or
  closed.

