"""The one runnable check for timeline_to_captions.py:  python scripts/test_timeline_to_captions.py"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tempfile
from timeline_to_captions import MASKED_CONF, MIN_CONF, QUIET_TEXT, read_segments, to_records  # noqa: E402

FIELDS = {"t_start", "t_end", "description", "activity", "background", "confidence", "clip_file"}

rows = [  # two hourly files of one day, deliberately out of order, one of each window kind
    dict(recorder="14", stem="20231122_140000", seg_idx=0, t_start=0.0, kind="null",
         activity=None, background=None, act_peak=0.0, bg_peak=0.0, drop_reason=None),
    dict(recorder="14", stem="20231122_130000", seg_idx=0, t_start=0.0, kind="activity_background",
         activity="Running Water in Sink", background="Fridge Humming",
         act_peak=0.61, bg_peak=0.90, drop_reason=None),
    dict(recorder="14", stem="20231122_130000", seg_idx=1, t_start=10.0, kind="DROP",
         activity=None, background=None, act_peak=0.80, bg_peak=0.40, drop_reason="privacy_masked"),
    dict(recorder="14", stem="20231122_130000", seg_idx=2, t_start=20.0, kind="background_only",
         activity=None, background="Fridge Humming", act_peak=0.20, bg_peak=0.45, drop_reason=None),
    dict(recorder="14", stem="20231122_130000", seg_idx=3, t_start=30.0, kind="DROP",
         activity=None, background=None, act_peak=0.30, bg_peak=0.10, drop_reason="no_confident_label"),
]
recs = to_records(pd.DataFrame(rows))

assert [r["t_start"] for r in recs] == [46800.0, 46810.0, 46820.0, 46830.0, 50400.0], "sort by absolute time"
assert all(set(r) == FIELDS for r in recs), "contract fields only"
assert recs[0]["confidence"] == 0.61, "activity present -> activity peak, not the louder background"
assert recs[0]["clip_file"] == "14_20231122_130000_0000.wav"
assert recs[1]["activity"] is None and recs[1]["confidence"] == MASKED_CONF, "masked = no evidence"
assert recs[2]["activity"] is None and recs[2]["confidence"] == 0.45, "background only -> bg peak"
assert recs[3]["confidence"] == MIN_CONF and recs[3]["description"] != recs[4]["description"], \
    "unidentified and quiet both null, but distinguishable in the description"
print("ok")

csv = Path(tempfile.mkdtemp()) / "segments_all.csv"
pd.DataFrame(rows).to_csv(csv, index=False)
back = read_segments(csv)
assert back.kind.tolist()[0] == "null" and back.activity.isna().tolist()[0], "kind 'null' must survive the CSV round trip (pandas treats it as NaN by default)"
assert to_records(back)[4]["description"] == QUIET_TEXT   # the 14:00 quiet window sorts last
print("csv round trip ok")
