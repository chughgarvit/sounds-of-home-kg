"""End-to-end CLI check on a tiny synthetic zip: python scripts/test_panns_to_captions_cli.py"""
import json, subprocess, sys, tempfile, zipfile
from pathlib import Path
root = Path(__file__).resolve().parents[1]
tmp = Path(tempfile.mkdtemp()); z = tmp / "labels.zip"
DT = 0.213333
def hour(rec, stem, cls):
    frames = [{"frame_index": i, "sample_index": i, "time": round(i * DT, 6), "predictions": [{"class": cls, "prob": 0.8}]} for i in range(int(3595 / DT))]
    frames.append({"metadata": {"recorder_number": rec}})
    return json.dumps(frames)
with zipfile.ZipFile(z, "w", zipfile.ZIP_DEFLATED) as zf:
    zf.writestr("L/01/20231116_070000_light.json", hour("01", "20231116_070000", "Television"))
    zf.writestr("L/02/20231116_070000_light.json", hour("02", "20231116_070000", "Water tap, faucet"))
out = tmp / "out"
r = subprocess.run([sys.executable, str(root / "scripts/panns_to_captions.py"), str(z), str(out), "--workers", "2"], capture_output=True, text=True)
assert r.returncode == 0, r.stderr
recs = json.load(open(out / "captions_02_20231116.json"))
assert len(recs) == 359 and all(x["activity"] == "Running Water in Sink" for x in recs), (len(recs), recs[0])
assert (out / "report.md").exists() and (out / "segments_all.csv").exists()
homes = json.load(open(out / "recorders.json"))
assert homes["02"]["room"] == "kitchen" and homes["01"]["home"] == homes["02"]["home"]
print("ok")
