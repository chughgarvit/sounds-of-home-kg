"""Render a timeline page per recorder-day graph plus an index. python scripts/kg_index.py data/real/kg data/real/recorders.json data/real/kg/index.html"""
import gzip, html, json, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from kg_timeline import load, render, rows_for, schema  # noqa: E402
from temporal_graph_view import render as render_temporal  # noqa: E402
from event_graph_view import run as render_events  # noqa: E402


def main(kg_dir, recorders_json, out):
    kg_dir, out = Path(kg_dir), Path(out)
    rec = json.load(open(recorders_json))
    rows = []
    for f in sorted(kg_dir.glob("captions_*.nt.gz")):
        r, date = f.stem.replace(".nt", "").split("_")[1:3]
        df = load(f)
        page = f.with_suffix("").with_suffix(".html")
        groups = rows_for(df)
        render(groups, schema(df), f"{rec[r]['home']} · recorder {r} ({rec[r]['room']}) · {date[:4]}-{date[4:6]}-{date[6:]}", df.ts.min(), df.ts.max(), page)
        captions = kg_dir.parent / f"captions_{r}_{date}.json"
        ev = {}
        if captions.exists():
            render_temporal(captions, recorders_json, kg_dir / f"temporal_{r}_{date}.html")
            ev = render_events(captions, recorders_json, kg_dir / f"events_{r}_{date}.html", kg_dir / f"events_{r}_{date}.nt.gz")
        labelled = df[~df.prop.str.endswith("/none")]
        rows.append(dict(home=rec[r]["home"], recorder=r, room=rec[r]["room"], date=f"{date[:4]}-{date[4:6]}-{date[6:]}",
                         hours=round((df.ts.max() - df.ts.min()).total_seconds() / 3600 + 10 / 3600, 1), obs=len(df),
                         labelled_pct=round(100 * len(labelled) / max(1, len(df)), 1),
                         triples=sum(1 for l in gzip.open(f, "rt") if l.strip()), page=page.name, events=ev.get("events", 0), states=ev.get("states", 0),
                         temporal=f"temporal_{r}_{date}.html" if captions.exists() else None, evpage=f"events_{r}_{date}.html" if captions.exists() else None))
    rows.sort(key=lambda x: (x["home"], x["recorder"], x["date"]))
    tr = "".join(f"<tr><td>{x['home']}</td><td>{x['recorder']}</td><td>{x['room']}</td><td><a href='{x['page']}'>{x['date']}</a></td>"
                 f"<td>{x['hours']}</td><td>{x['obs']:,}</td><td>{x['labelled_pct']}</td><td>{x['triples']:,}</td>"
                 f"<td>{('<a href=' + chr(39) + x['evpage'] + chr(39) + '>' + str(x['events']) + ' events / ' + str(x['states']) + ' states</a>') if x['evpage'] else '-'}</td>"
                 f"<td>{('<a href=' + chr(39) + x['temporal'] + chr(39) + '>timeline graph</a>') if x['temporal'] else '-'}</td></tr>" for x in rows)
    out.write_text(f"""<!doctype html><html><head><meta charset="utf-8"><title>Sounds of Home observation graphs</title>
<style>body{{font:14px system-ui,sans-serif;margin:24px;color:#0b0b0b;background:#f9f9f7}}table{{border-collapse:collapse}}td,th{{padding:4px 10px;border-bottom:1px solid #e1e0d9;text-align:left;font-variant-numeric:tabular-nums}}th{{background:#fcfcfb}}</style></head>
<body><h1>Sounds of Home as a SAREF observation graph</h1><p>{len(rows)} recorder-days, {sum(x['triples'] for x in rows):,} triples. Per day: the observation timeline (date), the event-centric graph (events chained by hasPreviousEvent → states → observations), and the temporal state graph. Home and room are inferred (see report.md).</p>
<table><tr><th>home</th><th>recorder</th><th>room (guess)</th><th>date</th><th>hours</th><th>observations</th><th>labelled %</th><th>triples</th><th>event graph</th><th>temporal graph</th></tr>{tr}</table></body></html>""")
    print(f"{len(rows)} pages + {out}")


if __name__ == "__main__":
    main(*sys.argv[1:4])
