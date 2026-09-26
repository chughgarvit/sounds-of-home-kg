"""The one runnable check for captions_to_nt.py:  python scripts/test_captions_to_nt.py"""
import gzip, sys, tempfile
from datetime import datetime
from pathlib import Path
import rdflib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from captions_to_nt import triples  # noqa: E402

recs = [
    {"t_start": 50520.0, "t_end": 50530.0, "description": 'The user runs water "loudly".', "activity": "Running Water in Sink",
     "background": "Fridge Humming", "confidence": 0.8, "clip_file": "a.wav"},
    {"t_start": 50530.0, "t_end": 50540.0, "description": "The house is quiet.", "activity": None,
     "background": None, "confidence": 0.7, "clip_file": "b.wav"},
]
nt = "\n".join(triples(recs, "https://x.org/soh", "14", datetime(2023, 11, 22)))
g = rdflib.Graph().parse(data=nt, format="nt")
assert len(g) == 5 + 2 + 5 + 5 + 2, len(g)          # activity(+label,+clip) + background + null(+label,+clip)
hits = list(g.query("""
  PREFIX saref: <https://saref.etsi.org/core/>
  SELECT ?t ?v WHERE { ?o saref:relatesToProperty <https://x.org/soh/property/activity/Running_Water_in_Sink> ;
                          saref:hasTimestamp ?t ; saref:hasValue ?v . FILTER(?v > 0.6) }"""))
assert len(hits) == 1 and str(hits[0][0]) == "2023-11-22T14:02:00" and float(hits[0][1]) == 0.8, hits
assert any(str(o) == 'The user runs water "loudly".' for o in g.objects(predicate=rdflib.RDFS.label)), "label escaping"
mics = set(g.objects(predicate=rdflib.URIRef("https://saref.etsi.org/core/measurementMadeBy")))
assert mics == {rdflib.URIRef("https://x.org/soh/mic/14")}
print("ok")
