"""Render the temporal event-state graph of one recorder-day: time on the x axis, one lane per appliance
(State intervals) and per activity type (SoundEvents inside their ActivityBlocks), evidence edges from
each State to the events it rests on, and derived next-edges between consecutive States.

Usage: python scripts/temporal_graph_view.py data/real/captions_10_20231122.json data/real/recorders.json out.html
"""
import json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from graph import build_graph  # noqa: E402


def layout(hg):
    g = hg.g
    states = sorted((n for n, a in g.nodes(data=True) if a["type"] == "State"), key=lambda n: g.nodes[n]["t_start"])
    events = sorted((n for n, a in g.nodes(data=True) if a["type"] == "SoundEvent"), key=lambda n: g.nodes[n]["t_start"])
    blocks = sorted((n for n, a in g.nodes(data=True) if a["type"] == "ActivityBlock"), key=lambda n: g.nodes[n]["t_start"])
    apps = []
    for s in states:
        a = g.nodes[s]["appliance"]
        if a not in apps:
            apps.append(a)
    acts = []
    for e in events:
        for lbl in (g.nodes[e]["activity"], g.nodes[e]["background"]):
            if lbl and lbl not in acts:
                acts.append(lbl)
    S = [dict(id=s, lane=g.nodes[s]["appliance"], **{k: g.nodes[s][k] for k in ("t_start", "t_end", "status", "confidence", "n_evidence", "closed_by", "masked_inside")}) for s in states]
    E = [dict(id=e, lanes=[l for l in (g.nodes[e]["activity"], g.nodes[e]["background"]) if l], **{k: g.nodes[e][k] for k in ("t_start", "t_end", "confidence", "description", "clip_file")}) for e in events]
    B = [dict(id=b, lane=g.nodes[b]["activity"], **{k: g.nodes[b][k] for k in ("t_start", "t_end", "n_events", "confidence")}) for b in blocks]
    EV = [(u, v) for u, v, k in g.edges(keys=True) if k == "evidenced_by"]
    NX = [(S[i]["id"], S[i + 1]["id"]) for i in range(len(S) - 1) if S[i]["lane"] == S[i + 1]["lane"]]
    NX = [(a, b) for lane in apps for a, b in zip([s["id"] for s in S if s["lane"] == lane], [s["id"] for s in S if s["lane"] == lane][1:])]
    return dict(room=hg.room, recorder=hg.recorder, apps=apps, acts=acts, states=S, events=E, blocks=B, evidence=EV, next=NX,
                t0=min(e["t_start"] for e in E) if E else 0, t1=max(e["t_end"] for e in E) if E else 1,
                counts=dict(events=len(E), states=len(S), blocks=len(B), evidence=len(EV)))


TEMPLATE = r'''<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title>
<style>
:root{color-scheme:light;--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--surface:#1a1a19;--page:#0d0d0d;--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500}}
body{margin:0;background:var(--page);color:var(--ink);font:14px system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1400px;margin:0 auto;padding:24px}
h1{font-size:20px;margin:0 0 4px}p.sub{color:var(--ink2);margin:0 0 12px}section{background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:16px}
.legend{display:flex;gap:18px;flex-wrap:wrap;color:var(--ink2);font-size:12px;margin-bottom:8px;align-items:center}.legend i{display:inline-block;width:12px;height:12px;margin-right:6px;vertical-align:-2px;border-radius:2px}
svg{display:block;width:100%;height:auto;cursor:grab;user-select:none}button{font:12px system-ui;padding:2px 8px}svg text{fill:var(--ink2);font-size:11px}svg .lab{fill:var(--ink)}svg .hdr{fill:var(--ink);font-weight:600}
.state{fill:var(--s1);opacity:.9}.state.tentative{opacity:.45;stroke:var(--s1);stroke-dasharray:3 2;fill:none;stroke-width:1.5}.state.open{}
.block{fill:var(--s3);opacity:.18}.ev{fill:var(--s2)}.ev.bg{fill:var(--s4)}
.edge{stroke:var(--s1);stroke-opacity:.18;stroke-width:1}.edge.hi{stroke-opacity:.9;stroke-width:1.5}.next{stroke:var(--ink2);stroke-opacity:.6;stroke-width:1;marker-end:url(#arrow)}
.grid{stroke:var(--grid)}.axis{stroke:var(--axis)}.gap{fill:var(--muted);opacity:.25}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--axis);border-radius:6px;padding:6px 8px;font-size:12px;display:none;max-width:360px;box-shadow:0 2px 8px rgba(0,0,0,.15)}
</style></head><body><main><h1>__TITLE__</h1>
<p class="sub">Temporal event-state graph built online from the day's caption records. x = clock time. Hover anything; click a state to highlight the sound events it rests on. Drag to pan, ⌘/Ctrl + wheel or the buttons to zoom.</p>
<section><div class="legend"><span><i style="background:var(--s1)"></i>State (confirmed) · dashed = tentative · open right edge = still on when audio ended</span><span><i style="background:var(--s2)"></i>SoundEvent (activity)</span><span><i style="background:var(--s4)"></i>SoundEvent (background)</span><span><i style="background:var(--s3);opacity:.35"></i>ActivityBlock (episode)</span><span><i style="background:var(--s1);opacity:.3"></i>evidenced_by edge</span><span>→ next state (derived)</span><span id="counts"></span><span style="margin-left:auto"><button id="zin">＋</button> <button id="zout">－</button> <button id="zreset">reset</button> <span id="range"></span></span></div><div id="svg"></div></section></main><div id="tip"></div>
<script>
const D=__DATA__;const DAY0=D.t0,DAY1=D.t1;const L=210,W=1360,RH=26,P=28;
const lanes=[...D.apps.map(a=>({kind:'app',name:a})),...D.acts.map(a=>({kind:'act',name:a}))];
const laneY={};lanes.forEach((l,i)=>laneY[l.kind+':'+l.name]=P+40+i*RH);const H=P+40+lanes.length*RH+P;
const hh=t=>{const h=Math.floor(t/3600),m=Math.floor(t%3600/60);return `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`};
let T0=DAY0,T1=DAY1,hiState=null;
function draw(){
 const x=t=>L+(t-T0)/(T1-T0)*(W-L-P);const vis=(a,b)=>b>=T0&&a<=T1;const span=T1-T0;const step=span>6*3600?1800:span>2*3600?600:span>1800?300:60;
 let s=`<svg viewBox="0 0 ${W} ${H}" id="g"><defs><marker id="arrow" viewBox="0 0 6 6" refX="6" refY="3" markerWidth="6" markerHeight="6" orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="var(--ink2)"/></marker><clipPath id="clip"><rect x="${L}" y="0" width="${W-L-P+8}" height="${H}"/></clipPath></defs>`;
 for(let t=Math.ceil(T0/step)*step;t<=T1;t+=step){s+=`<line class="grid" x1="${x(t)}" x2="${x(t)}" y1="${P+28}" y2="${H-P}"/>`;if(t%(step*2)==0||step<=300)s+=`<text x="${x(t)}" y="${P+20}" text-anchor="middle">${hh(t)}</text>`}
 s+=`<text class="hdr" x="0" y="${P+34}">Appliances${D.room?' · '+D.room:''}</text>`;if(D.acts.length)s+=`<text class="hdr" x="0" y="${P+34+D.apps.length*RH}">Activity types</text>`;
 lanes.forEach(l=>{const y=laneY[l.kind+':'+l.name];s+=`<text class="lab" x="12" y="${y+4}">${l.name.replace(/_/g,' ')}</text><line class="grid" x1="${L}" x2="${W-P}" y1="${y+RH/2}" y2="${y+RH/2}"/>`});
 s+=`<g clip-path="url(#clip)">`;const pos={};
 D.blocks.forEach(b=>{if(!vis(b.t_start,b.t_end))return;const y=laneY['act:'+b.lane];s+=`<rect class="block" x="${x(b.t_start)}" y="${y-10}" width="${Math.max(2,x(b.t_end)-x(b.t_start))}" height="20" rx="4" data-t="ActivityBlock ${b.lane}: ${hh(b.t_start)}–${hh(b.t_end)}, ${b.n_events} events, conf ${b.confidence}"/>`});
 D.events.forEach(e=>{if(!vis(e.t_start,e.t_end))return;e.lanes.forEach((ln,i)=>{const y=laneY['act:'+ln];const cx=x(e.t_start)+1.5;if(i==0)pos[e.id]=[cx,y];s+=`<circle class="ev ${i?'bg':''}" cx="${cx}" cy="${y}" r="3" data-t="SoundEvent ${hh(e.t_start)} · ${ln} · conf ${e.confidence}<br>${e.description}<br>${e.clip_file}"/>`})});
 D.states.forEach(st=>{const te=st.t_end==null?DAY1:st.t_end;if(!vis(st.t_start,te))return;const y=laneY['app:'+st.lane];const x1=x(st.t_start),x2=st.t_end==null?x(DAY1)+6:x(st.t_end);pos[st.id]=[(x1+Math.min(x2,x(T1)))/2,y+7];
  s+=`<rect class="state ${st.status}${st.t_end==null?' open':''}" x="${x1}" y="${y-7}" width="${Math.max(3,x2-x1)}" height="14" rx="3" data-id="${st.id}" data-t="State ${st.lane} running ${hh(st.t_start)} → ${st.t_end==null?'still on when audio ended':hh(st.t_end)}<br>${st.status}, conf ${st.confidence}, ${st.n_evidence} evidence windows, closed by ${st.closed_by}${st.masked_inside?', '+st.masked_inside+' masked windows inside':''}"/>`;
  if(st.t_end==null&&T1>=DAY1)s+=`<text x="${x(DAY1)+8}" y="${y+4}">▶ open</text>`});
 D.evidence.forEach(([a,b])=>{if(pos[a]&&pos[b])s+=`<line class="edge${a==hiState?' hi':''}" data-s="${a}" x1="${pos[a][0]}" y1="${pos[a][1]}" x2="${pos[b][0]}" y2="${pos[b][1]}"/>`});
 D.next.forEach(([a,b])=>{const A=D.states.find(z=>z.id==a),B=D.states.find(z=>z.id==b);const y=laneY['app:'+A.lane];const x1=A.t_end==null?x(DAY1):x(A.t_end),x2=x(B.t_start);if(x2-x1>8&&vis(A.t_end||DAY1,B.t_start))s+=`<line class="next" x1="${x1+1}" y1="${y}" x2="${x2-1}" y2="${y}"/>`});
 s+=`</g><line class="axis" x1="${L}" x2="${W-P}" y1="${H-P}" y2="${H-P}"/></svg>`;document.getElementById('svg').innerHTML=s;
 const tip=document.getElementById('tip');document.querySelectorAll('[data-t]').forEach(el=>{el.onmousemove=e=>{tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';tip.innerHTML=el.dataset.t};el.onmouseleave=()=>tip.style.display='none'});
 document.querySelectorAll('rect.state').forEach(el=>el.onclick=()=>{hiState=hiState==el.dataset.id?null:el.dataset.id;draw()});
 document.getElementById('range').textContent=`${hh(T0)} – ${hh(T1)}`;
}
function zoom(k,at){const c=at==null?(T0+T1)/2:at;let span=(T1-T0)*k;span=Math.max(600,Math.min(DAY1-DAY0,span));let a=c-(c-T0)/(T1-T0)*span,b=a+span;if(a<DAY0){a=DAY0;b=a+span}if(b>DAY1){b=DAY1;a=b-span}T0=a;T1=b;draw()}
document.getElementById('zin').onclick=()=>zoom(0.5);document.getElementById('zout').onclick=()=>zoom(2);document.getElementById('zreset').onclick=()=>{T0=DAY0;T1=DAY1;draw()};
const box=document.getElementById('svg');let drag=null;
box.addEventListener('wheel',e=>{if(!(e.ctrlKey||e.metaKey))return;e.preventDefault();const r=box.getBoundingClientRect();const at=T0+((e.clientX-r.left)/r.width*W-L)/(W-L-P)*(T1-T0);zoom(e.deltaY<0?0.8:1.25,at)},{passive:false});
box.addEventListener('mousedown',e=>{drag=[e.clientX,T0,T1]});window.addEventListener('mouseup',()=>drag=null);
box.addEventListener('mousemove',e=>{if(!drag)return;const r=box.getBoundingClientRect();const dt=-(e.clientX-drag[0])/r.width*W/(W-L-P)*(drag[2]-drag[1]);let a=drag[1]+dt,b=drag[2]+dt;if(a<DAY0){b+=DAY0-a;a=DAY0}if(b>DAY1){a-=b-DAY1;b=DAY1}T0=a;T1=b;draw()});
draw();document.getElementById('counts').textContent=`${D.counts.events} events · ${D.counts.states} states · ${D.counts.blocks} episodes · ${D.counts.evidence} evidence edges`;
</script></body></html>'''


def render(captions, recorders_json, out):
    recs = json.load(open(captions)); name = Path(captions).stem.split("_")
    recorder, date = (name[1], name[2]) if len(name) >= 3 else (None, "")
    room = None
    if recorders_json and Path(recorders_json).exists() and recorder:
        room = json.load(open(recorders_json)).get(recorder, {}).get("room")
    hg = build_graph(recs, room=room, recorder=recorder)
    d = layout(hg)
    title = f"Temporal graph · recorder {recorder or '?'}{' (' + room + ')' if room else ''} · {date[:4]}-{date[4:6]}-{date[6:]}" if date else f"Temporal graph · {Path(captions).stem}"
    Path(out).write_text(TEMPLATE.replace("__TITLE__", title).replace("__DATA__", json.dumps(d)))
    return d["counts"]


if __name__ == "__main__":
    c = render(sys.argv[1], sys.argv[2] if len(sys.argv) > 3 else None, sys.argv[-1])
    print(c, "->", sys.argv[-1])
