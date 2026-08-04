# Validation evidence

Version 0.1.0 is validated at four layers.

## Behavioral tests

Seventy-five standard-library unit tests cover:

- portable identifiers, escaping, deterministic JSON, and hashing;
- all seven artifact validators;
- workspace creation, replacement, ordering, and counts;
- BibTeX and CSL JSON success and failure cases;
- weighted score behavior, missing coverage, and matrices;
- graph edges, task ordering, cycles, waves, blockers, and backlogs;
- cross-reference audit failures and warnings;
- seal stability, verification, and change detection;
- report escaping, interpretation boundaries, exports, and the full demo.

Run:

```bash
python -m unittest discover -s tests -v
```

## Static checks

```bash
ruff check src tests
ruff format --check src tests
python -m compileall -q src tests
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
report.

## Supported matrix

- Windows and Ubuntu
- Python 3.11 and 3.13

Support means the automated matrix passes. Other operating systems and Python versions may work
but are not claimed by version 0.1.0.

