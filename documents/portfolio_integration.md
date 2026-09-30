# Portfolio integration plan (juandamunoz.com) — pending

Not started. Two blockers:

1. This session could not read `ARTICLE_INTEGRATION_HANDBOOK.md`, `src/data/projects.js` or
   `src/data/articles.js` in `DavidMume/juan-david-portfolio` (the raw-file fetch needed an approval
   that was never granted), so the current schemas are unknown.
2. The execution environment cannot push to GitHub. Integration has to run from a machine with
   access to that repository, e.g. Claude Code on the owner's computer.

## Steps (per the project brief §17-18)

1. Branch: `git checkout -b feature/petro-report-nlp-audit` (never commit to `main`).
2. Read `ARTICLE_INTEGRATION_HANDBOOK.md` in full, then the current schema of `src/data/projects.js` and `src/data/articles.js`.
3. Project entry in `src/data/projects.js`:
   - category: `data-journalism` (recommended: the output is a traceable audit, not political commentary)
   - bilingual title / summary (ES/EN), stack, links to this repo and to the web app
   - sections: Pregunta · Documento · Metodología · Pipeline · NLP · Claim extraction · Verification · Visualisations · Limitations · Repository · Article · Sources
4. Article at `/articulos/<slug-final>`: **only after the verification phase has more than the 10-claim pilot, and after human review.** It has to be an editorial piece built on the results, not a copy of the project page. Validate `sources` and `highlights` against the handbook, check every URL, run `npm run build` and lint.
5. Cross-link the project page and the article, and connect both to the home page following the portfolio's existing architecture.

## Web app hosting options

- Build `web/` (`npm run build`, relative base `./`) and serve `web/dist/` as a sub-path of the portfolio, or on its own Cloudflare Pages / GitHub Pages site.
