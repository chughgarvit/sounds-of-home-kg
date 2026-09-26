"""Ten assert-based checks over Contract 2 and the online state logic. python graph/test_api.py"""
import sys, tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph import build_graph, HomeGraph  # noqa: E402
from graph.api import history, provenance, query, upsert  # noqa: E402

def rec(t, act=None, bg=None, conf=0.8, masked=False):
    return {"t_start": t, "t_end": t + 10, "activity": act, "background": bg, "confidence": 0.0 if masked else conf,
            "description": "Audio unavailable (privacy-masked)." if masked else (act or "The house is quiet."), "clip_file": f"c{int(t)}.wav"}

# tap 3 windows, 2 quiet, tap 1 window (tentative), 3 quiet, masked stretch, tv running into the end of audio
recs = [rec(0, "Running Water in Sink", conf=.8), rec(10, "Running Water in Sink", "Fridge Humming", conf=.7), rec(20, "Running Water in Sink", conf=.9),
        rec(30), rec(40), rec(50), rec(60, "Running Water in Sink", conf=.6), rec(70), rec(80), rec(90),
        rec(100, "Watching Television"), rec(110, "Watching Television"), rec(120, masked=True), rec(130, masked=True), rec(140, "Watching Television")]
hg = build_graph(recs, room="kitchen", recorder="10")
g = hg.g
assert {g.nodes[n]["type"] for n in g} == {"Room", "Appliance", "ActivityType", "SoundEvent", "State", "ActivityBlock"}      # 1 all node types
tap = history(hg, "tap")
assert [(s["t_start"], s["t_end"], s["status"]) for s in tap] == [(0, 30, "confirmed"), (60, 70, "tentative")], tap          # 2 closed after GAP_TOL quiet windows; single window stays tentative
assert abs(tap[0]["confidence"] - 0.8) < 1e-6 and tap[0]["n_evidence"] == 3 and tap[1]["confidence"] == 0.3, tap             # 3 confidence = mean evidence; tentative discounted
assert len(provenance(hg, tap[0]["id"])) == 3 and provenance(hg, tap[0]["id"])[0] == "c0.wav"                                # 4 provenance to clips
tv = history(hg, "tv")
assert len(tv) == 1 and tv[0]["t_end"] is None and tv[0]["closed_by"] == "open_at_end_of_audio" and tv[0]["masked_inside"] == 2, tv   # 5 masked gap does not close; open at end = still on
fridge = history(hg, "fridge"); assert fridge and fridge[0]["status"] == "tentative"                                         # 6 background appliances tracked too
blocks = [n for i, n in query(hg, "Running Water in Sink") if n["type"] == "ActivityBlock"]
assert len(blocks) == 1 and blocks[0]["n_events"] == 4 and blocks[0]["t_end"] == 70, blocks                                  # 7 episode: 40 s gap < BLOCK_GAP merges the two runs
assert [n["type"] for _, n in query(hg, "tap", (25, 65))] == ["State", "State"]                                              # 8 range query on the appliance
ev = upsert(hg, rec(150, "Toilet Flushing")); assert ev in g and history(hg, "toilet")[0]["status"] == "tentative"          # 9 online upsert after build
p = Path(tempfile.mkdtemp()) / "g.json"; hg.save(p); back = HomeGraph.load(p)
assert sorted(back.g.nodes) == sorted(g.nodes) and back.g.number_of_edges() == g.number_of_edges() and back.room == "kitchen"  # 10 snapshot round trip
print("ok")
