# Durable Task Records

Use a task record for multi-session, risky, blocked, or discovery-heavy work. Small isolated edits do
not need one. Tasks preserve decisions and evidence; they are not a duplicate of source-of-truth
register notes or public documentation.

## IDs And Lifecycle

- Assign monotonic IDs such as `TASK-001` and a stable lowercase kebab-case slug.
- Use `backlog`, `active`, `blocked`, or `closed` as the status.
- Add every task to `docs/agents/tasks/index.yml`.
- Resume matching active work instead of creating an overlapping task.
- Close only when the objective is met or intentionally terminated, validation is recorded, and
  unfinished work is explicitly retained or moved to a new task.

## Start As One File

Default to a single record:

```text
docs/agents/tasks/audio-stream-initialization.md
```

Its top-level index entry points directly to that Markdown file. Copy
`docs/agents/tasks/task-template.md` and replace the placeholders.

## Expand Only When Needed

When one record becomes difficult to navigate or has independently owned branches, migrate it to:

```text
docs/agents/tasks/audio-stream-initialization/
├── index.yml
├── overview.md
├── decisions.md
└── evidence.md
```

The task's top-level entry then points to the nested `index.yml`. Preserve the same task ID and git
history where practical. A nested index should use this shape:

```yaml
schema_version: 1
task: TASK-001
title: Audio stream initialization
status: active
entrypoint: docs/agents/tasks/audio-stream-initialization/overview.md
branches:
  - id: decisions
    path: docs/agents/tasks/audio-stream-initialization/decisions.md
    load_when:
      - reviewing accepted or rejected approaches
  - id: evidence
    path: docs/agents/tasks/audio-stream-initialization/evidence.md
    load_when:
      - reviewing experiment or validation results
```

Do not create a folder merely to hold one Markdown file.

## Evidence Hygiene

Record commands, dates, source paths, results, limitations, and whether a conclusion is observed or
inferred. Do not store proprietary binaries, huge traces, secrets, machine identifiers, or raw local
state in a task record. Promote durable technical conclusions into the canonical note or guide.

