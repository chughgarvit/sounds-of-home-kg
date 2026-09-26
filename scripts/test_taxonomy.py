"""Drift check: soh/taxonomy.py must equal what the reviewed notebook defines. python scripts/test_taxonomy.py"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1])); sys.path.insert(0, str(Path(__file__).resolve().parent))
from gen_taxonomy import notebook_namespace, CONSTS, MAPS, NB  # noqa: E402
from soh import taxonomy  # noqa: E402

if not NB.exists():
    print('ok (drift check skipped: reviewed notebook not present in this repo)'); sys.exit(0)
ns = notebook_namespace()
for name in CONSTS + MAPS:
    assert getattr(taxonomy, name) == ns[name], f"{name} drifted from the notebook - run scripts/gen_taxonomy.py"
assert "People Talking" not in taxonomy.activity_map("extended").values(), "speech is removed from this dataset; never map it"
assert set(taxonomy.activity_map("strict")) <= set(taxonomy.activity_map("extended"))
print("ok")
