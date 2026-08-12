# Roadmap

The roadmap prioritizes trustworthy interchange over automation volume.

## Shipped in 0.4.1

- Extended-length internal file operations on Windows keep maximum-length portable artifact IDs
  usable in deep workspaces without changing the user-visible paths.

## Shipped in 0.4.0

- Whole-batch bibliography preflight before any artifact is written.
- Deterministic `import --dry-run` output and explicit per-candidate acceptance.
- Read-only DOI and conservative title/year/author duplicate candidates in JSON, CSV, and
  Markdown without automatic merging or deletion.
- Installed-wheel acceptance for late collision, blocked duplicate, explicit acceptance, and
  no-side-effect paths.

## Shipped in 0.3.0

- Explicit individual-review and consensus records without automatic averaging or voting.
- Reviewer agreement exports and a report view.
- Strict filename/ID, finite-number, and malformed-workspace diagnostics.
- CodeQL, immutable Action pins, release ancestry/full-CI gates, and artifact attestations.

## Near term

- Formal migration commands for future format versions.
- Optional consensus rounds and supersession only if real workflows require them.
- Optional arXiv identifier candidates if real exports demonstrate a safe normalization boundary.
- Optional Graphviz and Mermaid exports without changing the core data model.
- Additional import fixtures from common citation managers.

## Later, if evidence supports the need

- Opt-in adapters for Zotero exports and executed experiment systems.
- Signed evidence seals if a concrete custody workflow requires identity-bound verification.
- Domain profiles for RF, embedded AI, power electronics, and computer vision.
- Export adapters for consensus discussions that preserve the underlying evidence notes.
- Scenario comparison tables for several named lab-resource profiles.

## Explicit non-goals

- Automatic scientific-quality rankings.
- Hidden or learned rubric weights.
- Uploading workspaces to a mandatory hosted service.
- Executing untrusted paper code.
- Inventing missing metadata through an LLM.
- Replacing a systematic-review protocol or an institutional integrity process.

Proposals should explain the user workflow, the new trust boundary, and how the result stays
reviewable without a network connection.
