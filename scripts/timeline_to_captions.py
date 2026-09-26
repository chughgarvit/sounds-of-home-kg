"""Convert the Sounds of Home pipeline output to caption records (the contract in README.md).

Input: `segments_all.csv` (notebook Stage 5 - every 10 s window, kept AND dropped). Use this
for the graph: state intervals (METHODS.md M1) assume a gapless timeline. `segments_final.csv`
(Stage 9) also works but is the capped, subsampled training set - not a timeline.

Emits one JSON per (recorder, date) day into the output directory.

Usage: python scripts/timeline_to_captions.py echollm_soh/meta/segments_all.csv data/real/
"""
import json
import sys
from pathlib import Path

import pandas as pd

SEG_SEC = 10.0
MIN_CONF = 0.30       # floor for windows with no confident label (quiet or unidentified)
MASKED_CONF = 0.0     # privacy-blanked audio: no evidence at all
MASKED_TEXT = "Audio unavailable (privacy-masked)."
QUIET_TEXT = "There is no meaningful home event happening."   # EchoScriptor's null sentence
UNKNOWN_TEXT = "Unidentified sounds."


def _label(v):
    return v if isinstance(v, str) and v else None


def _abs_start(stem: str, t_start: float) -> float:
    # stem = YYYYMMDD_HHMMSS; t_start is seconds within that hourly file
    h, m, s = int(stem[9:11]), int(stem[11:13]), int(stem[13:15])
    return float(t_start) + h * 3600 + m * 60 + s


def describe(activity, background) -> str:
    if activity and background:
        return f"{activity} while {background} in the background."
    return f"{activity or background}."


def to_record(r) -> dict:
    activity, background = _label(r.get("activity")), _label(r.get("background"))
    if r.get("drop_reason") == "privacy_masked":
        activity, background, conf, text = None, None, MASKED_CONF, MASKED_TEXT
    elif activity:
        conf, text = float(r.act_peak), describe(activity, background)
    elif background:
        conf, text = float(r.bg_peak), describe(None, background)
    elif r.get("kind") == "null":
        conf, text = MIN_CONF, QUIET_TEXT
    else:
        conf, text = MIN_CONF, UNKNOWN_TEXT
    gpt = r.get("output")                       # Stage 9 rows carry the GPT description
    if isinstance(gpt, str) and gpt:
        text = gpt
    wav = r.get("wav_out")
    clip = (Path(wav).name if isinstance(wav, str) and wav
            else f"{r.recorder}_{r.stem}_{int(r.seg_idx):04d}.wav")
    t0 = _abs_start(str(r.stem), r.t_start)
    return {
        "t_start": round(t0, 1),
        "t_end": round(t0 + SEG_SEC, 1),
        "description": text,
        "activity": activity,
        "background": background,
        "confidence": round(min(max(conf, 0.0), 1.0), 3),
        "clip_file": clip,
    }


def read_segments(csv_path) -> pd.DataFrame:
    """Read a Stage 5/9 CSV. keep_default_na=False: the kind 'null' is a real value, not a missing one."""
    df = pd.read_csv(csv_path, dtype={"recorder": str, "stem": str}, keep_default_na=False, na_values=[""])
    return df


def to_records(day: pd.DataFrame) -> list[dict]:
    return sorted((to_record(r) for _, r in day.iterrows()), key=lambda x: x["t_start"])


if __name__ == "__main__":
    csv_path, out_dir = Path(sys.argv[1]), Path(sys.argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    df = read_segments(csv_path)
    df["date"] = df.stem.str[:8]
    for (rec, date), day in df.groupby(["recorder", "date"]):
        recs = to_records(day)
        out = out_dir / f"captions_{rec}_{date}.json"
        out.write_text(json.dumps(recs, indent=1))
        print(f"{out}  {len(recs)} records")
