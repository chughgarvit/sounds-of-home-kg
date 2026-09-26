"""Rebuild data/real/recorders.json and report.md from an existing segments_all.csv (no re-parsing).
python scripts/infer_homes.py data/real"""
import json, sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from soh.homes import infer_homes  # noqa: E402
from panns_to_captions import report  # noqa: E402
from timeline_to_captions import read_segments  # noqa: E402

out = Path(sys.argv[1])
seg = read_segments(out / "segments_all.csv")
per_rec = infer_homes(seg)
(out / "recorders.json").write_text(json.dumps(per_rec, indent=1))
policy = "extended" if "Watching Television" in set(seg.activity.dropna()) else "strict"
(out / "report.md").write_text(report(seg, per_rec, policy))
for r, x in per_rec.items():
    print(f"rec {r}: {x['home']} {x['room']:12s} pair={x['pair']} speech_overlap={x['pair_speech_overlap']} kitchen_ratio={x['kitchen_ratio']} fridge={x['fridge_windows']} masked={x['masked_pct']}% [{x['pair_quality']}]")
