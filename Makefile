.PHONY: help venv install extract corpus nlp claims validation authorship charts web-data report web all clean test lock \
	calibration-fetch calibration-corpora detectors detectors-analysis detectors-dryrun

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
	@echo ""
	@echo "Detector calibration (needs requirements-detectors.txt and internet; see sources/calibration/README.md):"
	@echo "  calibration-fetch    - download the human control PDFs (corpus A) and log their hashes"
	@echo "  calibration-corpora  - build comparable passages for A, B, C and the report"
	@echo "  detectors            - score every passage (Qwen2.5 pair; SIZE=0.5B for low memory)"
	@echo "  detectors-analysis   - calibration metrics, gate, application to the report, charts 27-28"
	@echo "  detectors-dryrun     - tiny random models, no download, meaningless numbers (needs corpus A passages)"
	@echo "  (on a Mac, scripts/run_detectors_mac.sh does all of this in one command)"

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

DPYTHON ?= $(PYTHON)
SIZE ?= 1.5B

calibration-fetch:
	$(DPYTHON) scripts/fetch_calibration_human.py

calibration-corpora:
	$(DPYTHON) scripts/build_calibration_corpora.py

detectors:
	$(DPYTHON) scripts/run_detectors.py --size $(SIZE)

detectors-analysis:
	$(DPYTHON) scripts/analyse_detector_calibration.py

detectors-dryrun:
	$(DPYTHON) scripts/run_detectors.py --dry-run --max-tokens 256
	$(DPYTHON) scripts/analyse_detector_calibration.py --dry-run

test:
	$(PYTHON) -m pytest -q

clean:
	rm -rf data/interim/*.jsonl data/interim/*.npy data/interim/tables
	find . -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
