"""Notebook Stages 2, 3 and 5 without audio: PANNs frame JSON -> privacy mask -> 10 s segment labels.

Ported verbatim in behaviour from soundsofhome_to_echollm_reviewed.ipynb (incl. the review fixes:
alias aggregation before scoring). Only difference: the hour's duration comes from the last
annotated frame instead of the WAV header, because this path has no audio.
"""
import json
import math
import re
from collections import defaultdict
from datetime import datetime

import numpy as np

from soh import taxonomy as T

STEM_RE = re.compile(r"(\d{8}_\d{6})")
DEFAULT_DT = 0.213333


def load_annotation(path_or_file):
    """Returns (times[N], probs {class -> float32[N]}, metadata). Absent classes are 0 (outside the stored top-7)."""
    raw = json.load(path_or_file) if hasattr(path_or_file, "read") else json.load(open(path_or_file))
    meta = next((r["metadata"] for r in raw if isinstance(r, dict) and "metadata" in r), {})
    frames = [r for r in raw if isinstance(r, dict) and "predictions" in r]
    frames.sort(key=lambda r: r.get("sample_index", r.get("frame_index", 0)))
    n = len(frames)
    times = np.asarray([r["time"] for r in frames], dtype=np.float64)
    probs = defaultdict(lambda: np.zeros(n, dtype=np.float32))
    for i, r in enumerate(frames):
        for p in r["predictions"]:
            probs[p["class"]][i] = float(p["prob"])
    return times, dict(probs), meta


def privacy_mask(times, probs):
    """True where the released WAV is blanked: any privacy label >= 0.2, dilated by +/- 1 s (dataset Sec. 3.4)."""
    n = len(times)
    raw = np.zeros(n, dtype=bool)
    for lbl in T.PRIVACY_LABELS:
        v = probs.get(lbl)
        if v is not None:
            raw |= v >= T.PRIVACY_THR
    dt = float(np.median(np.diff(times))) if n > 1 else DEFAULT_DT
    pad = int(math.ceil(T.PRIVACY_PAD_SEC / dt))
    out = raw.copy()
    for s in range(1, pad + 1):
        out[s:] |= raw[:-s]
        out[:-s] |= raw[s:]
    return out


def best_label(probs, mapping, idx):
    """Per taxonomy label take the per-frame max over its aliases, THEN score peak and coverage (review fix)."""
    by_label = {}
    for src, dst in mapping.items():
        v = probs.get(src)
        if v is None:
            continue
        w = v[idx]
        if not w.size:
            continue
        by_label[dst] = np.maximum(by_label[dst], w) if dst in by_label else w
    if not by_label:
        return None, 0.0, 0.0
    scored = {lbl: (float(w.max()), float((w >= T.FRAME_THR).mean())) for lbl, w in by_label.items()}
    lbl, (peak, cov) = max(scored.items(), key=lambda kv: (kv[1][0], kv[1][1]))
    return lbl, peak, cov


def time_of_day(stem):
    h = datetime.strptime(stem, "%Y%m%d_%H%M%S").hour
    return "morning" if 5 <= h < 12 else "afternoon" if 12 <= h < 17 else "evening" if 17 <= h < 21 else "night"


def segment_hour(times, probs, recorder, stem, policy="extended"):
    """One row per 10 s window, kept AND dropped (the Stage 5 `segments_all` shape)."""
    amap = T.activity_map(policy)
    mask = privacy_mask(times, probs)
    dt = float(np.median(np.diff(times))) if len(times) > 1 else DEFAULT_DT
    dur = float(times[-1] + dt) if len(times) else 0.0
    sil = np.zeros(len(times), dtype=np.float32)
    for s in T.SILENCE_LABELS:
        if s in probs:
            sil = np.maximum(sil, probs[s])
    rows = []
    starts = np.arange(0.0, max(0.0, dur - T.SEG_SEC) + 1e-6, T.SEG_HOP_SEC)
    for k, t0 in enumerate(starts):
        idx = np.where((times >= t0) & (times < t0 + T.SEG_SEC))[0]
        if idx.size == 0:
            continue
        masked_frac = float(mask[idx].mean())
        sil_cov = float((sil[idx] >= T.FRAME_THR).mean())
        act, ap, ac = best_label(probs, amap, idx)
        bg, bp, bc = best_label(probs, T.BACKGROUND_MAP, idx)
        act_ok = act is not None and ap >= T.ACT_MIN_PEAK and ac >= T.ACT_MIN_COVERAGE
        bg_ok = bg is not None and bp >= T.BG_MIN_PEAK and bc >= T.BG_MIN_COVERAGE
        row = dict(recorder=recorder, stem=stem, seg_idx=k, t_start=float(t0), time_of_day=time_of_day(stem),
                   activity=act if act_ok else None, background=bg if bg_ok else None,
                   act_peak=ap, act_cov=ac, bg_peak=bp, bg_cov=bc, silence_cov=sil_cov, masked_frac=masked_frac,
                   drop_reason=None)
        if masked_frac > T.MAX_MASKED_FRAC:
            row.update(kind="DROP", drop_reason="privacy_masked")
        elif act_ok and bg_ok:
            row.update(kind="activity_background")
        elif act_ok:
            row.update(kind="activity_only")
        elif bg_ok:
            row.update(kind="background_only")
        elif sil_cov >= T.SILENCE_COVERAGE:
            row.update(kind="null")
        else:
            row.update(kind="DROP", drop_reason="no_confident_label")
        rows.append(row)
    return rows
