# Security policy

## Supported versions

Security fixes are applied to the latest release.

## Report a vulnerability

Use GitHub's private vulnerability reporting feature for this repository. Do not open a public
issue containing exploit details, private research material, credentials, or restricted URLs.

## Trust boundary

ReproWeave reads local JSON, BibTeX, and CSL JSON and writes local reports. It does not execute
paper code, open repository URLs, download datasets, or send telemetry. Generated reports embed
workspace content, so treat them as sensitive whenever the source notes are sensitive.

The report generator HTML-escapes displayed values and JSON-escapes embedded data. It does not
make arbitrary third-party content safe to share. Review reports before publishing them.

Evidence seals detect changes; they are not signatures and do not establish who created a file.
Use signed commits or an institutional archival system when authorship and custody matter.

Assessment `reviewer` values and consensus records are self-reported strings, not authenticated
identities, signatures, independent adjudication, or proof that two people actually reviewed a
paper. Reports can expose reviewer names and evidence notes in terminal logs or shared HTML.
Inspect both before publication.

Consensus source hashes detect when an individual assessment changes after the decision. They are
content checks, not identity-bound signatures or timestamps.
