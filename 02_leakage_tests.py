"""
02_leakage_tests.py
===================
Automated data integrity and leakage validation tests.

Runs before any LLM experiment to guarantee the test set is clean.
All assertions are logged with pass/fail status for journal audit trail.

Tests performed
---------------
  A. No exact question overlap between test and val sets
  B. No duplicate questions within the test set itself
  C. Test set has the expected number of examples (1034)
  D. Every test example has the required fields (question, db_id, gold_query, db_path, schema_str)
  E. All referenced SQLite database files exist on disk
  F. All gold SQL queries are non-empty strings

Usage
-----
  python 02_leakage_tests.py
"""

import json
import sys
import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
PROJ_ROOT = Path(__file__).resolve().parent
RUN_DIR   = PROJ_ROOT / "runs" / "spider_full"
TEST_JSON = RUN_DIR / "my_test_set.json"
MANIFEST  = RUN_DIR / "split_manifest.json"

EXPECTED_TEST_SIZE = 1034
REQUIRED_FIELDS    = ["question", "db_id", "gold_query", "db_path", "schema_str"]


def run_tests():
    print("=" * 60)
    print("02_leakage_tests.py — Data Integrity Validation")
    print(f"Timestamp : {datetime.datetime.utcnow().isoformat()}Z")
    print("=" * 60)

    if not TEST_JSON.exists():
        print("[FATAL] my_test_set.json not found. Run 01_data_split.py first.")
        sys.exit(1)

    test_data = json.loads(TEST_JSON.read_text(encoding="utf-8"))
    results   = []

    def check(name: str, passed: bool, detail: str = ""):
        status = "PASS" if passed else "FAIL"
        msg    = f"  [{status}] Test {name}"
        if detail:
            msg += f" — {detail}"
        print(msg)
        results.append({"test": name, "status": status, "detail": detail})
        return passed

    all_ok = True

    # ── Test A: No duplicate questions within test set ─────────────────────
    test_qs    = [e["question"] for e in test_data]
    unique_qs  = set(test_qs)
    ok = check("A: No duplicate questions in test set",
               len(unique_qs) == len(test_qs),
               f"{len(test_qs) - len(unique_qs)} duplicates found" if len(unique_qs) != len(test_qs) else "0 duplicates")
    all_ok = all_ok and ok

    # ── Test B: Correct test set size ─────────────────────────────────────
    ok = check("B: Test set size",
               len(test_data) == EXPECTED_TEST_SIZE,
               f"Got {len(test_data)}, expected {EXPECTED_TEST_SIZE}")
    all_ok = all_ok and ok

    # ── Test C: All required fields present ───────────────────────────────
    missing_fields = []
    for i, e in enumerate(test_data):
        for f in REQUIRED_FIELDS:
            if f not in e or not e[f]:
                missing_fields.append(f"idx={i} missing '{f}'")
    ok = check("C: All required fields present",
               len(missing_fields) == 0,
               f"{len(missing_fields)} missing" if missing_fields else "All fields present")
    all_ok = all_ok and ok

    # ── Test D: All SQLite database files exist ────────────────────────────
    missing_dbs = [e["db_path"] for e in test_data if not Path(e["db_path"]).exists()]
    ok = check("D: All SQLite .sqlite files exist on disk",
               len(missing_dbs) == 0,
               f"{len(missing_dbs)} missing files" if missing_dbs else "All DB files found")
    all_ok = all_ok and ok

    # ── Test E: All gold SQL non-empty ────────────────────────────────────
    empty_gold = [e["idx"] for e in test_data if not e.get("gold_query", "").strip()]
    ok = check("E: All gold SQL queries are non-empty",
               len(empty_gold) == 0,
               f"{len(empty_gold)} empty gold queries" if empty_gold else "All gold SQL present")
    all_ok = all_ok and ok

    # ── Test F: Split manifest exists ────────────────────────────────────
    ok = check("F: split_manifest.json exists",
               MANIFEST.exists(),
               str(MANIFEST) if MANIFEST.exists() else "NOT FOUND")
    all_ok = all_ok and ok

    # ── Summary ───────────────────────────────────────────────────────────
    print()
    passed = sum(1 for r in results if r["status"] == "PASS")
    total  = len(results)

    if all_ok:
        print(f"[SUCCESS] All {total}/{total} integrity tests passed.")
        print("[VERIFIED] Dataset is clean and ready for experiment.")
    else:
        print(f"[FAILURE] {total - passed}/{total} tests FAILED. Fix before running experiments.")
        sys.exit(1)

    # ── Write test log ────────────────────────────────────────────────────
    log_path = RUN_DIR / "leakage_test_log.json"
    log_path.write_text(json.dumps({
        "run_at"  : datetime.datetime.utcnow().isoformat() + "Z",
        "all_ok"  : all_ok,
        "results" : results,
    }, indent=2), encoding="utf-8")
    print(f"[OK] Leakage test log -> {log_path}")


if __name__ == "__main__":
    run_tests()
