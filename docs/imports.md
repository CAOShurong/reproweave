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
DOI, URL, and abstract. Literal and given/family author forms are supported. Parsing rejects
duplicate object keys, non-standard numbers such as `NaN`, malformed UTF-8, and invalid Unicode.

## Whole-batch preflight

`import` parses and validates every incoming record, checks batch and workspace-wide IDs and paths,
and calculates duplicate candidates before writing the first artifact. A later error that can be
found during preflight therefore leaves the entire batch unwritten.

```bash
reproweave import bibtex library.bib --workspace review --dry-run
```

The deterministic report contains `status`, `would_import`, `paper_ids`, `issues`, and
`candidates`. A ready dry-run exits 0. Any preflight failure exits 5 with structured JSON: duplicate
candidates use `duplicate_candidate`, while parse, schema, ID, and path failures use
`preflight_error`. The workspace remains unchanged. Dry-run writes only to stdout and does not
change the source file.

This is not a crash-safe transaction. Disk exhaustion, power loss, or another process changing the
workspace after preflight can still interrupt the later writes. ReproWeave does not claim locking,
journaling, or power-loss atomicity.

## Duplicate candidates

The read-only scanner is also available for existing workspaces:

```bash
reproweave duplicates --workspace review
reproweave duplicates --workspace review --format csv --output candidates.csv
reproweave duplicates --workspace review --format markdown --output candidates.md
```

Candidate comparison is deliberately conservative and offline:

- A non-empty DOI is Unicode-normalized, case-folded, trimmed, and stripped only of a known `doi:`
  or `doi.org` wrapper. Equality is an exact candidate.
- A title is Unicode NFKC-normalized, case-folded, and whitespace-collapsed. Equal titles become a
  possible candidate only when years differ by at most one and normalized first-author labels
  match. `Unknown` is not an author signal.
- Original title, author, and DOI fields are never rewritten with their comparison values.
- Candidate groups and IDs are independent of input and file creation order. An ID binds the
  normalization version, normalized comparison values, and the exact pairwise evidence edges.
  Superficial DOI wrapper or case changes retain the ID, while changed comparison evidence produces
  a different ID and therefore requires a new decision.

CSV output prefixes cells that spreadsheet software could interpret as formulas. Markdown output
escapes table separators and raw HTML metacharacters. Both formats preserve the review text rather
than executing or rendering untrusted bibliography fields.

Imports stop on both exact and possible candidates. Review the report, then accept only the named
candidate IDs that you have decided to retain:

```bash
reproweave import bibtex library.bib --workspace review \
  --accept-candidate sha256:0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
```

The option is repeatable. An ID that is absent from the current preflight is rejected, preventing a
stale decision from silently authorizing a different candidate. Acceptance keeps every paper; it
does not merge, delete, replace, or mark the candidate resolved. `duplicates` will continue to show
it for human review.

The same policy applies to `reproweave add paper`. If a single paper creates a candidate, inspect
`duplicates` or an import dry-run and pass the exact ID with repeatable `--accept-candidate`.

## No lookup behavior

Import never resolves a DOI, queries Crossref, downloads a PDF, or calls an AI service. This keeps
the transformation deterministic and prevents an offline review from leaking its topic.
