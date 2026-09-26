"""Export caption records (README data contract) as a SAREF observation graph, N-Triples gzip.

Same shape as the DAHCC knowledge graph: every observation carries the five DAHCC predicates
  void:inDataset, saref:measurementMadeBy, saref:relatesToProperty, saref:hasTimestamp, saref:hasValue
with the microphone as the sensor, the sound class as the measured property and the confidence as the
value. The activity observation additionally carries rdfs:label (the description) and
prov:wasDerivedFrom (the 10 s clip). Null windows become an observation of property activity/none, so
the timeline stays gapless.

Usage: python scripts/captions_to_nt.py data/real/captions_14_20231122.json data/real/captions_14_20231122.nt.gz
       [--recorder 14 --date 2023-11-22 --base https://example.org/soh]
recorder/date default to the captions_<recorder>_<YYYYMMDD>.json filename pattern.
"""
import argparse, gzip, json, re
from datetime import datetime, timedelta
from pathlib import Path

SAREF, VOID, RDFS, PROV, XSD = ("https://saref.etsi.org/core/", "http://rdfs.org/ns/void#",
                                 "http://www.w3.org/2000/01/rdf-schema#", "http://www.w3.org/ns/prov#",
                                 "http://www.w3.org/2001/XMLSchema#")
FNAME = re.compile(r"captions_(?P<rec>[^_]+)_(?P<date>\d{8})")


def slug(label):
    return re.sub(r"[^A-Za-z0-9]+", "_", label).strip("_")


def lit(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", " ") + '"'


def obs_iris(records, base, recorder, day):
    """The observation IRI(s) every record gets in triples(): [(activity_obs_iri, background_obs_iri or None)], same order."""
    ds = f"{base}/{recorder}_{day:%Y%m%d}"
    out, n = [], 0
    for r in records:
        a = f"{ds}/obs{n}"; n += 1
        b = None
        if r.get("background"):
            b = f"{ds}/obs{n}"; n += 1
        out.append((a, b))
    return out


def triples(records, base, recorder, day):
    ds, mic = f"<{base}/{recorder}_{day:%Y%m%d}>", f"<{base}/mic/{recorder}>"
    n = 0
    for r in records:
        t = (day + timedelta(seconds=float(r["t_start"]))).isoformat(timespec="microseconds")
        obs = [("activity", r.get("activity") or "none", True)]
        if r.get("background"):
            obs.append(("background", r["background"], False))
        for kind, label, primary in obs:
            o = f"<{base}/{recorder}_{day:%Y%m%d}/obs{n}>"; n += 1
            yield f"{o} <{VOID}inDataset> {ds} ."
            yield f"{o} <{SAREF}measurementMadeBy> {mic} ."
            yield f"{o} <{SAREF}relatesToProperty> <{base}/property/{kind}/{slug(label)}> ."
            yield f'{o} <{SAREF}hasTimestamp> "{t}"^^<{XSD}dateTime> .'
            yield f'{o} <{SAREF}hasValue> "{float(r["confidence"]):.3f}"^^<{XSD}float> .'
            if primary:
                yield f"{o} <{RDFS}label> {lit(r['description'])} ."
                yield f"{o} <{PROV}wasDerivedFrom> <{base}/clip/{slug(r['clip_file'])}> ."
            yield ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out")
    ap.add_argument("--recorder"); ap.add_argument("--date"); ap.add_argument("--base", default="https://home-audio-kg-bench.org/soh")
    a = ap.parse_args()
    m = FNAME.search(Path(a.src).name)
    recorder = a.recorder or (m and m["rec"]) or "mock"
    date = a.date or (m and f"{m['date'][:4]}-{m['date'][4:6]}-{m['date'][6:]}") or "2000-01-01"
    day = datetime.fromisoformat(date)
    records = json.load(open(a.src))
    with gzip.open(a.out, "wt") as f:
        n = 0
        for line in triples(records, a.base, recorder, day):
            f.write(line + "\n"); n += bool(line)
    print(f"{len(records)} records -> {n} triples ({recorder}, {date}) -> {a.out}")


if __name__ == "__main__":
    main()
