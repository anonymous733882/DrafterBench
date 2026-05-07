import json
try:
    import lmdb
except ImportError:
    lmdb = None
import pickle
from pathlib import Path

task_sets = [
    "add_table",
    "revise_table",
    "map_table",
    "refresh_table",
    "add_text",
    "revise_text",
    "map_text",
    "refresh_text",
    "add_vector",
    "delete_vector",
    "map_vector",
    "refresh_vector",
]

MODULE_DIR = Path(__file__).resolve().parent
LMDB_PATH = MODULE_DIR / "task_component.lmdb"


def build_task_component_lmdb(output_path=LMDB_PATH):
    if lmdb is None:
        raise ImportError("lmdb is required to build task_component.lmdb")
    env = lmdb.open(str(output_path))
    txn = env.begin(write=True)

    for task in task_sets:
        with open(MODULE_DIR / f"{task}_elements.json", "r", encoding="utf-8") as f:
            data = json.load(f)
            txn.put(
                task.encode("ascii"),
                pickle.dumps(data, protocol=pickle.HIGHEST_PROTOCOL),
            )

    txn.commit()
    env.sync()
    env.close()
    return output_path
