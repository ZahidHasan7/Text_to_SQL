"""
04_evaluation.py
================
Execution Accuracy evaluator for Spider Text-to-SQL experiments.

For each prediction file, this script:
  1. Executes predicted SQL against the real SQLite database
  2. Executes gold SQL against the same database
  3. Compares result sets (order-insensitive, value-normalised)
  4. Computes Execution Accuracy (EX) = correct / total
  5. Writes a per-item CSV report and a cross-model summary CSV
  6. Writes a JSON experiment log for full journal audit trail

Evaluation Protocol (as reported in the paper)
-----------------------------------------------
  - Metric       : Execution Accuracy (EX)
  - Comparison   : Order-insensitive set equality of result rows
  - Normalization: Strings lowercased, whitespace stripped;
                   numeric values kept as-is (float string preserved)
  - Denominator  : Always = total test set size (failed predictions
                   counted as incorrect, not excluded)
  - Timeout      : Per-query SQLite execution timeout = 10 s

Usage
-----
  python 04_evaluation.py
"""

import sqlite3
import json
import csv
import datetime
import os
import sys
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
PROJ_ROOT = Path(__file__).resolve().parent
RUN_DIR   = PROJ_ROOT / "runs" / "spider_full"
TEST_JSON = RUN_DIR / "my_test_set.json"

# ── Prediction files to evaluate ─────────────────────────────────────────────
# Add or remove filenames here. Missing files are skipped with a warning.
MODEL_ID = (
    os.getenv("GEMINI_MODEL")
    or os.getenv("OPENROUTER_MODEL")
    or "models/gemini-3.6-flash"
).strip()
MODEL_FILE_STEM = MODEL_ID.replace("/", "_").replace(":", "_").replace(" ", "_")
PRED_FILES = [
    RUN_DIR / f"predicted_scot_models_{MODEL_FILE_STEM}.sql",
    RUN_DIR / f"predicted_cot_models_{MODEL_FILE_STEM}.sql",
    RUN_DIR / "predicted_standard.sql",
    RUN_DIR / "predicted_qdecomp.sql",
    RUN_DIR / "predicted_qd_intercol.sql",
]

QUERY_TIMEOUT_SEC = 10   # SQLite per-query execution timeout


# ── Value normalisation ───────────────────────────────────────────────────────
def norm_cell(x) -> str:
    """Normalise a single cell value for comparison."""
    try:
        if x is None:
            return ""
        s = str(x).strip()
        try:
            float(s)          # keep numeric strings as-is
            return s
        except ValueError:
            return s.lower()  # lowercase text for case-insensitive match
    except Exception:
        return str(x)


# ── SQL Executor ──────────────────────────────────────────────────────────────
def run_query(db_path: str, sql: str) -> tuple[bool, object]:
    """
    Execute sql against the SQLite database at db_path.
    Returns (success: bool, result_rows_or_error_string).
    Result rows are normalised and sorted for order-insensitive comparison.
    """
    try:
        con = sqlite3.connect(db_path, timeout=QUERY_TIMEOUT_SEC)
        cur = con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close()
        con.close()
        norm = [tuple(norm_cell(c) for c in r) for r in rows]
        norm.sort()
        return True, norm
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


# ── Per-file evaluator ────────────────────────────────────────────────────────
def eval_one(pred_file: Path, test_data: list) -> dict:
    """
    Evaluate a single prediction file against the test set.
    Returns a result dict suitable for the summary CSV and JSON log.
    """
    print(f"\n{'='*60}")
    print(f"Evaluating : {pred_file.name}")
    print(f"{'='*60}")

    preds_raw = pred_file.read_text(encoding="utf-8").splitlines()
    preds     = [ln.strip() for ln in preds_raw]

    total = len(test_data)

    # Denominator is always the full test set size — no exclusions allowed.
    if len(preds) != total:
        print(f"[WARN] Pred count ({len(preds)}) != test size ({total}). "
              f"Padding/truncating to align.")
        # Pad with SELECT 1; if fewer predictions than items
        while len(preds) < total:
            preds.append("SELECT 1;")
        preds = preds[:total]

    correct      = 0
    api_failures = 0   # predictions that are "SELECT 1;" (LLM failure fallback)
    exec_errors  = 0   # predictions that failed SQLite execution
    rows_out     = []

    for i, (ex, pred_sql) in enumerate(zip(test_data, preds), 1):
        db      = ex["db_path"]
        gold_sql = ex["gold_query"].strip().rstrip(";") + ";"
        pred_sql = pred_sql.strip().rstrip(";") + ";"

        is_api_failure = pred_sql.strip().lower() in ("select 1;", "")
        if is_api_failure:
            api_failures += 1

        ok_g, gold_res = run_query(db, gold_sql)
        ok_p, pred_res = run_query(db, pred_sql)

        if not ok_p:
            exec_errors += 1

        match = ok_g and ok_p and (gold_res == pred_res)
        if match:
            correct += 1

        rows_out.append({
            "idx"             : ex.get("idx", i - 1),
            "db_id"           : ex["db_id"],
            "question"        : ex["question"],
            "match"           : match,
            "pred_exec_ok"    : ok_p,
            "gold_exec_ok"    : ok_g,
            "is_api_failure"  : is_api_failure,
            "pred_sql"        : pred_sql,
            "gold_sql"        : gold_sql,
            "pred_result"     : str(pred_res)[:500],  # truncate long results
            "gold_result"     : str(gold_res)[:500],
        })

        if i % 50 == 0:
            running_acc = correct / i * 100
            print(f"  Progress: {i}/{total}  |  Running EX: {running_acc:.1f}%")

    acc = correct / total * 100.0

    print(f"\n  Final Execution Accuracy : {correct}/{total} = {acc:.2f}%")
    print(f"  API failures (SELECT 1;) : {api_failures}")
    print(f"  SQLite exec errors       : {exec_errors}")

    # ── Per-item CSV ──────────────────────────────────────────────────────────
    out_csv = RUN_DIR / f"eval_report__{pred_file.stem}.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)
    print(f"  Per-item report -> {out_csv}")

    return {
        "pred_file"        : pred_file.name,
        "evaluated_at"     : datetime.datetime.utcnow().isoformat() + "Z",
        "total"            : total,
        "correct"          : correct,
        "exec_acc_pct"     : round(acc, 4),
        "api_failures"     : api_failures,
        "exec_errors"      : exec_errors,
        "per_item_csv"     : str(out_csv),
    }


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("04_evaluation.py — Execution Accuracy Evaluation")
    print(f"Timestamp : {datetime.datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    if not TEST_JSON.exists():
        print(f"[FATAL] Test set not found: {TEST_JSON}")
        print("  Run 01_data_split.py first.")
        sys.exit(1)

    test_data = json.loads(TEST_JSON.read_text(encoding="utf-8"))
    print(f"[i] Loaded {len(test_data)} test examples")

    summary = []
    for pf in PRED_FILES:
        if not pf.exists():
            print(f"\n[SKIP] {pf.name} not found.")
            continue
        result = eval_one(pf, test_data)
        summary.append(result)

    if not summary:
        print("\n[WARN] No prediction files found. Nothing to evaluate.")
        return

    # ── Summary CSV ───────────────────────────────────────────────────────────
    sum_csv = RUN_DIR / "eval_summary.csv"
    csv_fields = ["pred_file", "total", "correct", "exec_acc_pct",
                  "api_failures", "exec_errors", "evaluated_at"]
    with sum_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=csv_fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(summary)

    # ── Experiment log JSON (full audit trail for journal) ────────────────────
    experiment_log = {
        "experiment"        : "Spider Text-to-SQL Evaluation",
        "evaluation_metric" : "Execution Accuracy (EX)",
        "protocol" : {
            "order_sensitive"    : False,
            "value_normalisation": "lowercase text, preserve numerics",
            "denominator"        : "full test set (failures counted as incorrect)",
            "sqlite_timeout_sec" : QUERY_TIMEOUT_SEC,
        },
        "dataset" : {
            "name"    : "Spider Dev",
            "total"   : len(test_data),
            "source"  : str(TEST_JSON),
        },
        "run_at"  : datetime.datetime.utcnow().isoformat() + "Z",
        "results" : summary,
    }
    log_path = RUN_DIR / "experiment_log.json"
    log_path.write_text(json.dumps(experiment_log, indent=2), encoding="utf-8")

    # ── Print final table ─────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    print("FINAL RESULTS SUMMARY")
    print(f"{'='*60}")
    print(f"{'Method':<45} {'EX (%)':>8} {'Correct':>9} {'Total':>7}")
    print("-" * 60)
    for r in summary:
        name = r["pred_file"].replace("predicted_", "").replace(".sql", "")
        print(f"  {name:<43} {r['exec_acc_pct']:>8.2f} {r['correct']:>9} {r['total']:>7}")
    print("=" * 60)
    print(f"\n[OK] Summary CSV      -> {sum_csv}")
    print(f"[OK] Experiment log   -> {log_path}")
    print("\n[DONE] Evaluation complete.")


if __name__ == "__main__":
    main()
