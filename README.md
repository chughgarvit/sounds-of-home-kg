# sounds-of-home-kg

**The Sounds of Home as a temporal knowledge graph.** 1,342 hours of real, speech-removed home audio from
7 homes (14 microphones, 7 days each) turned into three linked graph layers, built from the dataset's public
labels package with one command, no audio download needed.

```
observation graph  ─ SAREF, one observation per 10 s window: microphone, sound class, time, confidence
       │                (same shape as the DAHCC Homelab graph; 98 recorder-days, 3.48 M triples)
temporal graph     ─ SoundEvents → States on appliances (opened by evidence, closed by its absence) → ActivityBlocks (episodes)
       │                (NetworkX, built online one record at a time; Contract 2 query API)
event graph        ─ Event —hasPreviousEvent→ Event; Event —has<Appliance>State→ State —hasObs→ Observation —hasSensor/hasValue/hasClip→
                        (the DAHCC event-graph shape; N-Triples per day + an expandable node-link page)
```

Every day gets three pages from `data/real/kg/index.html`: the observation timeline, the event graph and the
temporal state graph. `docs/KG.md` has the schema, statistics, SPARQL examples and the DAHCC comparison.
`graph/SCHEMA.md` is the temporal graph's schema (v2). `data/real/report.md` and `data/real/recorders.json`
are the build's report and the inferred recorder → home/room map.

## Quick start

```
python3 -m venv .venv && . .venv/bin/activate && pip install -r requirements.txt
scripts/build_all.sh                      # downloads the 1.05 GB labels package + SINS metadata, runs the tests, builds everything (~5 min)
open data/real/kg/index.html
python scripts/kg_query.py data/real/kg/captions_10_20231122.nt.gz       # the project's questions in SPARQL
python scripts/event_graph_view.py data/real/captions_10_20231122.json data/real/recorders.json ev.html ev.nt.gz
```

Tests only: `for t in scripts/test_*.py graph/test_api.py; do python3 $t; done`

## What is where

| path | what |
|---|---|
| `soh/taxonomy.py` | thresholds and AudioSet → activity/background maps (24 + 8 classes, plus the extended set); generated from the reviewed corpus notebook, drift-tested |
| `soh/panns.py` | PANNs frame JSON → privacy mask → 10 s segment labels (alias aggregation before scoring) |
| `soh/homes.py` | recorder → home pairing by speech co-occurrence; kitchen vs living room by kitchen-class share |
| `scripts/panns_to_captions.py` | labels package → caption records per recorder-day (gapless), `segments_all.csv`, `report.md`, `recorders.json` |
| `scripts/captions_to_nt.py` | caption records → SAREF observation graph |
| `scripts/panns_frames_to_nt.py` | one hour of raw frames → frame-level observation graph |
| `scripts/sins_to_nt.py` | SINS human activity labels → the same observation shape (per-session relative clock) |
| `graph/build.py`, `graph/api.py` | the temporal event-state graph, built online; `upsert / query / history / provenance` |
| `graph/eventgraph.py`, `scripts/event_graph_view.py` | the event-centric graph and its page |
| `scripts/temporal_graph_view.py`, `scripts/kg_timeline.py`, `scripts/kg_index.py` | the other two pages and the index |
| `scripts/kg_query.py` | six questions in SPARQL over a day graph |
| `scripts/test_*.py`, `graph/test_api.py` | twelve checks; `build_all.sh` runs them first |

## The caption record (the contract between perception and graph)

One JSON record per 10 s of audio: `t_start, t_end, description, activity, background, confidence, clip_file`.
Privacy-masked windows are records with `activity: null` and confidence 0; quiet windows carry a null
sentence; so the graph can tell *no evidence* from *evidence of nothing*. A perception model that emits this
record (the audio-language model track of the parent project) plugs in with zero changes here.

## Headline numbers (labels package, `extended` policy)

482,496 windows · 46.4 % privacy-masked · 37.0 % quiet · 7.0 % unidentified · 5.6 % activity-labelled (75 h)
· 24 activity classes · 98 day graphs, 3,477,842 triples, 14 MB. Recorder 10 on 2023-11-22 as an event graph:
67 events, 117 states, 493 observations, 3,002 triples. Full tables in `data/real/report.md` and `docs/KG.md`.

## Citation

Data: Bibbo, Deacon, Singh, Plumbley, *The Sounds of Home: A Speech-Removed Residential Audio Dataset for Sound
Event Detection*, 2024 (arXiv:2409.11262), CC BY 4.0. SINS: Dekkers et al., DCASE 2018 Task 5.
Code: MIT, Garvit Chugh, IIT Jodhpur, 2026.
