"""Event-centric view of a recorder-day (the DAHCC event-graph shape):

  Event_k --hasPreviousEvent--> Event_{k-1};  Event_k hasActivity "label", hasTimestamp, hasEndTimestamp
  Event_k --has<Appliance>State--> State (depth 1);  Event_k --hasRoomState--> RoomState
  State --hasObs--> Obs (depth 2, the SAREF observation IRIs of captions_to_nt);  Obs --hasSensor/hasValue/hasClip--> leaves

An Event is an ActivityBlock (episode) of the temporal graph; its States are the appliance States that
overlap it plus the room's occupancy state during it. Exported as N-Triples (vocabulary below) and as a
node/edge JSON for the interactive view.
"""
import re
from datetime import datetime, timedelta

EV = "https://home-audio-kg-bench.org/ev#"


def slug(s):
    return re.sub(r"[^A-Za-z0-9]+", "_", str(s)).strip("_")


def build_event_graph(hg, records, base, recorder, day):
    """Returns dict(nodes=[{id,type,label,level,...}], edges=[{from,to,label}], triples=[...])."""
    from scripts.captions_to_nt import obs_iris  # local import: scripts/ is on sys.path in every entry point
    g = hg.g
    recs = sorted(records, key=lambda r: float(r["t_start"]))
    iris = dict(zip((int(float(r["t_start"])) for r in recs), obs_iris(recs, base, recorder, day)))
    ds = f"{base}/{recorder}_{day:%Y%m%d}"
    ts = lambda t: (day + timedelta(seconds=float(t))).isoformat(timespec="seconds")
    hh = lambda t: (day + timedelta(seconds=float(t))).strftime("%H:%M:%S")
    nodes, T = [], []
    seen, seen_edges = set(), set()

    class _Edges(list):                      # a state under several events must not repeat its edges
        def append(self, e):
            key = (e["from"], e["to"], e["label"])
            if key not in seen_edges:
                seen_edges.add(key); super().append(e)
    edges = _Edges()

    def node(**kw):
        if kw["id"] not in seen:
            seen.add(kw["id"]); nodes.append(kw)

    blocks = sorted((n for n, a in g.nodes(data=True) if a["type"] == "ActivityBlock"), key=lambda n: g.nodes[n]["t_start"])
    states = [(n, a) for n, a in g.nodes(data=True) if a["type"] == "State"]
    prev = None
    for k, b in enumerate(blocks):
        a = g.nodes[b]; eid = f"{ds}/event{k}"
        node(id=eid, type="Event", level=0, label=f"Event {k}\n{a['activity']}\n{hh(a['t_start'])}", activity=a["activity"],
             t_start=ts(a["t_start"]), t_end=ts(a["t_end"]), n_events=a["n_events"], confidence=a["confidence"])
        T += [f"<{eid}> <{EV}hasActivity> \"{a['activity']}\" .", f"<{eid}> <{EV}hasTimestamp> \"{ts(a['t_start'])}\"^^<http://www.w3.org/2001/XMLSchema#dateTime> .",
              f"<{eid}> <{EV}hasEndTimestamp> \"{ts(a['t_end'])}\"^^<http://www.w3.org/2001/XMLSchema#dateTime> .", f"<{eid}> <{EV}confidence> \"{a['confidence']}\"^^<http://www.w3.org/2001/XMLSchema#float> ."]
        if prev:
            edges.append(dict(**{"from": eid, "to": prev}, label="hasPreviousEvent", kind="prev")); T.append(f"<{eid}> <{EV}hasPreviousEvent> <{prev}> .")
        prev = eid
        # depth 1: appliance states overlapping the event, plus the room state during it
        for sid, s in states:
            s_end = s["t_end"] if s["t_end"] is not None else 1e12
            if s["t_start"] <= a["t_end"] and s_end >= a["t_start"]:
                st_id = f"{ds}/state/{slug(sid)}"
                node(id=st_id, type="State", level=1, label=f"{s['appliance']}\nState", appliance=s["appliance"], state=s["state"], status=s["status"],
                     t_start=ts(s["t_start"]), t_end=None if s["t_end"] is None else ts(s["t_end"]), confidence=s["confidence"], n_evidence=s["n_evidence"], closed_by=s.get("closed_by"))
                pred = f"has{slug(s['appliance']).title().replace('_', '')}State"
                edges.append(dict(**{"from": eid, "to": st_id}, label=pred, kind="state")); T.append(f"<{eid}> <{EV}{pred}> <{st_id}> .")
                T += [f"<{st_id}> <{EV}appliance> \"{s['appliance']}\" .", f"<{st_id}> <{EV}state> \"{s['state']}\" .", f"<{st_id}> <{EV}status> \"{s['status']}\" .",
                      f"<{st_id}> <{EV}confidence> \"{s['confidence']}\"^^<http://www.w3.org/2001/XMLSchema#float> .", f"<{st_id}> <{EV}hasTimestamp> \"{ts(s['t_start'])}\"^^<http://www.w3.org/2001/XMLSchema#dateTime> ."]
                if s["t_end"] is not None:
                    T.append(f"<{st_id}> <{EV}hasEndTimestamp> \"{ts(s['t_end'])}\"^^<http://www.w3.org/2001/XMLSchema#dateTime> .")
                # depth 2: the observations behind the state
                for _, e, kk in g.out_edges(sid, keys=True):
                    if kk != "evidenced_by":
                        continue
                    en = g.nodes[e]; o = iris[int(en["t_start"])]
                    oid = o[0] if en.get("activity") and ACT_APP(en["activity"]) == s["appliance"] else (o[1] or o[0])
                    _obs(node, edges, T, st_id, oid, en, hh, recorder, base)
        room = hg.room or "room"
        rs = f"{ds}/state/{slug(room)}_{k}"
        node(id=rs, type="State", level=1, label=f"{room}\nState", appliance=room, state="occupied", status="derived", t_start=ts(a["t_start"]), t_end=ts(a["t_end"]), confidence=a["confidence"], n_evidence=a["n_events"])
        edges.append(dict(**{"from": eid, "to": rs}, label=f"has{slug(room).title()}State", kind="state")); T += [f"<{eid}> <{EV}has{slug(room).title()}State> <{rs}> .", f"<{rs}> <{EV}state> \"occupied\" .", f"<{rs}> <{EV}status> \"derived\" ."]
        for e, _, kk in g.in_edges(b, keys=True):
            if kk == "member_of":
                en = g.nodes[e]; _obs(node, edges, T, rs, iris[int(en["t_start"])][0], en, hh, recorder, base)
    return dict(nodes=nodes, edges=list(edges), triples=list(dict.fromkeys(T)), recorder=recorder, room=hg.room, date=day.strftime("%Y-%m-%d"))


def ACT_APP(label):
    from graph.build import ACTIVITY_TO_APPLIANCE
    return ACTIVITY_TO_APPLIANCE.get(label)


def _obs(node, edges, T, parent, oid, en, hh, recorder, base):
    node(id=oid, type="Obs", level=2, label=f"Obs\n{hh(en['t_start'])}", confidence=en["confidence"], description=en["description"], clip=en["clip_file"])
    edges.append(dict(**{"from": parent, "to": oid}, label="hasObs", kind="obs")); T.append(f"<{parent}> <{EV}hasObs> <{oid}> .")
    sensor, value, clip = f"{base}/mic/{recorder}", f"{oid}/value", f"{base}/clip/{slug(en['clip_file'])}"
    node(id=sensor, type="Sensor", level=3, label=f"mic {recorder}"); node(id=value, type="Value", level=3, label=f"{en['confidence']}"); node(id=clip, type="Clip", level=3, label=en["clip_file"])
    for tgt, pred in ((sensor, "hasSensor"), (value, "hasValue"), (clip, "hasClip")):
        edges.append(dict(**{"from": oid, "to": tgt}, label=pred, kind="leaf"))
    T += [f"<{oid}> <{EV}hasSensor> <{sensor}> .", f"<{oid}> <{EV}hasValue> \"{en['confidence']}\"^^<http://www.w3.org/2001/XMLSchema#float> .", f"<{oid}> <{EV}hasClip> <{clip}> ."]
