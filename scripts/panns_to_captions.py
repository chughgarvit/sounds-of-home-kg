"""Sounds of Home labels -> caption records (README contract), one JSON per (recorder, date), gapless.

Input: the labels-only Zenodo package (Cnn14_DecisionLevelAtt_light.zip, record 14246752) or an
unzipped directory of <recorder>/<YYYYMMDD_HHMMSS>*.json files. Runs notebook Stages 2-5 without
audio (soh/panns.py), then the same converter Sarita's CSV goes through (timeline_to_captions).

Usage: python scripts/panns_to_captions.py ~/Downloads/Cnn14_DecisionLevelAtt_light.zip data/real
         [--policy extended|strict] [--recorders 14,13] [--workers 8]
Writes data/real/captions_<rec>_<date>.json, data/real/segments_all.csv, data/real/report.md,
data/real/recorders.json (per-recorder dates, hours, and an inferred recorder -> home/room map).
"""
import argparse
import io
import json
import os
import re
import sys
import zipfile
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from soh.panns import STEM_RE, load_annotation, segment_hour  # noqa: E402
from soh.homes import infer_homes  # noqa: E402
from timeline_to_captions import to_records  # noqa: E402

def list_members(src):
    """[(recorder, stem, ref)] for every hourly annotation file, from a zip or a directory."""
    out = []
    if src.is_dir():
        for p in sorted(src.rglob("*.json")):
            m = STEM_RE.search(p.name)
            if m:
                out.append((p.parent.name, m.group(1), str(p)))
    else:
        with zipfile.ZipFile(src) as z:
            for name in sorted(z.namelist()):
                m = STEM_RE.search(Path(name).name)
                if name.endswith(".json") and m:
                    out.append((Path(name).parent.name, m.group(1), f"{src}::{name}"))
    return out


def _open(ref):
    if "::" in ref:
        zpath, member = ref.split("::", 1)
        with zipfile.ZipFile(zpath) as z:
            return io.StringIO(z.read(member).decode("utf-8"))
    return open(ref)


def work(args):
    recorder, stem, ref, policy = args
    times, probs, meta = load_annotation(_open(ref))
    rec = str(meta.get("recorder_number") or recorder)
    return segment_hour(times, probs, rec, stem, policy)


def report(seg, per_rec, policy):
    L = [f"# Sounds of Home labels -> segments (policy: {policy})\n",
         f"{len(seg):,} windows of 10 s from {seg.groupby(['recorder', 'stem']).ngroups:,} hourly files, {seg.recorder.nunique()} recorders.\n",
         "## Windows by kind\n", seg.kind.value_counts().to_frame("n").assign(pct=lambda d: (100 * d.n / len(seg)).round(1)).to_markdown(), "",
         "## Drop reasons\n", seg[seg.kind == "DROP"].drop_reason.value_counts().to_frame("n").to_markdown(), "",
         "## Activities (labelled windows)\n", seg.activity.value_counts().to_frame("n").to_markdown(), "",
         "## Backgrounds\n", seg.background.value_counts().to_frame("n").to_markdown(), "",
         "## Per recorder\n"]
    rows = []
    for r, g in seg.groupby("recorder"):
        x = per_rec[r]
        rows.append(dict(recorder=r, home=x["home"], room=x["room"], pair=x["pair"], speech_overlap=x["pair_speech_overlap"],
                         kitchen_ratio=x["kitchen_ratio"], fridge=x["fridge_windows"], evidence_agrees=x.get("room_evidence_agrees"),
                         hours=x["hours"], days=len(x["dates"]), masked_pct=x["masked_pct"],
                         labelled_pct=round(100 * g.kind.str.startswith("activity").mean(), 1),
                         top_activity=g.activity.value_counts().index[0] if g.activity.notna().any() else "-"))
    L.append(pd.DataFrame(rows).to_markdown(index=False))
    L.append("\n`home`, `room`: inferred. Pairing = greedy matching on the Jaccard overlap of speech-masked windows (two mics in one home hear the same conversations; 0.68-0.90 within a home, <0.6 across). Room = higher share of kitchen activities vs television; `fridge` is secondary evidence and `evidence_agrees` is False where it disagrees. Confirm with the dataset owners before publishing.\n")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", type=Path); ap.add_argument("out", type=Path)
    ap.add_argument("--policy", default="extended", choices=["strict", "extended"])
    ap.add_argument("--recorders", help="comma-separated recorder folders to include (default all)")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)
    members = list_members(a.src)
    if a.recorders:
        keep = set(a.recorders.split(","))
        members = [m for m in members if m[0] in keep]
    if not members:
        sys.exit(f"no <recorder>/<YYYYMMDD_HHMMSS>*.json annotation files found in {a.src}")
    print(f"{len(members)} hourly files, {len({m[0] for m in members})} recorders, policy={a.policy}, workers={a.workers}")
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, r in enumerate(ex.map(work, [(*m, a.policy) for m in members], chunksize=4), 1):
            rows.extend(r)
            if i % 100 == 0:
                print(f"  {i}/{len(members)}", flush=True)
    seg = pd.DataFrame(rows)
    seg.to_csv(a.out / "segments_all.csv", index=False)
    seg["date"] = seg.stem.str[:8]
    n_days = 0
    for (rec, date), day in seg.groupby(["recorder", "date"]):
        recs = to_records(day)
        (a.out / f"captions_{rec}_{date}.json").write_text(json.dumps(recs, indent=1))
        n_days += 1
    per_rec = infer_homes(seg)
    (a.out / "recorders.json").write_text(json.dumps(per_rec, indent=1))
    (a.out / "report.md").write_text(report(seg, per_rec, a.policy))
    print(f"{len(seg):,} windows -> {n_days} recorder-days in {a.out}; report.md + recorders.json written")


if __name__ == "__main__":
    main()
