# Validation evidence

Version 0.2.0 is validated at five layers.

## Behavioral tests

More than eighty standard-library unit tests cover:

- portable identifiers, escaping, deterministic JSON, and hashing;
- all seven artifact validators;
- workspace creation, replacement, ordering, and counts;
- BibTeX and CSL JSON success and failure cases;
- weighted score behavior, missing coverage, and matrices;
- graph edges, task ordering, cycles, waves, blockers, and backlogs;
- rule-based candidate triage, resource overrides, hard blockers, and portable exports;
- cross-reference audit failures and warnings;
- seal stability, verification, and change detection;
- report escaping, interpretation boundaries, exports, and the full demo.

Run:

```bash
python -m unittest discover -s tests -v
```

## Static checks

```bash
ruff check src tests scripts
ruff format --check src tests scripts
python -m compileall -q src tests scripts
python scripts/check_repository.py
```

## Deterministic demonstration

The demo fixes timestamps and synthetic inputs. The evidence seal root must remain identical when
generated at the same path on supported platforms. The generated report includes the absolute
workspace path in its embedded audit record, but reports are deliberately outside the evidence
seal.

```bash
reproweave demo scratch/one
reproweave verify --workspace scratch/one
```

## Package smoke test

CI builds a wheel and source distribution, installs the wheel into a clean virtual environment,
checks the installed version, creates a demo, audits it, verifies its seal, and generates a second
report. The release job also exercises triage, runs `twine check`, writes SHA-256 checksums, and
publishes versioned assets only from a pushed tag.

## Public artifact checks

After release, validation is not complete until all of the following are checked from public
endpoints:

- main and tag CI runs pass on every supported matrix entry;
- Pages serves the site and synthetic report over HTTPS;
- a fresh environment installs the release wheel URL and exercises demo, triage, audit, seal
  verification, and report generation;
- the release contains exactly one wheel, one source archive, and `SHA256SUMS`;
- the GitHub contributor view names only the repository owner.

## Supported matrix

- Windows and Ubuntu
- Python 3.11 and 3.13

Support means the automated matrix passes. Other operating systems and Python versions may work
but are not claimed by version 0.2.0.
