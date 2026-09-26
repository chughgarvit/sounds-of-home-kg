"""Visualise a SAREF observation KG (DAHCC participant, or our Sounds of Home / SINS exports) as a state timeline + schema.

Usage: python scripts/kg_timeline.py data/real/kg/captions_14_20231122.nt.gz out.html
The KG is a flat observation log (obs -> sensor, property, timestamp, value); the only
readable picture of it is (a) which sensors measure what, and (b) the on/off timeline
of the state-bearing sensors. Both are rendered into a single self-contained HTML page.
"""
import gzip, json, re, sys
from pathlib import Path
from collections import defaultdict
import pandas as pd

POWER_ON_W = 25.0         # ponytail: 'on' = idle (10th pct) + 25 W; a learned per-appliance threshold if standby loads confuse it
MAX_ROWS_PER_GROUP = 8
PAT = re.compile(r'^<[^>]*/(obs\d+)> <([^>]+)> (.+) \.$')


def load(path):
    rows = {}
    with gzip.open(path, 'rt') as f:
        for line in f:
            m = PAT.match(line.rstrip('\n'))
            if not m:
                continue
            obs, pred, obj = m.groups()
            d = rows.setdefault(obs, {})
            p = pred.rsplit('/', 1)[-1]
            if p == 'measurementMadeBy':   d['sensor'] = obj.strip('<>').rsplit('/', 1)[-1]
            elif p == 'relatesToProperty': d['prop'] = '/'.join(obj.strip('<>').split('/')[-2:]) if '/property/' in obj else obj.strip('<>').rsplit('/', 1)[-1]
            elif p == 'hasTimestamp':      d['ts'] = obj.split('"')[1]
            elif p == 'hasValue':          d['value'] = obj.split('"')[1]
    df = pd.DataFrame.from_dict(rows, orient='index')
    df['ts'] = pd.to_datetime(df['ts'])
    return df.sort_values('ts')


def intervals(s, is_on):
    """Run-length group a boolean series (index=ts) into [start, end] pairs; last open interval ends at last sample."""
    out, start = [], None
    for ts, on in zip(s.index, is_on):
        if on and start is None:
            start = ts
        elif not on and start is not None:
            out.append((start, ts)); start = None
    if start is not None:
        out.append((start, s.index[-1]))
    return out


def intervals_from_stamps(stamps, seg_sec=10.0, max_gap_sec=20.0):
    """Label-type graphs (our audio exports) only carry observations where the label fired: consecutive stamps
    closer than max_gap form one interval; each interval ends seg_sec after its last stamp."""
    import pandas as pd
    out, start, prev = [], None, None
    for ts in sorted(stamps):
        if prev is not None and (ts - prev).total_seconds() > max_gap_sec:
            out.append((start, prev + pd.Timedelta(seconds=seg_sec))); start = None
        if start is None:
            start = ts
        prev = ts
    if start is not None:
        out.append((start, prev + pd.Timedelta(seconds=seg_sec)))
    return out


def rows_for(df):
    groups = []
    w = df[df.prop == 'environment.waterRunning::bool']
    groups.append(('Water running', [(sid.replace('water.pi.', 'tap '), intervals(g.set_index('ts').value, g.value.values == 'true'))
                                     for sid, g in w.groupby('sensor')]))
    p = df[df.prop == 'people.presence.detected']
    groups.append(('Presence (per room)', [(('room ' + sid.split('.')[2]) if sid.split('.')[2].isdigit() else sid.split('.')[2], intervals(g.set_index('ts').value, g.value.values == 'true'))
                                           for sid, g in p.groupby('sensor')]))
    e = df[df.prop == 'energy.power'].copy(); e['v'] = e.value.astype(float)
    e['on'] = e.v > e.groupby('sensor').v.transform(lambda v: v.quantile(0.10)) + POWER_ON_W
    top = e[e.on].groupby('sensor').v.agg(['count', 'max']).sort_values('count', ascending=False).head(MAX_ROWS_PER_GROUP)
    groups.append((f'Appliance power > idle + {POWER_ON_W:.0f} W', [(f"{sid.replace('velbus.', '')} (peak {mx:.0f} W)", intervals(e[e.sensor == sid].set_index('ts').v, e[e.sensor == sid].on.values))
                                                                    for sid, (_, mx) in top.iterrows()]))
    o = df[df.prop == 'environment.open']
    topo = o.groupby('sensor').size().sort_values(ascending=False).head(MAX_ROWS_PER_GROUP).index
    groups.append(('Door / cupboard open', [(sid.replace('enocean.', 'contact '), intervals(o[o.sensor == sid].set_index('ts').value, (o[o.sensor == sid].value == 'true').values))
                                            for sid in topo]))
    if not any(rows for _, rows in groups):          # not a DAHCC file: one row per property, on = value > 0.5
        groups = []
        for kind, g in df.groupby(df.prop.str.split('/').str[0]):
            top = g.groupby('prop').size().sort_values(ascending=False).head(MAX_ROWS_PER_GROUP * 2).index
            groups.append((kind, [(pr.split('/')[-1].replace('_', ' '), intervals_from_stamps(g[(g.prop == pr) & (g.value.astype(float) > 0.5)].ts)) for pr in top if not pr.endswith('/none')]))
        masked = df[(df.prop.str.endswith('/none')) & (df.value.astype(float) == 0)]
        if len(masked):
            groups.append(('evidence gaps', [('privacy-masked (no audio)', intervals_from_stamps(masked.ts))]))
    return groups


def schema(df):
    fam = lambda s: re.sub(r'\.(EnergyMeter\d|PresenceDetector|TemperatureSensor|LightSensor|\d+)$', '', s)
    fam = lambda s: (re.sub(r'^(mqtt\.steinelHPD2)\..*', r'\1', s) if s.startswith('mqtt.steinel') else
                     re.sub(r'^(velbus)\..*', r'\1', s) if s.startswith('velbus') else
                     re.sub(r'^(enocean)\..*', r'\1', s) if s.startswith('enocean') else
                     'netatmo' if re.match(r'^[0-9a-f]{2}(:[0-9a-f]{2}){5}$', s) else s)
    d = defaultdict(int)
    for sid, prop in zip(df.sensor, df.prop):
        d[(fam(sid), prop.rsplit('.', 1)[-1].replace('::bool', '').split('/')[-1])] += 1
    return [{'from': a, 'to': b, 'n': n} for (a, b), n in d.items()]


def render(groups, edges, title, t0, t1, out):
    data = [{'group': g, 'rows': [{'label': l, 'iv': [[a.isoformat(), b.isoformat()] for a, b in iv]} for l, iv in rows]} for g, rows in groups]
    html = TEMPLATE.replace('__DATA__', json.dumps(data)).replace('__EDGES__', json.dumps(edges)) \
                   .replace('__TITLE__', title).replace('__T0__', t0.isoformat()).replace('__T1__', t1.isoformat())
    open(out, 'w').write(html)


TEMPLATE = r'''<!doctype html><html><head><meta charset="utf-8"><title>__TITLE__</title>
<script src="https://cdnjs.cloudflare.com/ajax/libs/vis-network/9.1.9/dist/vis-network.min.js"></script>
<style>
:root{color-scheme:light;--surface:#fcfcfb;--page:#f9f9f7;--ink:#0b0b0b;--ink2:#52514e;--muted:#898781;--grid:#e1e0d9;--axis:#c3c2b7;
--s1:#2a78d6;--s2:#eb6834;--s3:#1baf7a;--s4:#eda100}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){color-scheme:dark;--surface:#1a1a19;--page:#0d0d0d;--ink:#fff;--ink2:#c3c2b7;--grid:#2c2c2a;--axis:#383835;--s1:#3987e5;--s2:#d95926;--s3:#199e70;--s4:#c98500}}
body{margin:0;background:var(--page);color:var(--ink);font:14px system-ui,-apple-system,"Segoe UI",sans-serif}
main{max-width:1200px;margin:0 auto;padding:24px}
h1{font-size:20px;margin:0 0 4px}p.sub{color:var(--ink2);margin:0 0 16px}
section{background:var(--surface);border:1px solid var(--grid);border-radius:8px;padding:16px;margin-bottom:20px}
h2{font-size:15px;margin:0 0 8px}
.legend{display:flex;gap:16px;flex-wrap:wrap;color:var(--ink2);font-size:12px;margin-bottom:8px}.legend span::before{content:"";display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px;vertical-align:-1px;background:var(--c)}
svg text{fill:var(--ink2);font-size:12px}svg .grid{stroke:var(--grid)}svg .axis{stroke:var(--axis)}svg .lab{fill:var(--ink)}svg .grp{fill:var(--ink);font-weight:600}
rect.bar{rx:2}rect.bar:hover{stroke:var(--ink);stroke-width:1}
#tip{position:fixed;pointer-events:none;background:var(--surface);color:var(--ink);border:1px solid var(--axis);border-radius:6px;padding:6px 8px;font-size:12px;display:none;box-shadow:0 2px 8px rgba(0,0,0,.15)}
#net{height:560px;border:1px solid var(--grid);border-radius:6px}
table{border-collapse:collapse;font-size:12px;width:100%}td,th{border-bottom:1px solid var(--grid);padding:4px 6px;text-align:left;font-variant-numeric:tabular-nums}
details summary{cursor:pointer;color:var(--ink2)}
</style></head><body><main>
<h1>__TITLE__</h1><p class="sub">SAREF observation graph. Each bar is an interval during which the sensor reported that state or label. Hover a bar for times.</p>
<section><h2>State timeline</h2><div class="legend" id="legend"></div><div id="tl"></div>
<details><summary>Table view</summary><table id="tbl"></table></details></section>
<section><h2>Sensor families → measured properties</h2><p class="sub">Edge width = number of observations. Drag nodes; scroll to zoom.</p><div id="net"></div></section>
</main><div id="tip"></div>
<script>
const DATA=__DATA__,EDGES=__EDGES__,T0=new Date("__T0__"),T1=new Date("__T1__");
const COLORS=["var(--s1)","var(--s2)","var(--s3)","var(--s4)","var(--muted)"];
const colorOf=(g,i)=>g.group==="evidence gaps"?"var(--muted)":COLORS[i];
document.getElementById("legend").innerHTML=DATA.map((g,i)=>`<span style="--c:${colorOf(g,i)}">${g.group}</span>`).join("");
const L=230,W=1140,RH=22,GH=28,P=24;let rows=[];DATA.forEach((g,gi)=>{rows.push({grp:g.group});g.rows.forEach(r=>rows.push({...r,gi,color:colorOf(g,gi)}))});
const H=P*2+rows.length*RH;const x=t=>L+(new Date(t)-T0)/(T1-T0)*(W-L-P);
let s=`<svg width="${W}" height="${H}" role="img" aria-label="state timeline">`;
const h0=new Date(T0);h0.setSeconds(0,0);h0.setMinutes(h0.getMinutes()<30?30:60);for(let h=h0;h<=T1;h.setMinutes(h.getMinutes()+30)){const X=x(h);s+=`<line class="grid" x1="${X}" x2="${X}" y1="${P}" y2="${H-P}"/><text x="${X}" y="${P-8}" text-anchor="middle">${h.toTimeString().slice(0,5)}</text>`}
rows.forEach((r,i)=>{const y=P+i*RH;if(r.grp){s+=`<text class="grp" x="0" y="${y+15}">${r.grp}</text>`;return}
s+=`<text class="lab" x="12" y="${y+15}">${r.label}</text>`;r.iv.forEach(([a,b])=>{const x1=x(a),x2=Math.max(x(b),x1+2);s+=`<rect class="bar" x="${x1}" y="${y+4}" width="${x2-x1}" height="${RH-8}" fill="${r.color}" data-t="${r.label}: ${a.slice(11,19)} → ${b.slice(11,19)}"/>`})});
s+=`<line class="axis" x1="${L}" x2="${W-P}" y1="${H-P}" y2="${H-P}"/></svg>`;document.getElementById('tl').innerHTML=s;
const tip=document.getElementById('tip');document.querySelectorAll('rect.bar').forEach(r=>{r.onmousemove=e=>{tip.style.display='block';tip.style.left=(e.clientX+12)+'px';tip.style.top=(e.clientY+12)+'px';tip.textContent=r.dataset.t};r.onmouseleave=()=>tip.style.display='none'});
let t='<tr><th>Group</th><th>Row</th><th>Start</th><th>End</th></tr>';DATA.forEach(g=>g.rows.forEach(r=>r.iv.forEach(([a,b])=>t+=`<tr><td>${g.group}</td><td>${r.label}</td><td>${a.slice(11,19)}</td><td>${b.slice(11,19)}</td></tr>`)));document.getElementById('tbl').innerHTML=t;
const ids=new Map(),nodes=[],edges=[];const nid=(n,kind)=>{if(!ids.has(n)){ids.set(n,nodes.length);nodes.push({id:nodes.length,label:n,shape:kind==='s'?'box':'ellipse',color:kind==='s'?{background:getComputedStyle(document.documentElement).getPropertyValue('--s1').trim(),border:'transparent'}:{background:getComputedStyle(document.documentElement).getPropertyValue('--grid').trim(),border:'transparent'},font:{color:kind==='s'?'#fff':getComputedStyle(document.documentElement).getPropertyValue('--ink').trim(),size:16},scaling:{label:{drawThreshold:1}}})}return ids.get(n)};
EDGES.forEach(e=>edges.push({from:nid(e.from,'s'),to:nid(e.to,'p'),width:Math.max(1,Math.log10(e.n)),title:`${e.from} → ${e.to}: ${e.n} observations`,color:{color:getComputedStyle(document.documentElement).getPropertyValue('--axis').trim()}}));
new vis.Network(document.getElementById('net'),{nodes,edges},{nodes:{scaling:{label:{drawThreshold:1}}},physics:{stabilization:true,barnesHut:{gravitationalConstant:-3000,springLength:90,springConstant:0.05}},interaction:{hover:true}});
</script></body></html>'''


if __name__ == '__main__':
    src, out = sys.argv[1], sys.argv[2]
    df = load(src)
    groups = rows_for(df)
    render(groups, schema(df), f"{Path(src).name.split('.')[0]}: state timeline", df.ts.min(), df.ts.max(), out)
    n = sum(len(iv) for _, rows in groups for _, iv in rows)
    assert n > 0, "no intervals found - is this a DAHCC observation KG?"
    print(f"{len(df)} observations, {n} intervals in {sum(len(r) for _, r in groups)} rows -> {out}")
