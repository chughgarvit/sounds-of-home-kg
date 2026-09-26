"""Regenerate soh/taxonomy.py from the reviewed notebook. Usage: python scripts/gen_taxonomy.py [notebook.ipynb]"""
import json, pprint, sys
from pathlib import Path

NB = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1] / 'notebook' / 'soundsofhome_to_echollm_reviewed.ipynb'
OUT = Path(__file__).resolve().parents[1] / 'soh' / 'taxonomy.py'
STAGE0_HEAD, STAGE4_HEAD = '# CONFIG - edit the paths', 'TAXONOMY_POLICY = "strict"'
CONSTS = ['PRIVACY_LABELS', 'PRIVACY_THR', 'PRIVACY_PAD_SEC', 'MAX_MASKED_FRAC', 'FRAME_THR', 'ACT_MIN_PEAK', 'ACT_MIN_COVERAGE',
          'BG_MIN_PEAK', 'BG_MIN_COVERAGE', 'SILENCE_LABELS', 'SILENCE_COVERAGE', 'SEG_SEC', 'SEG_HOP_SEC', 'NULL_SENTENCE']
MAPS = ['ACTIVITY_MAP', 'BACKGROUND_MAP', 'NEW_ACTIVITIES', 'IGNORE', 'UNLEARNABLE_HERE']


def notebook_namespace(nb_path=NB):
    """Execute the notebook's Stage 0 and Stage 4 cells with their file-system side effects removed."""
    cells = [''.join(c['source']) for c in json.load(open(nb_path))['cells'] if c['cell_type'] == 'code']
    s0 = next(c for c in cells if STAGE0_HEAD in c).replace('d.mkdir(parents=True, exist_ok=True)', 'pass')
    s4 = next(c for c in cells if STAGE4_HEAD in c).replace('with open(META_DIR / "taxonomy_map.json", "w") as f:', 'if False:')
    ns = {'json': json}
    exec('from pathlib import Path\nimport builtins\nprint = lambda *a, **k: None\n' + s0, ns)
    exec('print = lambda *a, **k: None\n' + s4, ns)
    return ns


def render(ns):
    lines = ['"""Taxonomy and thresholds, GENERATED from soundsofhome_to_echollm_reviewed.ipynb (Stage 0 + Stage 4).',
             'Do not edit: regenerate with `python scripts/gen_taxonomy.py`; scripts/test_taxonomy.py fails if this drifts."""', '']
    lines += [f"{n} = {pprint.pformat(ns[n], width=100)}" for n in CONSTS]
    lines += [f"\n{n} = {pprint.pformat(ns[n], width=100, sort_dicts=False)}" for n in MAPS]
    lines.append('''

def activity_map(policy: str) -> dict:
    """'strict' = EchoScriptor's 24 classes only; 'extended' adds NEW_ACTIVITIES (TV, doors, drawers, cutlery...)."""
    if policy not in ("strict", "extended"):
        raise ValueError(f"policy must be strict|extended, got {policy!r}")
    return {**ACTIVITY_MAP, **NEW_ACTIVITIES} if policy == "extended" else dict(ACTIVITY_MAP)
''')
    return '\n'.join(lines) + '\n'


if __name__ == '__main__':
    if not NB.exists():
        sys.exit(f'notebook not found at {NB}; soh/taxonomy.py is the committed, generated copy')
    OUT.write_text(render(notebook_namespace()))
    print('wrote', OUT)
