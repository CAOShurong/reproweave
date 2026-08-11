# Data model

ReproWeave stores one JSON object per artifact. Filenames equal artifact IDs, producing stable
diffs and low-conflict reviews.

## Identity rules

IDs start with a lowercase letter and contain lowercase letters, digits, and hyphens. They are
workspace-local and unique across every artifact type because graph edges are stored as IDs.
Each JSON filename must equal its internal ID. Renaming an ID is a migration because other
artifacts may reference it. IDs are limited to 200 ASCII characters so JSON and atomic temporary
filenames remain portable across common Windows, Linux, and macOS filesystems.

## Relationship model

```mermaid
flowchart LR
  P[Paper] -->|reports| C[Claim]
  P -->|contains| E[Experiment]
  C -->|supported by| E
  E -->|uses| R[Resource]
  A[Assessment] -->|evaluates| P
  S[Screening decision] -->|classifies| P
  T[Replication task] -->|targets| P
  T -->|depends on| T2[Replication task]
```

### Paper

Bibliographic identity used by the rest of the workspace. ReproWeave intentionally stores only a
small portable subset. Rich citation management belongs in the source citation manager.

### Claim

A bounded statement with an `evidence_locator`. `confidence` records the reviewer's current
relationship to the statement: reported, corroborated, contested, or uncertain. It is not a
probability.

### Experiment

A protocol summary that links a paper to the resources required to reconstruct a result.
`metric_ids` and `baseline_ids` are open ID lists reserved for workspaces that model those
concepts as resources or extensions.

### Resource

Code, dataset, environment, model, hardware, protocol, result, or other dependency. Availability
is separate from URL presence. A repository can be reachable but only partially usable.

### Assessment

Eight dimension records with a rating, evidence note, and optional next action. An omitted `kind`
means `individual` for backward compatibility. One individual assessment resolves directly. Two
or more individual assessments require exactly one explicit `kind: "consensus"` record whose
`source_assessment_ids` name every current individual assessment for that paper. A consensus may
not reference another consensus or a review of another paper. `source_assessment_hashes` binds the
canonical SHA-256 of each source, so later edits make the consensus stale. ReproWeave never
averages, votes, or selects one individual record automatically.

Version 0.3 supports one consensus round per paper. Supersession, signatures, blind review, and
reviewer identity verification are outside this format. See
[`reviewer-consensus.md`](reviewer-consensus.md).

### Task

A node in the replication directed acyclic graph. Dependencies must point to other task IDs.
`acceptance` should describe observable completion evidence, not activity. `estimate_hours` is a
finite non-negative planning input capped at 1,000,000,000 hours so all aggregations and exports
remain bounded; it is not an observed duration.

### Screening

An appendable decision record for discovery, deduplication, screening, inclusion, or exclusion.
The v1 demo uses one terminal record per paper. Longitudinal workflows can retain multiple
timestamped IDs.

## Forward compatibility

Runtime validators allow additional properties so laboratories can add namespaced fields without
forking the tool. Core commands ignore unknown fields. Removing or changing a core field requires
a format-version migration.

Published JSON Schemas live in [`schemas/`](../schemas/). The Python runtime deliberately does
not require a JSON Schema package.
