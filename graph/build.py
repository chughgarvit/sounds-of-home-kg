"""Build the temporal event-state graph from caption records, online (one record at a time).

Node types: Room, Appliance, ActivityType, SoundEvent (one per labelled record), State (an interval on an
appliance, opened by evidence and closed by its absence), ActivityBlock (consecutive events of one activity
consolidated into an episode). Edges: instance_of, state_of, evidenced_by, member_of, located_in.
Time is an attribute; order is derived. Nothing is ever deleted; a State that never gets confirmed keeps
status 'tentative'. States are managed like tracks (perceptual anchoring / M-of-N track management):
opened by the first evidence, confirmed after CONFIRM_M evidence windows, kept through short quiet gaps,
kept (with a note) through privacy-masked stretches where there is no evidence either way, closed after
GAP_TOL consecutive windows that had audio but not the sound.
"""
import json
from statistics import mean

import networkx as nx

SEG_SEC = 10.0
GAP_TOL = 2            # consecutive audible windows without the sound that close a state (20 s)
MASK_TOL = 30          # masked windows tolerated inside a state (5 min): no evidence is not counter-evidence
CONFIRM_M = 2          # evidence windows needed to confirm a tentative state
BLOCK_GAP_SEC = 300    # gap that splits two episodes of the same activity
TENTATIVE_DISCOUNT = 0.5
MASKED_TEXT = "Audio unavailable (privacy-masked)."

# the only place this knowledge lives (SCHEMA.md). Backgrounds that are appliances are included.
ACTIVITY_TO_APPLIANCE = {
    "Running Water in Sink": "tap", "Shower": "shower", "Toilet Flushing": "toilet", "Washing Machine": "washing_machine",
    "Laundry": "washing_machine", "Dishwasher": "dishwasher", "Microwave": "microwave", "Blender": "blender",
    "Food Processor": "food_processor", "Coffee Grinder": "coffee_grinder", "Vacuum Cleaner": "vacuum_cleaner",
    "Hairdryer": "hairdryer", "Electric Razor": "razor", "Electric Toothbrush": "toothbrush", "Printer": "printer",
    "Shredder": "shredder", "Watching Television": "tv", "Typing on Keyboard": "computer", "Phone Ringing": "phone",
    "Timer Beeping": "timer", "Air Conditioning": "air_conditioning", "Fridge Humming": "fridge",
}


def _is_masked(r):
    return r.get("description") == MASKED_TEXT or (r.get("activity") is None and float(r.get("confidence", 1)) == 0)


class HomeGraph:
    """The graph plus the online state of every tracked appliance and episode (Contract 2 lives in api.py)."""

    def __init__(self, room=None, recorder=None):
        self.g = nx.MultiDiGraph(room=room, recorder=recorder)
        self.room = room
        self.recorder = recorder
        self._open = {}       # appliance -> state node id
        self._blocks = {}     # activity label -> block node id
        self.now = None
        if room:
            self.g.add_node(f"room:{room}", type="Room", label=room)

    # ---- nodes -------------------------------------------------------------------------------------------
    def _activity_type(self, label):
        nid = f"act:{label}"
        if nid not in self.g:
            self.g.add_node(nid, type="ActivityType", label=label)
        return nid

    def _appliance(self, key):
        nid = f"app:{key}"
        if nid not in self.g:
            self.g.add_node(nid, type="Appliance", label=key)
            if self.room:
                self.g.add_edge(nid, f"room:{self.room}", key="located_in", type="located_in")
        return nid

    # ---- online update -----------------------------------------------------------------------------------
    def upsert(self, r):
        """Ingest one caption record in time order. Returns the SoundEvent node id, or None for a null window."""
        t0, t1 = float(r["t_start"]), float(r["t_end"])
        self.now = t1
        masked = _is_masked(r)
        labels = [x for x in (r.get("activity"), r.get("background")) if x]
        ev = None
        if labels:
            ev = f"ev:{self.recorder or 'r'}:{int(t0)}"
            self.g.add_node(ev, type="SoundEvent", t_start=t0, t_end=t1, confidence=float(r["confidence"]),
                            description=r.get("description", ""), clip_file=r.get("clip_file"), activity=r.get("activity"),
                            background=r.get("background"))
            for lbl in labels:
                self.g.add_edge(ev, self._activity_type(lbl), key="instance_of", type="instance_of")
            if r.get("activity"):
                self._block(r["activity"], ev, t0, t1, float(r["confidence"]))
        fed = set()
        for lbl in labels:
            app = ACTIVITY_TO_APPLIANCE.get(lbl)
            if app:
                self._feed_state(app, ev, t0, t1, float(r["confidence"]))
                fed.add(app)
        for app in list(self._open):
            if app not in fed:
                self._miss(app, masked)
        return ev

    def _feed_state(self, app, ev, t0, t1, conf):
        sid = self._open.get(app)
        if sid is None:
            sid = f"st:{app}:{int(t0)}"
            self.g.add_node(sid, type="State", appliance=app, state="running", t_start=t0, t_end=None, status="tentative",
                            confidence=conf * TENTATIVE_DISCOUNT, n_evidence=0, misses=0, masked_run=0, masked_inside=0,
                            last_evidence=t1)
            self.g.add_edge(sid, self._appliance(app), key="state_of", type="state_of")
            self._open[app] = sid
        n = self.g.nodes[sid]
        self.g.add_edge(sid, ev, key="evidenced_by", type="evidenced_by")
        n["n_evidence"] += 1; n["misses"] = 0; n["masked_run"] = 0; n["last_evidence"] = t1
        confs = [self.g.nodes[e]["confidence"] for _, e, k in self.g.out_edges(sid, keys=True) if k == "evidenced_by"]
        if n["n_evidence"] >= CONFIRM_M:
            n["status"] = "confirmed"
        n["confidence"] = round(mean(confs) * (1.0 if n["status"] == "confirmed" else TENTATIVE_DISCOUNT), 3)

    def _miss(self, app, masked):
        sid = self._open[app]; n = self.g.nodes[sid]
        if masked:
            n["masked_run"] += 1; n["masked_inside"] += 1
            if n["masked_run"] <= MASK_TOL:
                return                                   # no audio: neither evidence nor counter-evidence
        else:
            n["misses"] += 1
            if n["misses"] <= GAP_TOL:
                return
        self._close(app, reason="masked" if masked else "silence")

    def _close(self, app, reason):
        sid = self._open.pop(app); n = self.g.nodes[sid]
        n["t_end"] = n["last_evidence"]; n["closed_by"] = reason

    def finish(self):
        """End of the stream: states still fed at the end stay open (t_end None); stale ones close."""
        for app in list(self._open):
            n = self.g.nodes[self._open[app]]
            if n["misses"] == 0 and n["masked_run"] == 0 and self.now is not None and n["last_evidence"] >= self.now - SEG_SEC:
                n["closed_by"] = "open_at_end_of_audio"; self._open.pop(app)
            else:
                self._close(app, reason="end_of_audio")
        return self

    def _block(self, act, ev, t0, t1, conf):
        bid = self._blocks.get(act)
        if bid is not None and t0 - self.g.nodes[bid]["t_end"] > BLOCK_GAP_SEC:
            bid = None
        if bid is None:
            bid = f"blk:{act}:{int(t0)}"
            self.g.add_node(bid, type="ActivityBlock", activity=act, t_start=t0, t_end=t1, n_events=0, confidence=conf)
            self.g.add_edge(bid, self._activity_type(act), key="instance_of", type="instance_of")
            self._blocks[act] = bid
        n = self.g.nodes[bid]
        self.g.add_edge(ev, bid, key="member_of", type="member_of")
        n["t_end"] = t1; n["n_events"] += 1
        n["confidence"] = round((n["confidence"] * (n["n_events"] - 1) + conf) / n["n_events"], 3)

    # ---- persistence --------------------------------------------------------------------------------------
    def save(self, path):
        json.dump(nx.node_link_data(self.g), open(path, "w"))

    @classmethod
    def load(cls, path):
        d = json.load(open(path)); hg = cls(); hg.g = nx.node_link_graph(d, multigraph=True, directed=True)
        hg.room, hg.recorder = hg.g.graph.get("room"), hg.g.graph.get("recorder")
        return hg


def build_graph(records, room=None, recorder=None):
    hg = HomeGraph(room=room, recorder=recorder)
    for r in sorted(records, key=lambda x: float(x["t_start"])):
        hg.upsert(r)
    return hg.finish()
