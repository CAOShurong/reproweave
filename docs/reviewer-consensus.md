# Reviewer consensus and migration

ReproWeave 0.3 prevents multiple assessment files from silently becoming one paper score. It
keeps every individual review and requires a separate, explicit consensus before derived ranking
commands run.

## Why this is a real result-integrity problem

The public 0.2.1 CLI accepted two assessments for one paper while different commands treated them
differently: the audit passed, the assessment summary counted both, and matrix/triage behavior
depended on ID ordering. That is a reproducible software defect, not evidence that ReproWeave has
an established user population.

The chosen rule follows a mature review pattern rather than inventing an automatic score:

- The current [Cochrane Handbook, section 4.6.4](https://www.cochrane.org/authors/handbooks-and-manuals/handbook/current/chapter-04)
  calls for at least two independent people in key selection decisions and a predefined way to
  resolve disagreements.
- [Covidence](https://support.covidence.org/help/resolving-conflicts-at-screening-stage) and
  [Rayyan](https://help.rayyan.ai/hc/en-us/articles/25316026225041-How-to-Resolve-Screening-Conflicts-in-Rayyan)
  expose conflicts for human resolution instead of silently choosing a record. Rayyan explicitly
  avoids automatic majority resolution.
- An older official [Chinese translation of the Cochrane Handbook](https://community.cochrane.org/sites/default/files/uploads/inline-files/CochraneHandbookChineseDec2014_0.pdf)
  likewise describes independent review and discussion or third-person adjudication. It is useful
  Chinese-language corroboration, but it is not the current English edition.
- A practitioner discussion in [ASReview #557](https://github.com/asreview/asreview/discussions/557)
  illustrates that adding reviewers can change interpreted statistics and that disagreement can
  represent honest judgment rather than a simple data-entry error. This is anecdotal evidence for
  the failure class, not a prevalence estimate.

## Record format

Existing single-assessment workspaces need no change; an omitted `kind` means `individual`.

```json
{
  "id": "review-alice",
  "paper_id": "paper-one",
  "kind": "individual",
  "reviewer": "Alice",
  "ratings": {}
}
```

When a second individual assessment is added, create one consensus that covers every current
individual assessment for the paper:

```json
{
  "id": "consensus-round-one",
  "paper_id": "paper-one",
  "kind": "consensus",
  "reviewer": "Alice and Bob after discussion",
  "source_assessment_ids": ["review-alice", "review-bob"],
  "source_assessment_hashes": {
    "review-alice": "sha256:0000000000000000000000000000000000000000000000000000000000000000",
    "review-bob": "sha256:1111111111111111111111111111111111111111111111111111111111111111"
  },
  "ratings": {}
}
```

The two digests above are illustrative placeholders. Replace them with the exact values emitted by
`agreement`; otherwise audit reports the consensus as stale.

Each real record still needs the eight rating objects and evidence notes described in the
[methodology](methodology.md). Run `reproweave agreement --workspace REVIEW` to inspect status and
copy the reported `individual_assessment_hashes` into the consensus record. Exit status 4 means at
least one paper has an unresolved or invalid multi-review state.

## Strict boundaries

- Identical individual rating vectors still require explicit consensus; matching numbers do not
  prove matching evidence or intent.
- Consensus must cover all current individual assessments, not a selected subset.
- Consensus binds the canonical SHA-256 of every source card. Editing a source after consensus
  makes the decision stale and requires a new consensus record.
- A consensus cannot cite another consensus or an assessment of a different paper.
- Version 0.3 permits one consensus per paper and does not model rounds or supersession.
- ReproWeave does not average, vote, compute inter-rater agreement, blind reviewers, authenticate
  reviewer names, or sign decisions.
- Source hashes detect changed review content. They are not signatures and do not prove reviewer
  identity, authorship, or independent adjudication.

## Why not reuse a hosted review platform?

| Option | License/cost and operating model | Fit and migration cost |
|---|---|---|
| Covidence | Proprietary hosted service; its public pricing lists US$339/year for one review | Strong conflict workflow, but moving a local file-native replication plan into a paid SaaS changes the privacy and operating boundary |
| Rayyan | Proprietary hosted free/paid tiers | Strong screening collaboration, but it targets systematic-review screening rather than ReproWeave's eight-dimension reconstructability records |
| ASReview | Apache-2.0; active open source | Its multi-user server requires a web service, database/task infrastructure, and deployment; useful for screening prioritization, not a zero-dependency local artifact extension |
| ReproWeave 0.3 | MIT; local Python CLI with no runtime dependencies | Adds consensus source IDs and hashes only when a paper has multiple assessments; no service migration |

Sources: [Covidence pricing](https://www.covidence.org/pricing/),
[Rayyan pricing](https://www.rayyan.ai/pricing), [ASReview repository](https://github.com/asreview/asreview),
and [ASReview server documentation](https://asreview.readthedocs.io/en/stable/server/overview.html).
These alternatives are maintained and should be used directly when collaborative screening is the
actual need. ReproWeave's narrower change is justified only for its local replication-planning
records.
