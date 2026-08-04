# Methodology

ReproWeave answers a narrow question: **how much of a reported result is currently documented
well enough for a reviewer to reconstruct it?** It does not answer whether the result is true,
important, novel, ethical, statistically valid, or generalizable.

## Unit of analysis

The paper is the scoring unit, but evidence is stored below that level:

1. A **claim** records a bounded statement and an exact locator.
2. An **experiment** records the protocol that could support one or more claims.
3. A **resource** records a versioned dependency such as code, data, hardware, or a result bundle.
4. An **assessment** records the reviewer's evidence and next action for each dimension.

This separation matters. “Code available” is not useful if the code cannot be connected to the
experiment behind the headline result.

## Ratings

- `yes`: the reviewer found sufficient, specific evidence to attempt reconstruction.
- `partial`: useful evidence exists, but at least one material choice remains.
- `no`: the artifact or detail is explicitly absent, unavailable, or withheld.
- `unknown`: the reviewer has not established availability.
- `na`: the dimension genuinely does not apply and is excluded from the denominator.

`Unknown` is scored as zero because it is not currently actionable, not because the underlying
artifact necessarily does not exist. Keeping `unknown` distinct from `no` preserves an important
research distinction.

## Dimensions and weights

| Dimension | Weight | Rationale |
|---|---:|---|
| Method specificity | 1.25 | An underspecified method prevents reconstruction even when code exists. |
| Data availability | 1.25 | Exact inputs often dominate the result and split behavior. |
| Code availability | 1.00 | Code reduces transcription ambiguity but does not replace protocol evidence. |
| Environment capture | 1.00 | Dependency, hardware, and seed differences can change results. |
| Metric definition | 1.00 | A number is not comparable without aggregation and uncertainty rules. |
| Baseline traceability | 0.75 | Baselines matter, but a target method can sometimes be reconstructed independently. |
| Compute disclosure | 0.75 | Compute bounds affect feasibility and exact training replication. |
| Result traceability | 1.25 | The result must connect to a configuration and output artifact. |

Weights are explicit constants in `src/reproweave/constants.py`. They are policy, not learned
parameters.

## Calculation

Ratings map to `yes = 1`, `partial = 0.5`, and `no/unknown = 0`. `na` is excluded. For applicable
dimensions:

```text
score = 100 × Σ(rating value × dimension weight) / Σ(dimension weight)
```

The result is rounded to one decimal place. ReproWeave separately reports **rubric coverage**:
the percentage of dimensions that have an explicit non-missing record. A high score with low
rubric coverage should not be treated as complete.

## Evidence discipline

Every rating must contain a non-empty evidence note. Prefer locators that another reviewer can
check: page and section, figure or table, supplement identifier, repository path and commit,
dataset version, container digest, hardware revision, or correspondence date.

Do not paste large copyrighted passages. Record a short paraphrase and the locator.

## Comparison rules

Scores are most useful within one review where:

- the same question and inclusion criteria apply;
- the same reviewer guidance is used;
- evidence was assessed at approximately the same time;
- `na` is used consistently;
- version changes are recorded.

Cross-domain league tables are usually misleading. A hardware experiment and a public-data
benchmark face different availability constraints.

## Human review remains necessary

The application validates the shape and connections of the record. It cannot determine whether a
quoted section supports the rating, whether a repository is correct, whether an implementation is
safe to run, or whether an experiment reproduces the paper.

