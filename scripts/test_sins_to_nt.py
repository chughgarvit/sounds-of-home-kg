"""python scripts/test_sins_to_nt.py"""
import sys, tempfile
from pathlib import Path
import rdflib
sys.path.insert(0, str(Path(__file__).resolve().parent))
from sins_to_nt import parse, triples  # noqa: E402

meta = "audio/DevNode1_ex2_1.wav\tcooking\ts2\naudio/DevNode1_ex2_2.wav\tcooking\ts2\naudio/DevNode2_ex2_1.wav\tcooking\ts2\naudio/DevNode1_ex1_1.wav\tabsence\ts1\n"
p = Path(tempfile.mkdtemp()) / "meta.txt"; p.write_text(meta)
rows = parse(p); assert len(rows) == 4
g = rdflib.Graph().parse(data="\n".join(triples(rows, "https://x.org/sins")), format="nt")
assert len(g) == 4 * 6
q = """PREFIX saref: <https://saref.etsi.org/core/> SELECT ?mic ?t WHERE { ?o saref:relatesToProperty <https://x.org/sins/property/activity/cooking> ;
        saref:measurementMadeBy ?mic ; saref:hasTimestamp ?t } ORDER BY ?t ?mic"""
r = [(str(m).rsplit('/', 1)[-1], str(t)[11:19]) for m, t in g.query(q)]
assert r == [("node1", "00:00:00"), ("node2", "00:00:00"), ("node1", "00:00:10")], r   # per-session relative clock; nodes share it
print("ok")
