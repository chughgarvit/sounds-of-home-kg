"""python scripts/test_event_graph.py — chain order, state linkage, shared observation IRIs, RDF round trip + SPARQL."""
import gzip, json, sys, tempfile
from datetime import datetime
from pathlib import Path
import rdflib
ROOT = Path(__file__).resolve().parents[1]; sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from graph import build_graph  # noqa: E402
from graph.eventgraph import build_event_graph, EV  # noqa: E402
from captions_to_nt import obs_iris, triples as saref_triples  # noqa: E402
from event_graph_view import run  # noqa: E402

def rec(t, act=None, bg=None, conf=0.8):
    return {"t_start": t, "t_end": t + 10, "activity": act, "background": bg, "confidence": conf, "description": act or "quiet", "clip_file": f"c{t}.wav"}
recs = [rec(0, "Running Water in Sink", "Fridge Humming"), rec(10, "Running Water in Sink"), rec(20), rec(30), rec(40),
        rec(400, "Watching Television"), rec(410, "Watching Television"), rec(420, "Opening or Closing a Door")]
hg = build_graph(recs, room="kitchen", recorder="10"); day = datetime(2023, 11, 22)
eg = build_event_graph(hg, recs, "https://x.org/soh", "10", day)
ev = [n for n in eg["nodes"] if n["type"] == "Event"]
assert [n["activity"] for n in ev] == ["Running Water in Sink", "Watching Television", "Opening or Closing a Door"], ev
prev = [(e["from"], e["to"]) for e in eg["edges"] if e["kind"] == "prev"]
assert prev == [(ev[1]["id"], ev[0]["id"]), (ev[2]["id"], ev[1]["id"])], "hasPreviousEvent chains backwards in time"
tap_edges = [e for e in eg["edges"] if e["from"] == ev[0]["id"] and e["label"] == "hasTapState"]; assert len(tap_edges) == 1
keys = [(e["from"], e["to"], e["label"]) for e in eg["edges"]]; assert len(keys) == len(set(keys)) and len(eg["triples"]) == len(set(eg["triples"])), "no duplicate edges/triples"
obs = {n["id"] for n in eg["nodes"] if n["type"] == "Obs"}
saref = {l.split()[0].strip("<>") for l in saref_triples(recs, "https://x.org/soh", "10", day) if l}
assert obs and obs <= saref, "event-graph observations must be the SAREF observation IRIs"
g = rdflib.Graph().parse(data="\n".join(eg["triples"]), format="nt")
q = f"""SELECT ?a WHERE {{ ?e <{EV}hasActivity> "Opening or Closing a Door" ; <{EV}hasPreviousEvent> ?p . ?p <{EV}hasActivity> ?a }}"""
assert [str(r[0]) for r in g.query(q)] == ["Watching Television"], "what happened before the door?"
tmp = Path(tempfile.mkdtemp()); src = tmp / "captions_10_20231122.json"; src.write_text(json.dumps(recs))
c = run(src, None, tmp / "o.html", tmp / "o.nt.gz"); assert c["events"] == 3 and (tmp / "o.html").exists() and len(gzip.open(tmp / "o.nt.gz", "rt").read().splitlines()) == c["triples"]
print("ok")
