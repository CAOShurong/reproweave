# Replication planning

## Candidate triage

`reproweave triage` answers a different question from the task scheduler: which selected paper
should the lab act on next? It joins four recorded inputs for each paper:

1. the reconstructability assessment and its `no`, `unknown`, `missing`, or `partial` gaps;
2. resources referenced by the paper's experiments and their availability;
3. paper-linked tasks, their states, and unfinished dependencies;
4. remaining human-entered effort.

The command does not collapse these inputs into a new weighted score. It applies named decision
rules and returns `complete`, `run_now`, `prepare`, `evidence_first`, or `needs_planning`, together
with the exact next action. This makes the queue reviewable and prevents a small effort estimate
from hiding an unavailable dataset or missing assessment.

Use repeatable resource overrides to test a scenario without changing the workspace:

```bash
reproweave triage --workspace review \
  --resource private-traces=available \
  --resource custom-board=partial \
  --format markdown --output reports/access-scenario.md
```

An override changes resource availability only in that output. It does not mark blocked tasks
complete, edit evidence ratings, or modify the saved resource record.

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
