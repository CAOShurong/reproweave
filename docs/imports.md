# Bibliography imports

ReproWeave accepts UTF-8 BibTeX and CSL JSON without network access.

## BibTeX

The parser handles common `@article`, `@inproceedings`, and related entries with braced, quoted,
or bare field values; nested braces; multiple authors separated by `and`; and both brace and
parenthesis entry delimiters.

It deliberately does not implement:

- string macro expansion;
- `crossref` inheritance;
- concatenated values using `#`;
- LaTeX-to-Unicode conversion;
- citation formatting.

Keep the original `.bib` export beside the workspace if exact citation fidelity matters. An
unsupported construct fails visibly rather than being guessed.

## CSL JSON

The importer accepts one object or a list. It reads title, authors, issued year, container title,
DOI, URL, and abstract. Literal and given/family author forms are supported.

## Deduplication

ReproWeave detects duplicate normalized IDs inside one import but does not silently merge across
existing papers. A DOI can identify duplicates, but DOI absence and metadata variation make
automatic merging risky. Review collisions and use `--replace` only when intentional.

## No lookup behavior

Import never resolves a DOI, queries Crossref, downloads a PDF, or calls an AI service. This keeps
the transformation deterministic and prevents an offline review from leaking its topic.

