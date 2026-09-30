# Web app

An independent, data-oriented app for exploring the audit (Spanish UI). It is **not** the portfolio
site; the portfolio will link to it.

- Stack: React 19 + Vite 8 + TypeScript + Recharts, with d3-force for the networks. Versions are pinned in `package.json`.
- Data: `public/data/*.json`, written by `python scripts/export_web_data.py` (`make web-data`). The app
  reads those files and computes nothing analytical itself.
- Routes (hash-based, so it works on any static host): `#/`, `#/documento`, `#/nlp`, `#/temas`,
  `#/entidades`, `#/afirmaciones[/<claim_id>]`, `#/verificacion`, `#/procedencia`, `#/datos`,
  `#/metodologia`, `#/fuentes`.
- Claim drill-down: claim → original passage → page → source cited by the report → external evidence →
  assessment → confidence.
- Light and dark themes (token-based; follows the OS setting, with a manual toggle).

```bash
npm install
npm run dev        # local
npm run build      # → dist/ (relative asset paths)
```
