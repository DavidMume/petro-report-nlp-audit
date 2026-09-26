# Research Log

Chronological record of methodological decisions, alternatives considered,
and their impact. Negative findings (claims that could not be verified,
models that underperformed, hypotheses the data did not support) belong
here too — they are not deleted for not fitting a narrative.

Format per entry: **date — decision — reason — alternative considered — impact**.

---

## 2026-09-27 — Project scaffolded before source document ingestion

**Decision:** Create the full repository structure, config files, schema
definitions, stub modules/scripts, minimal tests, and initial README before
placing the confirmed source PDF in `data/raw/` or running any extraction
or NLP.

**Reason:** The task brief for this first session was explicitly scoped to
scaffolding only (folder structure, git init, environment, `.gitignore`,
dependencies, initial README, metadata schema, base extraction scripts,
corpus/claims schemas, minimal tests, first commit) — substantive analysis
was explicitly deferred to avoid drawing conclusions before the source
document's provenance is confirmed.

**Alternative considered:** Immediately ingest the document found attached
to this Claude Project (`🆑-Libro-De-La-Verdad.pdf`) and begin extraction.
Rejected for this session because (a) the project brief's own rule is not
to assume a document's authorship/organisation before verifying it against
the source itself, and (b) only the project's text-extracted rendering of
that PDF was accessible from this environment, not confirmed original PDF
bytes suitable for a provenance-grade SHA-256 hash — copying a
already-extracted text version into `data/raw/` would violate the
immutable-original-bytes rule in `data/raw/README.md`.

**Impact:** `documents/source_metadata.json` and `data/raw/` remain
placeholders (all fields `null`, folder empty) pending an explicit decision
from the project owner on how to bring in the verified original PDF file.
No organisation name or acronym (including "ADLA", which the project brief
explicitly flagged as unverified) has been used anywhere in code, file
names, or metadata.

---

## 2026-09-27 — GitHub remote repository not created

**Decision:** Skip `gh repo create` for `DavidMume/petro-report-nlp-audit`
and keep the repository local-only for this session.

**Reason:** `gh auth status` failed (`The token in GH_TOKEN is invalid`) —
no valid GitHub authentication as `DavidMume` was available in this
environment. Per the task brief, when authentication is unavailable the
correct behaviour is to continue locally and document the missing command,
not to attempt alternative credentials.

**Alternative considered:** None attempted, by instruction.

**Impact:** The repository exists locally with `main` as the default
branch and an initial commit, but has no `origin` remote and has not been
pushed anywhere. The exact command to run once authenticated is documented
in `README.md` §"Repository status".

---

## 2026-09-27 — A document titled "El Libro de la Verdad" was found already attached to the Claude Project

**Decision:** Note its presence and basic front-matter content in this log
and in the session report, without treating it yet as the confirmed,
ingested source document for this pipeline.

**Reason:** A project document (`🆑-Libro-De-La-Verdad.pdf`) was already
attached to the Claude Project this session runs in. Its opening pages
(cover, table of contents, presidential and vice-presidential presentation
letters) identify it as "El Libro de la Verdad", presented under an
"Empalme Anticorrupción 2026" / "Comité Nacional del Empalme
Anticorrupción" transition process, addressing prior-administration
findings. These are facts *as stated inside the document itself* — this
project takes no position on their accuracy, and per the project's own
editorial-neutrality rule (`documents/methodology.md`), no conclusion about
the prior administration is drawn from this alone. Whether "ADLA" is a
correct shorthand for anyone named in the document, and who occupies which
office as of the document's stated date, are exactly the kind of claims
this project should verify rather than assume — hence the "no asumas ADLA"
instruction was taken literally: this log records what the cover pages say
about themselves, not an independently confirmed fact about the world.
Note also that the assistant's reliable knowledge cutoff (January 2026)
predates the document's own apparent context, so no outside verification of
officeholders or events was attempted here.

**Alternative considered:** Immediately copying the project's
text-extracted rendering into `data/raw/` as the working source file.
Rejected — see prior entry.

**Impact:** No file was added to `data/raw/`. The project owner should
confirm (a) whether this is indeed the document to be audited, and (b)
how to obtain its original PDF bytes (vs. the already-extracted text
rendering available via the Project) so that a provenance-grade SHA-256
hash and complete `source_metadata.json` can be produced.
