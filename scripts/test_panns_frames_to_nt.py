"""python scripts/test_panns_frames_to_nt.py"""
import sys
from pathlib import Path
import numpy as np, rdflib
sys.path.insert(0, str(Path(__file__).resolve().parent))
from panns_frames_to_nt import triples  # noqa: E402
times = np.array([0.0, 0.213333]); probs = {"Water tap, faucet": np.array([0.7, 0.0], dtype=np.float32), "Silence": np.array([0.1, 0.9], dtype=np.float32)}
g = rdflib.Graph().parse(data="\n".join(triples(times, probs, "14", "20231122_130000", "https://x.org/soh")), format="nt")
assert len(g) == 3 * 5, len(g)   # zero-probability entries are not emitted
ts = sorted(str(t) for t in g.objects(predicate=rdflib.URIRef("https://saref.etsi.org/core/hasTimestamp")))
assert ts[0] == "2023-11-22T13:00:00" and ts[-1].startswith("2023-11-22T13:00:00.213333"), ts
print("ok")
