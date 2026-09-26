"""python scripts/test_temporal_graph_view.py — layout counts agree with the graph; page renders."""
import json, sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from graph import build_graph  # noqa: E402
from temporal_graph_view import layout, render  # noqa: E402
recs = json.load(open(Path(__file__).resolve().parents[1] / "data/mock_captions_sample.json"))
hg = build_graph(recs, room="kitchen", recorder="mock"); d = layout(hg)
g = hg.g
assert d["counts"]["events"] == sum(1 for _, a in g.nodes(data=True) if a["type"] == "SoundEvent")
assert d["counts"]["states"] == sum(1 for _, a in g.nodes(data=True) if a["type"] == "State") and d["counts"]["states"] > 0
assert d["counts"]["evidence"] == sum(1 for _, _, k in g.edges(keys=True) if k == "evidenced_by")
assert all(a != b and any(s["id"] == a for s in d["states"]) for a, b in d["next"])
tmp = Path(tempfile.mkdtemp()); src = tmp / "captions_mock_20231122.json"; src.write_text(json.dumps(recs))
c = render(src, None, tmp / "out.html"); assert c == d["counts"] and "<svg" not in (tmp / "out.html").read_text()[:200] and "draw()" in (tmp / "out.html").read_text()
print("ok")
