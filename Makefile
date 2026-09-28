.PHONY: help venv install extract corpus nlp claims validation authorship charts web-data report web all clean test lock

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help:
	@echo "Targets:"
	@echo "  install     - create .venv, install pinned dependencies + Spanish spaCy model"
	@echo "  extract     - PDF -> block-level pages (PyMuPDF -> pdfplumber -> OCR), verifies SHA-256"
	@echo "  corpus      - structured corpus (sentences/paragraphs/sections)"
	@echo "  nlp         - frequencies, TF-IDF, n-grams, NER, networks, topics, embeddings, framing"
	@echo "  claims      - rule-assisted claim candidates + numeric claims + causal review table"
	@echo "  validation  - integrity checks on curated evidence/assessments + merged views"
	@echo "  authorship  - exploratory stylometry / linguistic provenance"
	@echo "  charts      - regenerate outputs/charts/*.png and outputs/data_manifest.json"
	@echo "  web-data    - export JSON for the web app (web/public/data)"
	@echo "  web         - build the web app (needs node)"
	@echo "  all         - full pipeline, extract -> web-data"
	@echo "  test        - run the test suite"

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.lock   # includes es_core_news_lg by URL

lock:
	$(PIP) freeze --exclude-editable > requirements.lock

extract:
	$(PYTHON) scripts/extract_document.py

corpus:
	$(PYTHON) scripts/build_corpus.py

nlp:
	$(PYTHON) scripts/run_nlp.py

claims:
	$(PYTHON) scripts/extract_claims.py

validation:
	$(PYTHON) scripts/validate_claims.py

authorship:
	$(PYTHON) scripts/run_authorship.py

charts:
	$(PYTHON) scripts/build_outputs.py

web-data:
	$(PYTHON) scripts/export_web_data.py

report: charts web-data

web: web-data
	cd web && npm install && npm run build

all: extract corpus nlp claims validation authorship charts web-data

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf data/interim/*.jsonl data/interim/*.npy data/interim/tables
	find . -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
