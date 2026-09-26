"""Interactive event graph of a recorder-day (DAHCC event-graph shape), plus its N-Triples export.

Usage: python scripts/event_graph_view.py data/real/captions_10_20231122.json data/real/recorders.json out.html [out.nt.gz]
Click an Event to expand its States, a State to expand its Observations, an Observation to show sensor/value/clip.
"""
import gzip, json, re, sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "scripts"))
from graph import build_graph  # noqa: E402
from graph.eventgraph import build_event_graph  # noqa: E402

BASE = "https://home-audio-kg-bench.org/soh"
TEMPLATE = r'''<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.js"></script>
<style>
:root{color-scheme:light;--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--surface:#1a1a19;--page:#0d0d0d;--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;--s1:#3987e5;--s2:#d95926;--s3:#199e70}}
body{margin:0;background:var(--page);color:var(--ink);font:14px system-ui,-apple-system,"Segoe UI",sans-serif}main{max-width:1500px;margin:0 auto;padding:20px}
h1{font-size:20px;margin:0 0 4px}p.sub{color:var(--ink2);margin:0 0 10px}section{background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:12px}
.bar{display:flex;gap:10px;align-items:center;flex-wrap:wrap;font-size:12px;color:var(--ink2);margin-bottom:8px}button{font:12px system-ui;padding:3px 9px}
#net{height:760px;border:1px solid var(--grid);border-radius:6px;background:var(--surface)}
.legend i{display:inline-block;width:12px;height:12px;border-radius:50%;margin:0 5px 0 10px;vertical-align:-2px;border:1.5px solid var(--ink)}
</style></head><body><main><h1>__TITLE__</h1>
<p class="sub">Event-centric graph. Events are activity episodes chained by <b>hasPreviousEvent</b>; each carries its activity label and timestamps. Depth 1: the appliance and room <b>States</b> in force during the event. Depth 2: the 10 s <b>Observations</b> each state rests on (the same observation IRIs as the SAREF graph). Depth 3: sensor, value, clip.</p>
<section><div class="bar"><span>Expand all to depth:</span><button data-d="0">0 events</button><button data-d="1">1 states</button><button data-d="2">2 observations</button><button data-d="3">3 leaves</button><span style="margin-left:6px">or click a node to expand / collapse it</span>
<span class="legend" style="margin-left:auto"><i style="background:var(--surface)"></i>Event <i style="background:var(--s1)"></i>State <i style="background:var(--muted)"></i>Observation <i style="background:var(--grid)"></i>leaf</span><span id="counts"></span></div><div id="net"></div></section></main>
<script>
const D=__DATA__;const css=v=>getComputedStyle(document.documentElement).getPropertyValue(v).trim();
const ink=css('--ink'),surface=css('--surface'),s1=css('--s1'),muted=css('--muted'),grid=css('--grid'),ink2=css('--ink2');
const style={Event:{shape:'circle',color:{background:surface,border:ink},font:{color:ink,size:11}},State:{shape:'circle',color:{background:s1,border:s1},font:{color:'#fff',size:11}},
 Obs:{shape:'circle',color:{background:muted,border:muted},font:{color:'#fff',size:10}},Sensor:{shape:'box',color:{background:grid,border:grid},font:{color:ink,size:10}},Value:{shape:'box',color:{background:grid,border:grid},font:{color:ink,size:10}},Clip:{shape:'box',color:{background:grid,border:grid},font:{color:ink,size:9}}};
const children={};D.edges.forEach(e=>{if(e.kind!='prev'){(children[e.from]=children[e.from]||[]).push(e.to)}});
const byId={};D.nodes.forEach(n=>byId[n.id]=n);
const events=D.nodes.filter(n=>n.type=='Event');const open=new Set();
const tip=n=>Object.entries(n).filter(([k])=>!['id','label','level','type'].includes(k)&&n[k]!=null).map(([k,v])=>`${k}: ${v}`).join('\n');
const nodes=new vis.DataSet(),edges=new vis.DataSet();
function visible(){const vis=new Set(events.map(e=>e.id));const stack=[...events.map(e=>e.id)];while(stack.length){const p=stack.pop();if(open.has(p))(children[p]||[]).forEach(c=>{if(!vis.has(c)){vis.add(c);stack.push(c)}})}return vis}
function layout(vis){
 // events left→right by time; each expanded subtree centred under its parent, width-aware, no overlaps
 const X={},Y={},W={};const GAP={0:90,1:110,2:70,3:95};const LEVY={0:0,1:260,2:520,3:720};
 const width=id=>{const kids=open.has(id)?(children[id]||[]).filter(c=>vis.has(c)):[];if(!kids.length){W[id]=1;return 1}let w=0;kids.forEach(c=>{if(!(c in W))w+=width(c)});W[id]=Math.max(1,w);return W[id]};
 const placed=new Set();const place=(id,x0)=>{if(placed.has(id))return;placed.add(id);const n=byId[id];Y[id]=LEVY[n.level];const kids=open.has(id)?(children[id]||[]).filter(c=>vis.has(c)&&!placed.has(c)):[];
  if(!kids.length){X[id]=x0+ (W[id]*GAP[n.level])/2;return}let cx=x0;kids.forEach(c=>{place(c,cx);cx+=W[c]*GAP[byId[c].level]});X[id]=(X[kids[0]]+X[kids[kids.length-1]])/2};
 let cx=0;const unit=90;events.forEach(e=>{width(e.id)});events.forEach(e=>{place(e.id,cx);cx+=Math.max(1,W[e.id])*unit+140});
 return {X,Y}}
function render(){const vis=visible();const {X,Y}=layout(vis);const N=[],E=[];
 vis.forEach(id=>{const n=byId[id];N.push({id,label:n.label,title:tip(n),x:X[id],y:Y[id],fixed:true,...style[n.type],borderWidth:n.type=='Event'?1.5:1,size:n.type=='Obs'?14:n.type=='State'?22:26,shapeProperties:n.status=='tentative'?{borderDashes:[4,3]}:{}})});
 D.edges.forEach(e=>{if(vis.has(e.from)&&vis.has(e.to))E.push({id:e.from+'|'+e.to+'|'+e.label,from:e.from,to:e.to,label:e.label,arrows:'to',font:{size:9,color:ink2,strokeWidth:0,align:'middle'},color:{color:e.kind=='prev'?ink:e.kind=='state'?s1:muted,opacity:e.kind=='leaf'?.6:.9},smooth:e.kind=='prev'?{type:'curvedCW',roundness:.35}:false,width:e.kind=='prev'?1.5:1})});
 nodes.clear();edges.clear();nodes.add(N);edges.add(E);document.getElementById('counts').textContent=`${N.length} nodes · ${E.length} edges shown of ${D.nodes.length} / ${D.edges.length}`}
const net=new vis.Network(document.getElementById('net'),{nodes,edges},{physics:false,interaction:{hover:true,dragNodes:true,zoomView:true,dragView:true},edges:{selectionWidth:2}});
net.on('click',p=>{if(!p.nodes.length)return;const id=p.nodes[0];if(!(children[id]||[]).length)return;if(open.has(id))open.delete(id);else open.add(id);render()});
document.querySelectorAll('button[data-d]').forEach(b=>b.onclick=()=>{const d=+b.dataset.d;open.clear();D.nodes.forEach(n=>{if(n.level<d&&(children[n.id]||[]).length)open.add(n.id)});render();focusStart()});
events.slice(0,Math.min(events.length,4)).forEach(e=>open.add(e.id));render();
function focusStart(){const ids=nodes.getIds().filter(id=>{const n=byId[id];return events.slice(0,4).some(e=>e.id==id)||(n.level>=1&&nodes.get(id).x<nodes.get(events[Math.min(3,events.length-1)].id).x+200)});net.fit({nodes:ids,animation:false})}
focusStart();
</script></body></html>'''


def run(captions, recorders_json, out_html, out_nt=None):
    recs = json.load(open(captions)); name = Path(captions).stem.split("_")
    recorder, date = (name[1], name[2]) if len(name) >= 3 else ("mock", "20000101")
    room = json.load(open(recorders_json)).get(recorder, {}).get("room") if recorders_json and Path(recorders_json).exists() else None
    hg = build_graph(recs, room=room, recorder=recorder)
    eg = build_event_graph(hg, recs, BASE, recorder, datetime.strptime(date, "%Y%m%d"))
    title = f"Event graph · recorder {recorder}{' (' + room + ')' if room else ''} · {date[:4]}-{date[4:6]}-{date[6:]}"
    data = {k: eg[k] for k in ("nodes", "edges", "recorder", "room", "date")}
    Path(out_html).write_text(TEMPLATE.replace("__TITLE__", title).replace("__DATA__", json.dumps(data)))
    if out_nt:
        with gzip.open(out_nt, "wt") as f:
            f.write("\n".join(eg["triples"]) + "\n")
    return dict(events=sum(n["type"] == "Event" for n in eg["nodes"]), states=sum(n["type"] == "State" for n in eg["nodes"]),
                obs=sum(n["type"] == "Obs" for n in eg["nodes"]), edges=len(eg["edges"]), triples=len(eg["triples"]))


if __name__ == "__main__":
    a = sys.argv[1:]
    print(run(a[0], a[1], a[2], a[3] if len(a) > 3 else None), "->", a[2])
