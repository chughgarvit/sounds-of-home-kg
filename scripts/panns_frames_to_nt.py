"""Frame-level SAREF graph for ONE hourly Sounds of Home annotation file: exactly DAHCC's granularity
(microphone measured <AudioSet class> = <probability> at <time>, ~118k observations per hour). The
segment-level graph (captions_to_nt.py) is what the reasoning layer consumes; this is the raw-evidence
layer under it, for provenance drill-down and for showing the two datasets are one shape.

Usage: python scripts/panns_frames_to_nt.py <zip>::<member.json> | <file.json>  out.nt.gz [--date-from-stem]
"""
import argparse, gzip, io, re, sys, zipfile
from datetime import datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from soh.panns import STEM_RE, load_annotation  # noqa: E402

SAREF, VOID, XSD = "https://saref.etsi.org/core/", "http://rdfs.org/ns/void#", "http://www.w3.org/2001/XMLSchema#"


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_")


def triples(times, probs, recorder, stem, base):
    day = datetime.strptime(stem, "%Y%m%d_%H%M%S")
    ds, mic = f"<{base}/frames/{recorder}_{stem}>", f"<{base}/mic/{recorder}>"
    n = 0
    for i, t in enumerate(times):
        ts = (day + timedelta(seconds=float(t))).isoformat(timespec="microseconds")
        for cls, v in probs.items():
            if v[i] <= 0:
                continue
            o = f"<{base}/frames/{recorder}_{stem}/obs{n}>"; n += 1
            yield f"{o} <{VOID}inDataset> {ds} ."
            yield f"{o} <{SAREF}measurementMadeBy> {mic} ."
            yield f"{o} <{SAREF}relatesToProperty> <{base}/property/audioset/{slug(cls)}> ."
            yield f'{o} <{SAREF}hasTimestamp> "{ts}"^^<{XSD}dateTime> .'
            yield f'{o} <{SAREF}hasValue> "{float(v[i]):.4f}"^^<{XSD}float> .'
            yield ""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src"); ap.add_argument("out"); ap.add_argument("--base", default="https://home-audio-kg-bench.org/soh")
    a = ap.parse_args()
    if "::" in a.src:
        z, m = a.src.split("::", 1)
        with zipfile.ZipFile(z) as zf:
            fh = io.StringIO(zf.read(m).decode()); name = Path(m)
    else:
        fh = open(a.src); name = Path(a.src)
    times, probs, meta = load_annotation(fh)
    recorder, stem = str(meta.get("recorder_number") or name.parent.name), STEM_RE.search(name.name).group(1)
    n = 0
    with gzip.open(a.out, "wt") as f:
        for l in triples(times, probs, recorder, stem, a.base):
            f.write(l + "\n"); n += bool(l)
    print(f"{len(times)} frames x top-7 -> {n} triples -> {a.out}")


if __name__ == "__main__":
    main()
