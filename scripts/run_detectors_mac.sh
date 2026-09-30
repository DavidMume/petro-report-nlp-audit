#!/usr/bin/env bash
# Detector calibration experiment in one command (macOS or Linux).
#
#   cd ~/Projects/petro-report-nlp-audit && bash scripts/run_detectors_mac.sh
#
# 1. creates .venv-detectors and installs requirements-detectors.txt (torch is large);
# 2. downloads the human control PDFs (corpus A) and logs their SHA-256;
# 3. builds comparable passages (A, generated B, hybrid C if present, the report);
# 4. scores every passage with the Qwen2.5 pair (downloads ~6 GB of models the first time);
# 5. runs the calibration analysis and writes tables + charts 27-28.
#
# Re-running is safe: downloads and scores already done are skipped.
# SIZE=0.5B bash scripts/run_detectors_mac.sh   -> smaller models (automatic below 12 GB of RAM).
set -euo pipefail
cd "$(dirname "$0")/.."

PY=""
for c in python3.13 python3.12 python3.11 python3.10 python3; do
  if command -v "$c" >/dev/null 2>&1 && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)'; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo "Hace falta Python 3.10 o superior. Instálalo desde https://www.python.org/downloads/ o con: brew install python@3.12"
  exit 1
fi

ARCH="$(uname -m)"
MEM_GB=0
if [ "$(uname -s)" = "Darwin" ]; then
  MEM_GB=$(( $(sysctl -n hw.memsize) / 1024 / 1024 / 1024 ))
elif [ -r /proc/meminfo ]; then
  MEM_GB=$(( $(awk '/MemTotal/ {print $2}' /proc/meminfo) / 1024 / 1024 ))
fi
if [ -z "${SIZE:-}" ]; then
  if [ "$MEM_GB" -gt 0 ] && [ "$MEM_GB" -lt 12 ]; then SIZE="0.5B"; else SIZE="1.5B"; fi
fi
echo "== Python: $($PY --version) · arquitectura: $ARCH · memoria: ${MEM_GB} GB · modelos: Qwen2.5-$SIZE"

VENV=.venv-detectors
[ -d "$VENV" ] || "$PY" -m venv "$VENV"
"$VENV/bin/pip" install -q --upgrade pip
if [ "$(uname -s)" = "Darwin" ] && [ "$ARCH" = "x86_64" ]; then
  # Intel Macs: the last torch release with macOS x86_64 wheels is 2.2.2.
  "$VENV/bin/pip" install -q "torch==2.2.2" "numpy<2" "transformers>=4.44,<4.50"
fi
echo "== Instalando dependencias (la primera vez tarda unos minutos)…"
"$VENV/bin/pip" install -q -r requirements-detectors.txt

echo "== 1/4 Descargando documentos humanos de control"
"$VENV/bin/python" scripts/fetch_calibration_human.py
echo "== 2/4 Construyendo pasajes comparables"
"$VENV/bin/python" scripts/build_calibration_corpora.py --human --generated
echo "== 3/4 Calculando puntajes (descarga los modelos la primera vez)"
"$VENV/bin/python" scripts/run_detectors.py --size "$SIZE"
echo "== 4/4 Análisis de calibración"
"$VENV/bin/python" scripts/analyse_detector_calibration.py

echo
echo "Listo. Resultados en outputs/tables/detector_calibration_status.json y outputs/charts/27-28."
echo "Vuelve al chat y escribe 'listo' para revisar los resultados."
