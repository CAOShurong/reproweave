# Replication planning

Evidence gaps become useful only when they can drive work. ReproWeave models replication work as a
directed acyclic graph, usually called a DAG.

## Tasks and dependencies

Each task records:

- a portable ID and concrete title;
- state: blocked, ready, in progress, or done;
- priority: critical, high, medium, or low;
- estimated hours;
- paper targets;
- prerequisite task IDs;
- an observable acceptance condition;
- a human-written blocker note.

The planner topologically sorts this graph. Tasks with no unresolved structural prerequisite enter
wave 1. A task enters the wave after the latest prerequisite. Tasks in the same wave are shown as
parallel candidates.

## What the estimates mean

`total_effort_hours` adds every task estimate. `ideal_parallel_hours` adds the longest task in each
wave, assuming unlimited people and hardware within a wave. Neither value predicts calendar time.
Queueing, debugging, procurement, approvals, and failed runs remain outside the model unless you
create tasks for them.

## Blockers

A task is reported as blocked when:

- its own state is `blocked`; or
- a declared prerequisite is not `done`.

The first case is a human decision. The second is derived from current state. This distinction
prevents “dependency exists” from being confused with “external access is impossible.”

## Acceptance criteria

Prefer:

> Five seed-level result files, an aggregate table, and the exact environment digest are committed.

Avoid:

> Reproduce the paper.

The first can be reviewed. The second hides multiple outcomes behind one label.

## Safety

ReproWeave never executes a task or third-party research code. Treat external repositories,
containers, checkpoints, and datasets as untrusted. Inspect licenses and run risky workloads in an
appropriate sandbox.

