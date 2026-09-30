#!/usr/bin/env python3
"""Download the human-written control documents (corpus A) listed in
sources/calibration/A_human/sources.csv.

Writes sources/calibration/A_human/pdf/<source_id>.pdf (not committed) and
sources/calibration/A_human/downloads.csv (committed): URL, download time,
HTTP result, SHA-256, size, page count, PDF creation/modification dates and
whether the file is usable as a *pre-LLM* control.

A document is excluded when its PDF CreationDate is on or after the public
release of ChatGPT (2022-11-30). Files already downloaded are kept and only
re-hashed, so the script can be re-run.
"""

from __future__ import annotations

import datetime as dt
import re
import shutil
import ssl
import subprocess
import sys
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import calibration as cal
from src.extract import compute_sha256

UA = "Mozilla/5.0 (research; petro-report-nlp-audit calibration corpus)"


def _download(url: str, dest: Path) -> str:
    ctx = None
    try:
        import certifi
        ctx = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        pass
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=120, context=ctx) as r, open(dest, "wb") as f:
            shutil.copyfileobj(r, f)
        return "ok (urllib)"
    except Exception as e:  # certificate chains of some .gov.co hosts fail in Python; fall back to curl
        if shutil.which("curl"):
            res = subprocess.run(["curl", "-fsSL", "--max-time", "300", "-A", UA, "-o", str(dest), url],
                                 capture_output=True, text=True)
            if res.returncode == 0:
                return f"ok (curl; urllib failed: {type(e).__name__})"
            return f"failed: urllib {type(e).__name__}; curl {res.returncode} {res.stderr.strip()[:120]}"
        return f"failed: {type(e).__name__}: {e}"


def _pdf_date(s: str | None) -> str | None:
    m = re.match(r"D:(\d{4})(\d{2})?(\d{2})?", s or "")
    if not m:
        return None
    y, mo, d = m.group(1), m.group(2) or "01", m.group(3) or "01"
    return f"{y}-{mo}-{d}"


def main() -> None:
    import pymupdf

    src = pd.read_csv(cal.HUMAN_SOURCES_CSV, dtype=str)
    cal.HUMAN_PDF_DIR.mkdir(parents=True, exist_ok=True)
    rows = []
    for r in src.itertuples():
        dest = cal.HUMAN_PDF_DIR / f"{r.source_id}.pdf"
        when = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
        result = "already present" if dest.exists() and dest.stat().st_size > 0 else _download(r.url, dest)
        row = {"source_id": r.source_id, "url": r.url, "downloaded_at": when, "result": result,
               "sha256": None, "bytes": None, "pages": None, "pdf_creation_date": None, "pdf_mod_date": None,
               "usable": False, "exclusion_reason": None}
        if dest.exists() and dest.stat().st_size > 0:
            head = dest.read_bytes()[:5]
            row["sha256"], row["bytes"] = compute_sha256(dest), dest.stat().st_size
            if head != b"%PDF-":
                row["exclusion_reason"] = "not a PDF (the host returned another page)"
            else:
                try:
                    with pymupdf.open(dest) as doc:
                        row["pages"] = doc.page_count
                        row["pdf_creation_date"] = _pdf_date(doc.metadata.get("creationDate"))
                        row["pdf_mod_date"] = _pdf_date(doc.metadata.get("modDate"))
                    if row["pdf_creation_date"] and row["pdf_creation_date"] >= cal.CHATGPT_RELEASE:
                        row["exclusion_reason"] = f"PDF created {row['pdf_creation_date']}, after {cal.CHATGPT_RELEASE}"
                    else:
                        row["usable"] = True
                except Exception as e:
                    row["exclusion_reason"] = f"unreadable PDF: {type(e).__name__}"
        else:
            row["exclusion_reason"] = "download failed"
        print(f"[fetch] {r.source_id}: {result}; pages={row['pages']} created={row['pdf_creation_date']} "
              f"usable={row['usable']} {row['exclusion_reason'] or ''}")
        rows.append(row)
    pd.DataFrame(rows).to_csv(cal.HUMAN_DOWNLOADS_CSV, index=False)
    n = sum(r["usable"] for r in rows)
    print(f"[fetch] {n}/{len(rows)} documents usable; log in {cal.HUMAN_DOWNLOADS_CSV}")
    if n < cal.GATE["min_human_sources"]:
        sys.exit(f"Only {n} usable human documents (need {cal.GATE['min_human_sources']}).")


if __name__ == "__main__":
    main()
