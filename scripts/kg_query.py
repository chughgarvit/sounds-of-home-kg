"""Ask the observation graph the project's questions in SPARQL. python scripts/kg_query.py data/real/kg/captions_14_20231122.nt.gz [--q NAME]
Shows that a DAHCC-shaped audio graph already answers detection / temporal / counting questions with plain SPARQL;
state and absence questions need the reasoning layer on top (graph/, qa/)."""
import argparse, gzip, sys, time
import rdflib

P = "https://home-audio-kg-bench.org/soh/property/"
QUERIES = {
    "classes":   ("What did the microphone hear today, and how often (confidence > 0.5)?",
                  f"SELECT ?cls (COUNT(?o) AS ?n) WHERE {{ ?o saref:relatesToProperty ?p ; saref:hasValue ?v . FILTER(?v > 0.5) BIND(REPLACE(STR(?p), '{P}', '') AS ?cls) }} GROUP BY ?cls ORDER BY DESC(?n)"),
    "tap_when":  ("When did water run in the sink? (first/last window, count)",
                  f"SELECT (MIN(?t) AS ?first) (MAX(?t) AS ?last) (COUNT(?o) AS ?windows) WHERE {{ ?o saref:relatesToProperty <{P}activity/Running_Water_in_Sink> ; saref:hasTimestamp ?t }}"),
    "door_evening": ("Was there a door after 18:00? (detection with a time window)",
                  f"SELECT ?t ?v ?label WHERE {{ ?o saref:relatesToProperty <{P}activity/Opening_or_Closing_a_Door> ; saref:hasTimestamp ?t ; saref:hasValue ?v ; rdfs:label ?label . FILTER(HOURS(?t) >= 18) }} ORDER BY ?t LIMIT 10"),
    "masked":    ("How much of the day is privacy-masked (no evidence at all)?",
                  f"SELECT (COUNT(?o) AS ?masked) WHERE {{ ?o rdfs:label 'Audio unavailable (privacy-masked).' }}"),
    "evidence":  ("Provenance: which clips back the first three tap observations?",
                  f"SELECT ?t ?clip WHERE {{ ?o saref:relatesToProperty <{P}activity/Running_Water_in_Sink> ; saref:hasTimestamp ?t ; prov:wasDerivedFrom ?clip }} ORDER BY ?t LIMIT 3"),
    "unanswerable": ("Where did I last use my keys? (no such property: the correct answer is 'no evidence')",
                  f"SELECT (COUNT(?o) AS ?n) WHERE {{ ?o saref:relatesToProperty <{P}activity/Keys> }}"),
}
PREFIX = "PREFIX saref: <https://saref.etsi.org/core/> PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> PREFIX prov: <http://www.w3.org/ns/prov#>\n"


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("kg"); ap.add_argument("--q", choices=list(QUERIES), help="run one query only")
    a = ap.parse_args()
    t0 = time.time(); g = rdflib.Graph().parse(data=gzip.open(a.kg, "rt").read(), format="nt")
    print(f"{len(g):,} triples loaded in {time.time() - t0:.1f}s from {a.kg}\n")
    for name, (question, sparql) in QUERIES.items():
        if a.q and name != a.q:
            continue
        t0 = time.time(); rows = list(g.query(PREFIX + sparql))
        print(f"## {name}: {question}   [{1000 * (time.time() - t0):.0f} ms]")
        for r in rows[:15]:
            print("  ", " | ".join(str(x).replace(P, "") for x in r))
        print()


if __name__ == "__main__":
    main()
