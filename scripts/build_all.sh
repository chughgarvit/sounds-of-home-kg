#!/usr/bin/env bash
# Reproduce every artefact from the public downloads. Usage: scripts/build_all.sh [labels.zip] [sins_meta.txt]
set -euo pipefail
cd "$(dirname "$0")/.."
LABELS=${1:-$HOME/Downloads/sounds_of_home_labels/Cnn14_DecisionLevelAtt_light.zip}
SINS=${2:-$HOME/Downloads/sins_meta/DCASE2018-task5-dev/meta.txt}
if [ ! -s "$LABELS" ]; then
  mkdir -p "$(dirname "$LABELS")"
  curl -L -o "$LABELS" "https://zenodo.org/api/records/14246752/files/Cnn14_DecisionLevelAtt_light.zip/content"   # 1.05 GB, CC BY 4.0
fi
if [ ! -s "$SINS" ]; then
  mkdir -p "$(dirname "$SINS")/.." && (cd "$(dirname "$SINS")/.." && curl -L -o sins.meta.zip "https://zenodo.org/api/records/1247102/files/DCASE2018-task5-dev.meta.zip/content" && unzip -o -q sins.meta.zip)
fi
for t in scripts/test_*.py graph/test_api.py; do python3 "$t"; done
[ -f notebook/soundsofhome_to_echollm_reviewed.ipynb ] && python3 scripts/gen_taxonomy.py || true
python3 scripts/panns_to_captions.py "$LABELS" data/real --policy extended
mkdir -p data/real/kg data/sins
for f in data/real/captions_*.json; do python3 scripts/captions_to_nt.py "$f" "data/real/kg/$(basename "${f%.json}").nt.gz" > /dev/null; done
python3 scripts/sins_to_nt.py "$SINS" data/sins/sins_dev.nt.gz
EVAL="$(dirname "$SINS")/../DCASE2018-task5-eval/meta.txt"; [ -s "$EVAL" ] && python3 scripts/sins_to_nt.py "$EVAL" data/sins/sins_eval.nt.gz || echo "(SINS eval meta not present; dev only)"
python3 scripts/kg_index.py data/real/kg data/real/recorders.json data/real/kg/index.html
echo "done: $(ls data/real/kg/captions_*.nt.gz | wc -l) day graphs in data/real/kg (+ frame-level sample), SINS in data/sins, report in data/real/report.md, index (timeline + event graph + temporal graph per day) at data/real/kg/index.html"
