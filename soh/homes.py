"""Infer which recorders shared a home, and which was in the kitchen, from the segment table.

Sounds of Home does not publish the recorder -> home/room mapping. Two AudioMoths per home recorded
the same hours, so they heard the same conversations: the Jaccard overlap of privacy-masked (speech)
windows between two recorders is ~0.7-0.9 within a home and <0.6 across homes. Pairs are formed by greedy
maximum-overlap matching. Room: the recorder with the larger share of kitchen activities (tap, cutlery,
microwave, chopping...) relative to television is the kitchen; fridge hum is reported as secondary
evidence and a disagreement flag is set when it points the other way.
"""
import itertools
from collections import defaultdict

KITCHEN_CLASSES = {"Running Water in Sink", "Handling Cutlery or Dishes", "Microwave", "Blender", "Chopping Board",
                   "Coffee Grinder", "Food Processor", "Timer Beeping"}
LIVING_CLASSES = {"Watching Television"}
MIN_PAIR_OVERLAP = 0.5      # below this a match is reported as 'weak' (still the best available)


def jaccard(a, b):
    return len(a & b) / max(1, len(a | b))


def pair_recorders(seg):
    """Greedy max-overlap matching on speech-masked windows; returns [(rec_a, rec_b, overlap)]."""
    key = seg.stem.astype(str) + "_" + seg.seg_idx.astype(str)
    masked = {r: set(key[(seg.recorder == r) & (seg.drop_reason == "privacy_masked")]) for r in seg.recorder.unique()}
    hours = {r: set(seg.stem[seg.recorder == r]) for r in masked}
    scored = sorted(((jaccard(masked[a], masked[b]), jaccard(hours[a], hours[b]), a, b)
                     for a, b in itertools.combinations(sorted(masked, key=int), 2)), reverse=True)
    used, pairs = set(), []
    for mj, hj, a, b in scored:
        if a in used or b in used:
            continue
        used.update((a, b)); pairs.append((a, b, round(mj, 3), round(hj, 3)))
    for r in sorted(set(masked) - used, key=int):
        pairs.append((r, None, 0.0, 0.0))
    return pairs


def room_evidence(seg, r):
    g = seg[seg.recorder == r]
    kitchen, tv = int(g.activity.isin(KITCHEN_CLASSES).sum()), int(g.activity.isin(LIVING_CLASSES).sum())
    return dict(kitchen_windows=kitchen, tv_windows=tv, kitchen_ratio=round(kitchen / max(1, kitchen + tv), 4),
                fridge_windows=int((g.background == "Fridge Humming").sum()),
                masked_pct=round(100 * float((g.drop_reason == "privacy_masked").mean()), 1),
                hours=int(g.stem.nunique()), dates=sorted(set(g.stem.astype(str).str[:8])))


def infer_homes(seg):
    out = {}
    for hi, (a, b, mj, hj) in enumerate(sorted(pair_recorders(seg), key=lambda p: int(p[0]))):   # letter homes by lowest recorder id
        home = f"home_{chr(65 + hi)}"
        members = [a] if b is None else [a, b]
        ev = {r: room_evidence(seg, r) for r in members}
        if b is None:
            out[a] = dict(home=home, room="unknown", pair=None, pair_speech_overlap=None, pair_quality="unpaired", **ev[a]); continue
        kitchen = max(members, key=lambda r: ev[r]["kitchen_ratio"])
        by_fridge = max(members, key=lambda r: ev[r]["fridge_windows"])
        for r in members:
            out[r] = dict(home=home, room="kitchen" if r == kitchen else "living_room", pair=b if r == a else a,
                          pair_speech_overlap=mj, pair_hours_overlap=hj,
                          pair_quality="strong" if mj >= MIN_PAIR_OVERLAP else "weak (little speech in this home; hours pattern used)",
                          room_evidence_agrees=(by_fridge == kitchen), **ev[r])
    return dict(sorted(out.items(), key=lambda kv: int(kv[0])))
