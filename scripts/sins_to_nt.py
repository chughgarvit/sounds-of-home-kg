"""SINS / DCASE 2018 Task 5 metadata -> SAREF observation graph with HUMAN activity labels.

meta.txt rows are `audio/DevNode{node}_ex{session}_{segment}.wav <tab> activity <tab> s{session}`: 10 s segments of
one week in one real home, 4 microphone nodes observing the same instants. The release carries no clock
time, and session ids are grouped by activity rather than chronological, so every session gets its OWN
relative clock starting at 1970-01-01T00:00:00 (segment k -> +10(k-1) s). Within a session the order is
real; between sessions there is no order. Use it for activity-episode ground truth (durations, and what our
ActivityBlock layer must recover from a stream of observations), never for clock-time questions.

Usage: python scripts/sins_to_nt.py ~/Downloads/sins_meta/DCASE2018-task5-dev/meta.txt data/sins/sins_dev.nt.gz
"""
import argparse, gzip, re
from collections import defaultdict
from datetime import datetime, timedelta

SAREF, VOID, XSD = "https://saref.etsi.org/core/", "http://rdfs.org/ns/void#", "http://www.w3.org/2001/XMLSchema#"
NAME = re.compile(r"(?:Dev|Eval)?Node(?P<node>\d+)_ex(?P<sess>\d+)_(?P<seg>\d+)\.wav$")
SEG_SEC = 10


def parse(meta_path):
    rows = []
    for line in open(meta_path):
        parts = line.rstrip("\n").split("\t")
        if len(parts) < 2:
            continue
        m = NAME.search(parts[0])
        if m:
            rows.append((int(m["node"]), int(m["sess"]), int(m["seg"]), parts[1]))
        elif len(parts) >= 3 and parts[2].startswith("s"):   # eval set: audio/<n>.wav, node not released, order unknown
            rows.append((0, int(parts[2][1:]), int(re.search(r"(\d+)\.wav$", parts[0]).group(1)), parts[1]))
    return rows


def triples(rows, base, day=datetime(1970, 1, 1)):
    """One observation per (node, segment); every node shares the session's relative clock."""
    by_sess = defaultdict(list)
    for node, sess, seg, act in rows:
        by_sess[sess].append((node, seg, act))
    ds = f"<{base}/sins>"
    n = 0
    for sess in sorted(by_sess):
        t = day                                                   # each session: its own relative clock
        segs = by_sess[sess]
        if all(nd == 0 for nd, _, _ in segs):                      # eval set: renumber the anonymised files 1..k
            segs = [(nd, i + 1, act) for i, (nd, _, act) in enumerate(sorted(segs, key=lambda x: x[1]))]
        length = max(s for _, s, _ in segs)
        for node, seg, act in sorted(segs):
            ts = (t + timedelta(seconds=(seg - 1) * SEG_SEC)).isoformat(timespec="microseconds")
            o = f"<{base}/sins/obs{n}>"; n += 1
            yield f"{o} <{VOID}inDataset> {ds} ."
            yield f"{o} <{SAREF}measurementMadeBy> <{base}/mic/{'node%d' % node if node else 'unknown'}> ."
            yield f"{o} <{SAREF}relatesToProperty> <{base}/property/activity/{act}> ."
            yield f'{o} <{SAREF}hasTimestamp> "{ts}"^^<{XSD}dateTime> .'
            yield f'{o} <{SAREF}hasValue> "1.000"^^<{XSD}float> .'
            yield f"{o} <{base}/session> <{base}/sins_dev/session{sess}> ."
            yield ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("meta"); ap.add_argument("out"); ap.add_argument("--base", default="https://home-audio-kg-bench.org/sins")
    a = ap.parse_args()
    rows = parse(a.meta)
    import os; os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    n = 0
    with gzip.open(a.out, "wt") as f:
        for l in triples(rows, a.base):
            f.write(l + "\n"); n += bool(l)
    print(f"{len(rows)} segments, {len({r[1] for r in rows})} sessions, {len({r[0] for r in rows})} nodes -> {n} triples -> {a.out}")


if __name__ == "__main__":
    main()
