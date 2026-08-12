"""
01_data_split.py
================
Prepares the Spider dev set for evaluation.

Dataset   : Spider (Benchmark for Cross-Domain Text-to-SQL)
Source    : https://yale-seas.github.io/spider/
Dev file  : data/spider/dev.json  (1034 examples across 20 domains)
Gold SQL  : data/spider/dev_gold.sql

Outputs (in runs/spider_full/)
-------------------------------
  my_test_set.json   - All 1034 evaluation examples with schema + gold SQL
  my_val_set.json    - Prompt few-shot pool (currently empty; same DB space used)
  my_gold_set.sql    - Gold SQL lines, one per row (aligned with my_test_set.json)
  my_gold_set.json   - Gold SQL + db_id pairs for cross-checking
  split_manifest.json - Full audit trail: seed, counts, db distribution

Reproducibility
---------------
  random.seed(RANDOM_SEED) is used throughout. The seed and all counts are
  written to split_manifest.json so reviewers can verify the exact split.

Usage
-----
  python 01_data_split.py
"""

import json
import random
import sys
import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJ_ROOT      = Path(__file__).resolve().parent
SPIDER_DIR     = PROJ_ROOT / "data" / "spider"
OUT_DIR        = PROJ_ROOT / "runs" / "spider_full"

DEV_JSON_PATH  = SPIDER_DIR / "dev.json"
TABLES_JSON    = SPIDER_DIR / "tables.json"
GOLD_SQL_PATH  = SPIDER_DIR / "dev_gold.sql"

# ── Configuration ─────────────────────────────────────────────────────────────
# Use all 1034 examples from Spider dev set.
# Per the experimental design in the journal paper, the full dev set is used
# for evaluation. Few-shot examples in the SCoT prompt use different database
# instances than those in the test set at the query level.
NUM_SAMPLES   = 1034   # Full Spider dev set
RANDOM_SEED   = 42     # Fixed seed for reproducibility (reported in paper)

# ── Schema formatter ──────────────────────────────────────────────────────────
def format_schema(schema_info: dict) -> str:
    """
    Converts a Spider tables.json entry into the API-Docs schema format used
    in all prompts throughout this study.

    Format:
        ### SQLite SQL tables, with their properties:
        # table_name (col1, col2, ...)
        # FK: table_a.col -> table_b.col
    """
    lines = ["### SQLite SQL tables, with their properties:", "#"]
    table_names = schema_info["table_names_original"]
    col_pairs   = schema_info["column_names_original"]

    table_cols: dict[int, list] = {i: [] for i in range(len(table_names))}
    for t_idx, c_name in col_pairs:
        if t_idx == -1 or c_name == "*":
            continue
        table_cols[t_idx].append(c_name)

    for i, tname in enumerate(table_names):
        cols = ", ".join(table_cols.get(i, []))
        lines.append(f"# {tname} ({cols})")

    for (from_id, to_id) in schema_info.get("foreign_keys", []):
        ft, fc = col_pairs[from_id]
        tt, tc = col_pairs[to_id]
        if ft != -1 and tt != -1 and fc != "*" and tc != "*":
            lines.append(f"# FK: {table_names[ft]}.{fc} -> {table_names[tt]}.{tc}")

    return "\n".join(lines) + "\n"


def find_db_root(spider_dir: Path) -> Path:
    for cand in ["database", "databases"]:
        p = spider_dir / cand
        if p.is_dir():
            return p
    raise FileNotFoundError(f"Spider database directory not found inside {spider_dir}")


def main():
    print("=" * 60)
    print("01_data_split.py — Spider Full Dev Set Preparation")
    print(f"Timestamp : {datetime.datetime.utcnow().isoformat()}Z")
    print(f"Seed      : {RANDOM_SEED}")
    print(f"Target N  : {NUM_SAMPLES}")
    print("=" * 60)

    # ── Load raw files ────────────────────────────────────────────────────────
    for p in [DEV_JSON_PATH, TABLES_JSON, GOLD_SQL_PATH]:
        if not p.exists():
            print(f"[ERR] Missing required file: {p}")
            sys.exit(1)

    dev_data   = json.loads(DEV_JSON_PATH.read_text(encoding="utf-8"))
    tables_all = json.loads(TABLES_JSON.read_text(encoding="utf-8"))

    gold_sql_lines = []
    for ln in GOLD_SQL_PATH.read_text(encoding="utf-8").splitlines():
        ln = ln.strip()
        if "\t" in ln:
            ln = ln.split("\t", 1)[0].strip()
        gold_sql_lines.append(ln)

    schemas = {db["db_id"]: db for db in tables_all}
    db_root = find_db_root(SPIDER_DIR)

    print(f"[i] dev.json        : {len(dev_data)} examples")
    print(f"[i] tables.json     : {len(tables_all)} databases")
    print(f"[i] dev_gold.sql    : {len(gold_sql_lines)} gold SQL lines")

    # ── Build items ───────────────────────────────────────────────────────────
    all_items = []
    skipped   = 0
    for i, ex in enumerate(dev_data):
        db_id  = ex["db_id"]
        schema = schemas.get(db_id)
        if not schema:
            print(f"[WARN] No schema found for db_id={db_id}, skipping idx={i}")
            skipped += 1
            continue
        gold = gold_sql_lines[i] if i < len(gold_sql_lines) else ""
        db_path = str(db_root / db_id / f"{db_id}.sqlite")
        all_items.append({
            "idx"        : i,
            "db_id"      : db_id,
            "question"   : ex["question"],
            "schema_str" : format_schema(schema),
            "gold_query" : gold,
            "db_path"    : db_path,
        })

    print(f"[i] Usable items    : {len(all_items)} ({skipped} skipped — missing schema)")

    # ── Sample ────────────────────────────────────────────────────────────────
    random.seed(RANDOM_SEED)
    random.shuffle(all_items)
    test_sample = all_items[:NUM_SAMPLES]

    print(f"[i] Final test set  : {len(test_sample)} examples")

    # ── Database distribution log ─────────────────────────────────────────────
    db_counts: dict[str, int] = {}
    for e in test_sample:
        db_counts[e["db_id"]] = db_counts.get(e["db_id"], 0) + 1
    print(f"[i] Unique databases: {len(db_counts)}")

    # ── Write outputs ─────────────────────────────────────────────────────────
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    out_test   = OUT_DIR / "my_test_set.json"
    out_gold_sql  = OUT_DIR / "my_gold_set.sql"
    out_gold_json = OUT_DIR / "my_gold_set.json"
    out_manifest  = OUT_DIR / "split_manifest.json"

    out_test.write_text(
        json.dumps(test_sample, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    with out_gold_sql.open("w", encoding="utf-8") as f:
        for e in test_sample:
            f.write(e["gold_query"].strip() + "\n")

    out_gold_json.write_text(
        json.dumps(
            [{"idx": e["idx"], "db_id": e["db_id"], "query": e["gold_query"]}
             for e in test_sample],
            indent=2, ensure_ascii=False
        ), encoding="utf-8"
    )

    # ── Audit manifest (for journal reproducibility) ──────────────────────────
    manifest = {
        "created_at"         : datetime.datetime.utcnow().isoformat() + "Z",
        "source_file"        : str(DEV_JSON_PATH),
        "source_total"       : len(dev_data),
        "skipped_no_schema"  : skipped,
        "random_seed"        : RANDOM_SEED,
        "num_samples"        : NUM_SAMPLES,
        "actual_test_size"   : len(test_sample),
        "unique_databases"   : len(db_counts),
        "db_distribution"    : dict(sorted(db_counts.items())),
        "output_files"       : {
            "test_set"       : str(out_test),
            "gold_sql"       : str(out_gold_sql),
            "gold_json"      : str(out_gold_json),
            "manifest"       : str(out_manifest),
        }
    }
    out_manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"\n[OK] my_test_set.json   -> {out_test}")
    print(f"[OK] my_gold_set.sql    -> {out_gold_sql}")
    print(f"[OK] my_gold_set.json   -> {out_gold_json}")
    print(f"[OK] split_manifest.json-> {out_manifest}")
    print("\n[DONE] Data split complete. Ready for evaluation.")


if __name__ == "__main__":
    main()
