# Contributing to ReproWeave

Thank you for helping improve a small, auditable research tool.

## Good contributions

- A minimal bug reproduction and the smallest safe fix.
- A schema or rubric proposal with a concrete research workflow.
- Import fixtures that expose a real BibTeX or CSL edge case.
- Accessibility, offline behavior, or report portability improvements.
- Documentation that makes an interpretation boundary clearer.

Please do not submit real reviewer notes, restricted datasets, copyrighted PDFs, private
repository content, or personal allegations about paper authors.

## Development setup

```bash
git clone https://github.com/CAOShurong/reproweave.git
cd reproweave
python -m pip install -e .
python -m unittest discover -s tests -v
```

Install the pinned quality and build tools used in CI:

```bash
python -m pip install -r requirements/ci.txt
ruff check src tests scripts
ruff format --check src tests scripts
python -m build
```

## Pull requests

1. Keep each pull request focused.
2. Add tests for behavioral changes.
3. Update schemas and docs when the durable data model changes.
4. Preserve deterministic ordering and Windows/Linux portability.
5. State whether a change affects score interpretation or stored artifacts.

By participating, you agree to follow the [Code of Conduct](CODE_OF_CONDUCT.md).
