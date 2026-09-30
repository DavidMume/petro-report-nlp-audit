# Portfolio integration (juandamunoz.com)

## Done (2026-09-30), branch `feature/petro-report-nlp-audit` in `DavidMume/juan-david-portfolio`

- Project card in `src/data/projects.js` (slug `libro-de-la-verdad-audit`, category `data-journalism`,
  status "in progress", repo link).
- The audit web app is served as a static bundle at `/libro-de-la-verdad/`, following the
  `impuesto-saludable` pattern: `npm run sync:libro-de-la-verdad` builds `web/` in this repo and copies
  `web/dist` to `public/libro-de-la-verdad/`; `_redirects` rules sit before the SPA catch-all; the
  React route `/libro-de-la-verdad` covers dev.
- Checks passed before pushing: build, lint (with the maintainer's local `eslint.config.js`, which is
  not in the repo), `npm audit --omit=dev` (0 vulnerabilities), and preview routes at 1280px and
  390px with no console errors on the new pages.
- Opened as a pull request. Nothing was pushed to `main`.

## Pending

- **Article.** Not integrated. The handbook requires the author's confirmed text, verbatim. A draft to
  rewrite is in `documents/article_draft_es.md`. Integrate it only once the author approves the text
  and the pilot assessments have had human review. Then set `articleUrl` in the project entry and
  link back from the web app.
- After merging: confirm that Cloudflare Pages deployed the merge SHA and that
  `https://juandamunoz.com/libro-de-la-verdad/` serves the new hashed bundle (handbook §Cloudflare).
- Pre-existing issue, not caused by this change: at 390px the `votar-desde-lejos` article pages
  overflow horizontally.
- Pre-existing issue: `eslint.config.js` is untracked in the portfolio repo, so `npm run lint` fails on
  a fresh clone.
