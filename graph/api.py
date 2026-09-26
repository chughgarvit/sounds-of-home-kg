"""Contract 2: the only way downstream code (QA, benchmark) touches the graph.
upsert(record) · query(entity, t_range) · history(entity) · provenance(node_id)"""
from .build import HomeGraph, ACTIVITY_TO_APPLIANCE


def _entity_nodes(hg, entity):
    """entity = appliance key ('tap'), activity label ('Running Water in Sink'), or a node id."""
    g = hg.g
    if entity in g:
        return [entity]
    if f"app:{entity}" in g:
        return [f"app:{entity}"]
    if f"act:{entity}" in g:
        return [f"act:{entity}"]
    app = ACTIVITY_TO_APPLIANCE.get(entity)
    return [f"app:{app}"] if app and f"app:{app}" in g else []


def upsert(hg: HomeGraph, record):
    return hg.upsert(record)


def query(hg: HomeGraph, entity, t_range=None):
    """Events, states and blocks about `entity` overlapping [t0, t1] (whole day if None), sorted by time."""
    g = hg.g
    out = []
    for nid in _entity_nodes(hg, entity):
        for u, v, k in g.in_edges(nid, keys=True):
            n = g.nodes[u]
            if n["type"] in ("SoundEvent", "State", "ActivityBlock"):
                out.append((u, n))
    if t_range:
        t0, t1 = t_range
        out = [(i, n) for i, n in out if n["t_start"] <= t1 and (n.get("t_end") is None or n["t_end"] >= t0)]
    return sorted(out, key=lambda x: x[1]["t_start"])


def history(hg: HomeGraph, entity):
    """State intervals of an appliance, oldest first: [{state, t_start, t_end, confidence, status, n_evidence, closed_by}]."""
    return [dict(id=i, **{k: n[k] for k in ("state", "t_start", "t_end", "confidence", "status", "n_evidence", "closed_by", "masked_inside") if k in n})
            for i, n in query(hg, entity) if n["type"] == "State"]


def provenance(hg: HomeGraph, node_id):
    """The 10 s clips a node rests on (itself for an event; its evidence for a state; its members for a block)."""
    g = hg.g; n = g.nodes[node_id]
    if n["type"] == "SoundEvent":
        return [n["clip_file"]]
    if n["type"] == "State":
        return [g.nodes[e]["clip_file"] for _, e, k in g.out_edges(node_id, keys=True) if k == "evidenced_by"]
    if n["type"] == "ActivityBlock":
        return [g.nodes[e]["clip_file"] for e, _, k in g.in_edges(node_id, keys=True) if k == "member_of"]
    return []
