# `data/raw/` — immutable source documents

This folder holds the **original, unmodified** source document(s) under audit.

## Rules

1. **Immutability.** Once a file is placed here, it is never edited, re-encoded,
   re-compressed, or silently replaced. If a newer version of the source
   document is published, it is added as a **new, separately named file**
   (e.g. `informe_v2.pdf`) with its own entry in
   `documents/source_metadata.json` and its own SHA-256 hash. The original is
   kept.
2. **No silent substitution.** If the file that ends up here differs in any
   way from what was originally downloaded (different hash), that is treated
   as a data-integrity incident and logged in `RESEARCH_LOG.md`, not quietly
   overwritten.
3. **Provenance is mandatory.** Every file here must have a corresponding
   record in `documents/source_metadata.json` with, at minimum: title,
   publisher/authoring entity, publication date, original URL, download
   date, filename, SHA-256 hash, and page count. Do not analyse a file that
   lacks this record.
4. **No fabrication.** If the authoring organisation, title, or publication
   date cannot be confirmed from the document itself or a citable source,
   the corresponding metadata field stays `null` rather than being guessed.
   In particular, no acronym or organisation name is used in filenames,
   titles, or metadata until it has been verified against the source
   document.

## Status

This folder is currently empty. The source PDF has not yet been placed here
as of this scaffolding commit. See `RESEARCH_LOG.md` for the decision to
scaffold the project ahead of receiving the final, confirmed source file.

## How to add the source document

1. Place the PDF in this folder (e.g. `data/raw/informe.pdf`).
2. Compute its hash: `sha256sum data/raw/informe.pdf`.
3. Fill in `documents/source_metadata.json` completely — do not leave the
   hash, filename, or page count blank once the file is present.
4. Run `make extract` to begin the extraction pipeline.
