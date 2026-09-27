# Durable Task Records

Use a task record for multi-session, risky, blocked, or discovery-heavy work. Small isolated edits do
not need one. Tasks preserve decisions and evidence; they are not a duplicate of source-of-truth
register notes or public documentation.

## IDs And Lifecycle

- Assign monotonic IDs such as `TASK-001` and a stable lowercase kebab-case slug.
- Use `backlog`, `active`, `blocked`, `paused`, or `closed` as the status.
- Index open tasks in `docs/agents/tasks/index.yml` and closed tasks in
  `docs/agents/tasks/closed/index.yml`. Each task has exactly one entry across those indexes.
- Check both indexes before assigning an ID; archived IDs remain reserved.
- Resume matching active work instead of creating an overlapping task.
- Close only when the objective is met or intentionally terminated, validation is recorded, and
  unfinished work is explicitly retained or moved to a new task.

## YAML Routing

`docs/agents/tasks/index.yml` is the entrypoint. Its `tasks` list contains open records;
its `archives` list routes to `closed/index.yml`. Load archived records only when their
`load_when` conditions match the work, rather than loading all task history.

Both task indexes use `schema_version: 1`, `area`, `description`, and a `tasks` list.
Every task entry keeps `id`, `title`, repository-relative `path`, `summary`, `status`,
and `load_when`. Archive routes use the same routing fields with `status: historical`.
Task records themselves retain `status: closed`; moving them does not change their outcome.
Closed entries may add `resolution: completed` or `resolution: superseded` to distinguish
delivered work from a plan made obsolete by a change in direction.

```text
docs/agents/tasks/
  index.yml              # Open task entries and archive routes
  README.md
  task-template.md
  <open-task>.md
  closed/
    index.yml            # Closed task entries
    <closed-task>.md
```

## Closing And Reopening

When closing a task, record its outcome, validation, and remaining boundaries, then move its
Markdown file into `closed/`. Move its complete index entry to `closed/index.yml`, change its
path and status, and update links and repository-relative references in the same change.
For a multi-file task, move the whole task directory and fix its nested YAML paths as well.
Preserve evidence, the task ID, and its slug; do not create a second index entry or a duplicate
record at the old location.

Reopen an existing objective by moving its record and entry back to the main task area and
setting the appropriate open status. A distinct follow-up gets a new ID and links to the
archived evidence. Paused or blocked work stays in the open index until explicitly closed.

Before retaining or creating a feature task, check the main upstream driver. Functionality
already provided upstream is not a missing in-house feature to implement. Close obsolete plans
as superseded, with the reason and source evidence recorded. Do not turn every untested feature
into a replacement task; keep known limitations in current status until there is a concrete
validation, integration, or defect investigation objective.

After a move, parse the YAML, verify all indexed paths exist, check ID uniqueness and status
agreement, and search for stale references to the old path.

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
