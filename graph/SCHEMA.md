# Graph schema v2 (implemented in `graph/build.py`; extend only with sign-off)

The graph is a `networkx.MultiDiGraph`. Two kinds of nodes: **entity nodes** (one per
thing/type, no timestamps) and **instance nodes** (one per occurrence, timestamped).
Nothing is ever deleted or overwritten — history *is* the product.

## Node types

| Type | One per… | id example | attributes |
|---|---|---|---|
| `Appliance` | appliance/object type | `washing_machine` | `label` |
| `ActivityType` | activity category | `act:Running Water in Sink` | `label` |
| `SoundEvent` | caption record (instance) | `ev:43200` | `t_start, t_end, description, confidence, clip_file` |
| `State` | continuous state interval (instance) | `st:washing_machine:41000` | `state` ("running"), `t_start`, `t_end` (`None` while open), `confidence`, `status` (tentative/confirmed), `n_evidence`, `closed_by` (silence / masked / end_of_audio / open_at_end_of_audio), `masked_inside` |
| `ActivityBlock` | episode: consecutive events of one activity (gap ≤ 5 min) | `blk:Running Water in Sink:50520` | `activity`, `t_start`, `t_end`, `n_events`, `confidence` |
| `Room` | the room the microphone is in (from the recorder → room map) | `room:kitchen` | `label` |

`Room` comes free from which microphone recorded the day (`data/real/recorders.json`).

## Edge types

| Edge | From → To | Meaning |
|---|---|---|
| `instance_of` | SoundEvent → ActivityType | this 10s clip was this kind of activity |
| `state_of` | State → Appliance | this interval describes this appliance |
| `evidenced_by` | State → SoundEvent | provenance: the records this state was inferred from |
| `member_of` | SoundEvent → ActivityBlock | this event belongs to this episode |
| `located_in` | Appliance → Room | where the appliance's sounds were recorded |

Temporal order ("what came before X") is **derived from timestamps at query time**, not
stored as edges — storing `before` edges for 5,400 events/day would be noise.

## Attributes rules

- Every instance node carries `confidence` in [0,1]. A State's confidence = mean of its
  evidence records' confidences.
- Every State must have ≥1 `evidenced_by` edge. No orphan inferences, ever — an answer
  we can't trace to a clip is an answer we can't defend.
- `t_end=None` means "still open as far as the audio shows" — that's information, not
  a bug (it's how "did I turn it off?" gets answered).

## Worked example

Five records: tap runs 14:02:00–14:02:30 (3 records, confidences .8/.7/.9), then two
quiet records. The graph after ingestion:

```mermaid
graph LR
    E1["SoundEvent ev:50520<br/>14:02:00-10 · conf .8"] -->|instance_of| A["ActivityType<br/>Running Water in Sink"]
    E2["SoundEvent ev:50530<br/>14:02:10-20 · conf .7"] -->|instance_of| A
    E3["SoundEvent ev:50540<br/>14:02:20-30 · conf .9"] -->|instance_of| A
    S["State st:tap:50520<br/>running 14:02:00 → 14:02:30<br/>conf .8"] -->|state_of| T["Appliance tap"]
    S -->|evidenced_by| E1
    S -->|evidenced_by| E2
    S -->|evidenced_by| E3
```

The two quiet records close the interval (see METHODS.md, M1): `t_end = 14:02:30`.
Query `history("tap")` → `[{state: running, 14:02:00–14:02:30, conf 0.8, evidence: 3 clips}]`.
Question *"Did I turn the tap off?"* → the interval is **closed** → *"Yes — the water
sound stopped at 14:02:30 (confidence 0.8, 3 clips)."* If the quiet records were missing,
the interval would be open → *"I last heard it running at 14:02:30 and no stop since —
it may still be on."*

## Appliance vs. Activity — the mapping

Some activities imply an appliance state (`Running Water in Sink` → tap running,
`Washing Machine` → washing_machine running); some don't (`Chopping Board` is an
activity only). Keep a small dict `ACTIVITY_TO_APPLIANCE` in `graph/build.py` — that
dict is the only place this knowledge lives.


## v2 additions and the online rule (2026-09-26)

States are managed like tracks (perceptual anchoring, M-of-N track management): the first evidence window
opens a *tentative* State (confidence discounted ×0.5); the second confirms it; up to 2 consecutive audible
windows without the sound are tolerated (20 s); privacy-masked windows are neither evidence nor
counter-evidence and up to 30 of them (5 min) are tolerated inside a State, counted in `masked_inside`;
after that the State closes with `closed_by` recording why. A State still fed when the audio ends keeps
`t_end = None`. Every record is ingested online through `upsert`, so the same code runs live.
ActivityBlocks consolidate consecutive events of one activity with gaps up to 5 min. See
`scripts/temporal_graph_view.py` for the picture and `graph/test_api.py` for the ten checks.
