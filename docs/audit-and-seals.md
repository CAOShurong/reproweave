# Audit and evidence seals

The audit and the seal answer different questions.

## Structural audit

`reproweave audit` checks:

1. The workspace manifest and every artifact pass runtime validation.
2. Claim, experiment, assessment, task, and screening references resolve.
3. Replication tasks do not contain a dependency cycle.
4. Included papers have an assessment, reported as a warning when missing.

Errors produce exit code 2. Warnings preserve a passing status because an incomplete review can
still be structurally valid.

An audit does not fetch URLs, execute code, inspect a PDF, validate statistical reasoning, or
confirm that evidence notes are honest.

## Evidence seal

`reproweave seal` hashes the manifest and every source artifact with SHA-256. It then hashes the
ordered list of paths, sizes, and file hashes to produce one root.

Generated reports and the seal file itself are excluded. A report can therefore be regenerated
without changing the source root.

`reproweave verify` recomputes the root and reports `verified` or `changed`. The creation timestamp
is informational and is not part of the comparison.

## What a seal proves

A matching seal shows that the current source bytes match the sealed source snapshot. It does not
prove authorship, custody, timestamp validity, scientific correctness, or freedom from
fabrication. Use signed commits, release attestations, or an institutional archive when those
properties matter.

