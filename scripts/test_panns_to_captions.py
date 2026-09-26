"""One runnable check for the annotation-only pipeline: python scripts/test_panns_to_captions.py
Builds a synthetic hour of PANNs frames (6 windows) exercising alias aggregation, the privacy mask,
silence, strict-vs-extended, background-only and 'unidentified', end to end into contract records."""
import io
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from soh.panns import load_annotation, privacy_mask, segment_hour  # noqa: E402
from timeline_to_captions import to_records, MASKED_CONF  # noqa: E402

DT = 0.213333
frames = []
for i in range(int(61 / DT)):   # 61 s so the sixth 10 s window is complete
    t = i * DT; w = int(t // 10); preds = []
    if w == 0:   # tap: aliases alternate frame to frame -> only alias aggregation reaches 30 % coverage
        preds.append({"class": "Water tap, faucet" if i % 2 else "Pour", "prob": 0.7})
    elif w == 1 and 13 < t < 15:  # 2 s of speech in the middle -> blanked +/-1 s -> window masked
        preds.append({"class": "Speech", "prob": 0.9})
    elif w == 2:
        preds.append({"class": "Silence", "prob": 0.9})
    elif w == 3:
        preds.append({"class": "Television", "prob": 0.8})
    elif w == 4:
        preds.append({"class": "Refrigerator", "prob": 0.5})
    # w == 5: nothing confident
    preds.append({"class": "Inside, small room", "prob": 0.3})
    frames.append({"frame_index": i, "sample_index": i * 32 * 320, "time": round(t, 6), "predictions": preds})
frames.append({"metadata": {"sample_rate": 48000, "hop_size": 320, "recorder_number": "14", "model_type": "Cnn14_DecisionLevelAtt"}})
times, probs, meta = load_annotation(io.StringIO(json.dumps(frames)))
assert len(times) == 285 and meta["recorder_number"] == "14" and abs(float(probs["Speech"].max()) - 0.9) < 1e-6
assert 0.06 < privacy_mask(times, probs).mean() < 0.08, privacy_mask(times, probs).mean()  # 2 s speech + 1 s pad each side of 61 s

for policy, w3 in (("extended", "Watching Television"), ("strict", None)):
    rows = segment_hour(times, probs, "14", "20231122_130000", policy)
    assert [r["kind"] for r in rows] == ["activity_only", "DROP", "null", "activity_only" if w3 else "DROP", "background_only", "DROP"], (policy, [r["kind"] for r in rows])
    assert rows[0]["activity"] == "Running Water in Sink" and rows[0]["act_cov"] > 0.99, "alias aggregation"
    assert rows[1]["drop_reason"] == "privacy_masked" and rows[5]["drop_reason"] == "no_confident_label"
    assert rows[3]["activity"] == w3 and rows[4]["background"] == "Fridge Humming"
    recs = to_records(pd.DataFrame(rows))
    assert [r["t_start"] for r in recs] == [46800.0 + 10 * k for k in range(6)], "gapless, absolute time from stem hour"
    assert abs(recs[0]["confidence"] - 0.7) < 1e-6 and recs[1]["confidence"] == MASKED_CONF and recs[1]["activity"] is None
    assert recs[2]["description"] != recs[5]["description"], "quiet vs unidentified must read differently"
print("ok")
