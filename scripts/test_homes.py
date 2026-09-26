"""python scripts/test_homes.py — two homes, four recorders; speech overlap pairs them, kitchen ratio names the room."""
import sys
from pathlib import Path
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from soh.homes import infer_homes  # noqa: E402

rows = []
for w in range(200):
    for rec, home in (("01", "A"), ("02", "A"), ("03", "B"), ("04", "B")):
        speech = (w % 5 == 0) if home == "A" else (w % 7 == 0)          # each home has its own conversation times
        act = None
        if not speech:
            act = "Running Water in Sink" if (rec == "02" and w % 3 == 0) else "Watching Television" if (rec in ("01", "03") and w % 2 == 0) else ("Microwave" if rec == "04" and w % 4 == 0 else None)
        rows.append(dict(recorder=rec, stem="20231116_070000", seg_idx=w, activity=act, background="Fridge Humming" if rec == "01" and w % 2 else None,
                         drop_reason="privacy_masked" if speech else None))
res = infer_homes(pd.DataFrame(rows))
assert res["01"]["home"] == res["02"]["home"] and res["03"]["home"] == res["04"]["home"] and res["01"]["home"] != res["03"]["home"]
assert res["02"]["room"] == "kitchen" and res["01"]["room"] == "living_room" and res["04"]["room"] == "kitchen"
assert res["01"]["room_evidence_agrees"] is False, "fridge points at 01 but activities say 02: flagged"
assert res["01"]["pair_speech_overlap"] == 1.0 and res["01"]["pair_quality"] == "strong"
print("ok")
