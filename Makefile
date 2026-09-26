.PHONY: help venv install extract corpus nlp claims validation charts report all clean test

PYTHON := .venv/bin/python
PIP := .venv/bin/pip

help:
	@echo "Targets:"
	@echo "  venv        - create virtual environment"
	@echo "  install     - install dependencies into .venv"
	@echo "  extract     - extract raw PDF into paragraph/sentence-level text"
	@echo "  corpus      - build the structured corpus (parquet/csv)"
	@echo "  nlp         - run exploratory NLP (frequencies, TF-IDF, NER, topics)"
	@echo "  claims      - run claim extraction"
	@echo "  validation  - run claim validation against external evidence"
	@echo "  charts      - regenerate all visualisations from outputs"
	@echo "  report      - assemble final output tables/reports"
	@echo "  all         - run the full pipeline end-to-end"
	@echo "  test        - run the test suite"
	@echo "  clean       - remove interim/processed derived files (not data/raw)"

venv:
	python3 -m venv .venv

install: venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

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

charts:
	$(PYTHON) scripts/build_outputs.py

report: charts

all: extract corpus nlp claims validation charts report

test:
	$(PYTHON) -m pytest -v

clean:
	rm -rf data/interim/* data/processed/*
	rm -rf outputs/tables/* outputs/charts/* outputs/networks/* outputs/reports/*
	find . -name "__pycache__" -not -path "./.venv/*" -exec rm -rf {} +
