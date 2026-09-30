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

---

## 2026-09-28 — Source document confirmed and ingested into `data/raw/`

**Decision:** Place the user-provided `Libro-De-La-Verdad.pdf` (135 pages,
6.7MB) in `data/raw/` as the immutable source file, compute its SHA-256,
and populate the confirmable fields of `documents/source_metadata.json`
directly from the document's own front matter, rather than from any
external assumption.

**Reason:** The project owner uploaded the original PDF in response to the
prior session's request. Its embedded PDF metadata (via PyMuPDF) has blank
title/author XMP fields but a creation timestamp of `2026-08-17T21:24:09-05:00`
(Adobe InDesign export). Reading pages 1, 3, 5 and 7 directly (not the rest
of the document — no content analysis performed) shows: cover title "El
Libro de la Verdad", subtitle "Empalme Anticorrupción 2026", "Gobierno de
Colombia" branding; a "Carta de Presentación" signed by Abelardo De La
Espriella, identified in the document as "Presidente de la República de
Colombia"; and a "Presentación del Libro de la Verdad" signed by José
Manuel Restrepo Abondano, identified as "Vicepresidente de la República y
Director Nacional del Empalme". The corruption-findings chapter is
attributed to an "Equipo Élite Anticorrupción", and the sectoral-balance
chapter is described as being signed individually by each minister. These
are transcriptions of what the document states about itself, not verified
external facts — the assistant's knowledge cutoff (January 2026) predates
this document's apparent context (a mid-2026 Colombian government
transition), so no claim about real-world officeholders is being made
here, consistent with the project's verification-before-assertion
principle. The acronym "ADLA" was still not used anywhere.

**Alternative considered:** Waiting for a source URL before ingesting the
file. Rejected — the user provided the file directly rather than a link,
which is an acceptable provenance path; `original_url` and
`publication_date` are left `null` in the metadata rather than guessed
(e.g., from the PDF's InDesign export date, which reflects file production,
not necessarily official publication).

**Impact:** `data/raw/Libro-De-La-Verdad.pdf` now exists and is treated as
immutable going forward. `documents/source_metadata.json` is populated
except `publication_date` and `original_url`. The project can now proceed
to `make extract` / corpus construction once that work is explicitly
requested — this entry does not itself authorise running the full NLP
pipeline, which remains a separate decision per the project's phased
approach.

---

## 2026-09-28 — `gh auth login` device-code flow not usable from this sandbox

**Decision:** Do not pursue the browser/device-code `gh auth login --web`
flow from this cloud environment; recommend a Personal Access Token (PAT)
pasted by the user instead.

**Reason:** The environment's pre-set `GH_TOKEN`/`GITHUB_TOKEN` variables
are invalid and shadow any interactive login attempt (`gh` refuses to
proceed while they're set). After unsetting them, `gh auth login --web`
failed immediately with `HTTP 415` when requesting a device code — most
likely the sandbox's egress proxy interfering with that specific GitHub
API call. This is a cloud sandbox with no local browser to open on the
user's behalf regardless, unlike a local Claude Code session.

**Alternative considered:** Retrying the device-code flow with different
flags. Not pursued given the proxy-level failure suggests it isn't a
one-off; a PAT avoids the interactive flow entirely and is the standard
non-interactive `gh auth login --with-token` path.

**Impact:** GitHub remote creation remains pending on the user supplying a
valid PAT (or authenticating some other way outside this session).

---

## 2026-09-28 — Repo creation via the GitHub API is blocked at the platform level in this sandbox, independent of any token

**Decision:** Stop attempting `gh repo create` / `POST /user/repos` from
inside this session; this is not a token or scope problem.

**Reason:** With two different user-supplied tokens (a fine-grained PAT and
a classic PAT with `repo` scope), `gh` and direct `curl` calls to
`https://api.github.com/user/repos` both returned `HTTP 403 "This GitHub
API path is not available: sessions are bound to their configured
repositories. Use repository-scoped endpoints (repos/{owner}/{repo}/...)"`,
with the error's `documentation_url` pointing at Anthropic's own docs
rather than GitHub's — i.e. this response is generated by this
environment's egress proxy, not by GitHub. The proxy's status endpoint
(`$HTTPS_PROXY/__agentproxy/status`) confirms `gh` is a
"installedProxyPreconfiguredClis" tool, meaning its GitHub calls are
routed through a managed credential regardless of any `GH_TOKEN` exported
in the shell. Plain `curl GET https://api.github.com/user` with the user's
real token succeeds (200, correct account), so read access passes through
untouched; account-level write calls (repo creation, and presumably repo
listing) are specifically blocked for this session because no repository
has been "configured" for it (i.e., no GitHub connector/integration was
set up for this Cowork session pointing at a specific repo). No amount of
re-pasting a different token changes this — it's a session-level policy
gate, not a credential-validity issue.

**Alternative considered:** Trying further token scope combinations
(organisation-owned token, different fine-grained permission sets).
Rejected — the error text itself states the constraint is about which
repositories are "configured" for the session, not about token
permissions, and a proxy-generated 403 (evidenced by the Anthropic-docs
URL) confirms this is enforced before the request reaches GitHub at all.

**Impact:** Repo creation cannot happen from inside this sandboxed
session. Practical path forward: the user creates the empty repository
themselves at github.com (a plain account-level web action, unaffected by
this session's proxy policy), and this session then attempts a
repository-scoped `git push` to it, which the error message's own wording
suggests should be treated differently from account-level endpoints. If
that also fails, the fallback is delivering the repository as a
downloadable archive for the user to push from their own machine.

---

## 2026-09-28/30 — Phase 2: full pipeline over the confirmed PDF

Each item: **decision — reason — alternative — impact.**

**Extraction.** PyMuPDF block/line extraction with font size and bold kept per line. Pages 1, 2 and 4 have no text layer and were OCR'd (Tesseract `spa`), then excluded from the analytic corpus (cover, photos, logo). Raster figures covering ≥10% of a page (pp. 14, 25) were OCR'd separately; stacked image layers were de-duplicated. One footnote block on p. 8 used a font whose glyphs map to control characters (`identi\x17icados`); it was re-read by OCR over its own bounding box and the original is logged in `ocr_repaired_blocks.csv`. pdfplumber found no ruled tables. *Alternative:* whole-document OCR, rejected because it lowers fidelity everywhere to fix five pages. *Impact:* 1,670 analytic sentences; OCR text is flagged throughout.

**Structure.** Headings are lines ≥12pt; chapters come from the divider pages (170pt numerals); chapter titles are transcribed from the table of contents. Some pages put their main heading late in the PDF content stream (behaviour-definition pages in ch. II, sector openings in ch. IV), so a per-page prescan assigns the whole page to that heading. Ch. IV sector names are matched against a list transcribed from the headings, because a few headings run the sector name and the headline together in one span. *Impact:* 85 sections, all traceable to page ranges (`sections.csv`).

**Stopwords.** spaCy's Spanish list contains domain content words ("estado", "verdad", "poder", "mayor", "nuevo", "total"…). They were removed from the stopword list (`STOPWORD_KEEP`). *Alternative:* keep the default list; rejected because "Estado" would disappear from every frequency table.

**Embeddings (negative constraint).** huggingface.co is blocked by the environment's egress policy, so no sentence-transformer and no BERTopic. Fallback: averaged spaCy `es_core_news_lg` static vectors, with the method recorded in every output. *Impact:* embedding-based clusters and the UMAP map are weaker than planned. Re-run with sentence-transformers where it is available.

**Topic k.** Swept k = 6–14; picked k = 13 by the best NMF NPMI and used it for all models so they are comparable. **Negative finding:** NPMI is negative for every configuration and cross-model agreement is low (ARI 0.03–0.11), so topics are model-dependent and are reported without labels.

**Entities.** Two recurrent spaCy errors: ministry-name fragments tagged as places, and generic nouns ("Estado", "Gobierno") tagged as entities. These are typed `GENERIC` and a small reviewed override list is applied (`TYPE_OVERRIDES`). Acronyms are merged only when the document defines them itself (28 definitions found); ambiguous short forms such as "Contraloría" are never merged.

**Sentiment (negative finding).** The transparent lexicon and the pretrained `sentiment-analysis-spanish` classifier do not agree (Spearman ρ ≈ −0.03 per sentence). No sentiment score is used as a finding.

**Claims.** Rule-assisted scoring: money 3, percent 3, other number 2 (years excluded), date / comparative / ranking / causal / institution / attribution / law 1 each. Threshold ≥3 for a factual candidate; evaluative sentences without quantities are kept separately. Dates and legal references are masked before parsing quantities, after "Ley 951 de 2005" was first read as the quantity "951". *Impact:* 635 candidates (513 factual, 122 evaluative), all `auto_candidate`, none human-reviewed.

**Stylometry — an artefact caught.** The first change-point run found breaks at exactly every 5th segment. Cause: `ruptures.Pelt` defaults to `jump=5`. Fixed with `jump=1`, a standardised signal and BIC-scaled penalties over 12 configurations (2 cost models × 6 penalties). **Negative finding:** no change point is robust (≥ 2/3 of configurations); the most frequent (4/12) sit at the start of chapters III and IV, i.e. genre changes. Two Mahalanobis outliers: the front-matter letters (G001) and a dense legal passage (G021, pp. 51-53).

**AI provenance.** The document itself states that "instrumentos auxiliares de inteligencia artificial" supported document organisation, consolidation, prioritisation, traceability and "organización de los insumos de los productos finales" (ch. I, pp. 10-11). That is an author acknowledgement (§33) that AI was used in the process; it does not say whether AI drafted text. No detector was run (no calibrated Spanish detector; corpora A/B/C not assembled).

**Verification pilot.** 10 claims: 8 with checkable figures from different sectors and source types, plus one opinion and one non-verifiable example to exercise those categories. Evidence was gathered on 2026-09-28 by the AI assistant and is **pending human review**. Outcome: 1 supported, 7 mostly supported, 1 not independently verifiable, 1 opinion. The recurring pattern: figures match official or cited sources closely (0 to −0.5% difference), but context is omitted — the 2022 pre-electoral baseline (C0312), a 2014 commodity-peak base year for a decline that mostly predates 2022 (C0280), commitments vs obligations as the execution metric (C0108), an opinion column described as an "investigación" (C0184), a fiscal warning described as an "auditoría" (C0463). Press coverage *of the report* is registered in the ledger as `coverage_of_audited_document` and rejected as evidence by the validator (circularity).

**Stable claim IDs.** Claim IDs are sequential, so an extraction change can renumber them. Assessments are pinned to sentence_id + text prefix, the validator fails on drift, and `scripts/repin_assessments.py` re-attaches records only on an unambiguous match.

**Not done.** Portfolio integration (handbook unreadable from here; no push access) — see `documents/portfolio_integration.md`. Raw-dataset reconstructions (SIIF, SECOP, GEIH microdata). Human review of candidates. Detector calibration.
