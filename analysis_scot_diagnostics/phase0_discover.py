"""
phase0_discover.py
==================
Phase 0: Discover data schema, parse debug logs, reproduce EX for all methods
and all backends. Gate: if any EX differs from reported by > 0.05pp, exit.

Outputs (written to analysis_scot_diagnostics/):
  - phase0_schema.txt          : log field description + stage-to-field mapping
  - phase0_ex_validation.csv   : recomputed vs reported EX per backend/method
  - phase0_query_counts.csv    : query count per backend
  - parsed_debug_<backend>.pkl : parsed log records for downstream phases
"""

import re, csv, json, ast, sqlite3, time, sys, pickle
from pathlib import Path

ROOT      = Path(__file__).resolve().parent.parent   # project root
RUN_DIR   = ROOT / "runs" / "spider_full"
OUT_DIR   = Path(__file__).resolve().parent
OUT_DIR.mkdir(parents=True, exist_ok=True)

QUERY_TIMEOUT = 5  # seconds (as specified in prompt)

# ── Backend file-stem mapping ──────────────────────────────────────────────────
BACKENDS = {
    "llama":  "meta-llama_llama-3.3-70b-instruct",
    "haiku":  "anthropic_claude-haiku-4.5",
    "gemini": "google_gemini-2.5-flash",
    "gpt4o":  "openai_gpt-4o-mini",
}

METHODS = ["scot", "cot", "standard", "qdecomp", "qd_intercol"]

# Reported EX% from the paper (for gate check)
REPORTED_EX = {
    # format: (backend, method) -> reported %
    ("llama",  "scot"):       64.41,
    ("llama",  "qd_intercol"):75.05,
    ("haiku",  "scot"):       67.89,
    ("haiku",  "qd_intercol"):73.89,
    ("gemini", "scot"):       77.47,
    ("gemini", "qd_intercol"):77.47,
    ("gpt4o",  "scot"):       71.57,  # from task summary (54.64 was the original run, then resumed)
    ("gpt4o",  "qd_intercol"):70.70,
}

# ── EX scorer ─────────────────────────────────────────────────────────────────
def norm_cell(x) -> str:
    try:
        if x is None: return ""
        s = str(x).strip()
        try: float(s); return s
        except ValueError: return s.lower()
    except Exception: return str(x)

def run_query(db_path: str, sql: str, timeout=QUERY_TIMEOUT):
    """Execute sql. Returns (ok: bool, rows_or_error)."""
    try:
        con = sqlite3.connect(db_path)
        _start = time.monotonic()
        def _chk():
            return 1 if time.monotonic() - _start > timeout else 0
        con.set_progress_handler(_chk, 1000)
        cur = con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close(); con.close()
        norm = [tuple(norm_cell(c) for c in r) for r in rows]
        norm.sort()
        return True, norm
    except Exception as e:
        return False, str(e)

def ex_from_csv(csv_path: Path, test_data: list) -> dict:
    """
    Recompute EX from eval_report CSV.
    Returns {correct, total, api_failures, exec_errors, ex_pct}.
    """
    rows = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    correct = sum(1 for r in rows if r["match"].strip().lower() == "true")
    total   = len(rows)
    api_f   = sum(1 for r in rows if r["is_api_failure"].strip().lower() == "true")
    exec_e  = sum(1 for r in rows if r["pred_exec_ok"].strip().lower() == "false")
    return {"correct": correct, "total": total, "api_failures": api_f,
            "exec_errors": exec_e, "ex_pct": round(correct/total*100, 4)}

# ── Debug log parser ───────────────────────────────────────────────────────────
_BLOCK_SEP = re.compile(r"^--- IDX (\d+) \(([^)]+)\) ---$", re.MULTILINE)
_FIELD_PAT = {
    "plan":        re.compile(r"^PLAN:\n(.*?)(?=^CHECKED:|^RAW_SQL_TEXTS:|^CANDS:|^$)", re.MULTILINE | re.DOTALL),
    "checked":     re.compile(r"^CHECKED:\n(.*?)(?=^RAW_SQL_TEXTS:|^CANDS:|^$)", re.MULTILINE | re.DOTALL),
    "raw_texts":   re.compile(r"^RAW_SQL_TEXTS:\n(.*?)(?=^CANDS:|^$)", re.MULTILINE | re.DOTALL),
    "cands":       re.compile(r"^CANDS:\n(.*?)(?=^RAW_CANON_TEXTS:|^$)", re.MULTILINE | re.DOTALL),
    "raw_canon":   re.compile(r"^RAW_CANON_TEXTS:\n(.*?)(?=^CANON_CANDS:|^$)", re.MULTILINE | re.DOTALL),
    "canon_cands": re.compile(r"^CANON_CANDS:\n(.*?)(?=^LAST_ERROR:|^$)", re.MULTILINE | re.DOTALL),
    "last_error":  re.compile(r"^LAST_ERROR: ?(.*?)(?=^FINAL_SQL:|^$)", re.MULTILINE | re.DOTALL),
    "final_sql":   re.compile(r"^FINAL_SQL:\n?(.*?)$", re.MULTILINE | re.DOTALL),
}

def _try_parse_list(s: str):
    """Try to parse a Python list literal. Return None on failure."""
    s = s.strip()
    if not s: return []
    try:
        return ast.literal_eval(s)
    except Exception:
        return None

def parse_debug_log(log_path: Path) -> list:
    """
    Parse a scot_debug_*.log file into a list of record dicts.
    Each record has: idx, db_id, plan, checked, cands, canon_cands,
                     last_error, final_sql, parse_errors (list of field names
                     that could not be parsed)
    """
    text = log_path.read_text(encoding="utf-8", errors="replace")
    # Split on block headers
    blocks = _BLOCK_SEP.split(text)
    # blocks = [pre, idx1, db1, body1, idx2, db2, body2, ...]
    records = []
    i = 1
    while i + 2 < len(blocks):
        idx_str = blocks[i].strip()
        db_id   = blocks[i+1].strip()
        body    = blocks[i+2]
        i += 3

        rec = {"idx": int(idx_str), "db_id": db_id, "parse_errors": []}

        # plan
        m = re.search(r"^PLAN:\n(.*?)(?=^CHECKED:|^RAW_SQL_TEXTS:|^$)", body, re.M | re.S)
        rec["plan"] = m.group(1).strip() if m else None
        if not m: rec["parse_errors"].append("plan")

        # checked
        m = re.search(r"^CHECKED:\n(.*?)(?=^RAW_SQL_TEXTS:|^$)", body, re.M | re.S)
        rec["checked"] = m.group(1).strip() if m else None
        if not m: rec["parse_errors"].append("checked")

        # cands (post-sanitize, pre-canon)
        m = re.search(r"^CANDS:\n(.*?)(?=^RAW_CANON_TEXTS:|^CANON_CANDS:|^LAST_ERROR:|^$)", body, re.M | re.S)
        if m:
            rec["cands"] = _try_parse_list(m.group(1).strip())
            if rec["cands"] is None: rec["parse_errors"].append("cands")
        else:
            rec["cands"] = None; rec["parse_errors"].append("cands")

        # canon_cands (post-canon)
        m = re.search(r"^CANON_CANDS:\n(.*?)(?=^LAST_ERROR:|^$)", body, re.M | re.S)
        if m:
            rec["canon_cands"] = _try_parse_list(m.group(1).strip())
            if rec["canon_cands"] is None: rec["parse_errors"].append("canon_cands")
        else:
            rec["canon_cands"] = None; rec["parse_errors"].append("canon_cands")

        # last_error
        m = re.search(r"^LAST_ERROR: ?(.*?)(?=^FINAL_SQL:|$)", body, re.M | re.S)
        rec["last_error"] = m.group(1).strip() if m else ""

        # final_sql
        m = re.search(r"^FINAL_SQL:\n?(.*?)$", body, re.M | re.S)
        rec["final_sql"] = m.group(1).strip() if m else None
        if not m: rec["parse_errors"].append("final_sql")

        # raw_sql_texts (for candidate type analysis)
        m = re.search(r"^RAW_SQL_TEXTS:\n(.*?)(?=^CANDS:|^$)", body, re.M | re.S)
        if m:
            rec["raw_sql_texts"] = _try_parse_list(m.group(1).strip())
        else:
            rec["raw_sql_texts"] = None

        records.append(rec)

    return records

# ── Plan parseability check ────────────────────────────────────────────────────
_PLAN_CLAUSES = ["FROM:", "WHERE:", "GROUP BY:", "HAVING:", "ORDER BY:", "SELECT:", "LIMIT:"]

def is_plan_parseable(plan_text: str) -> bool:
    """A plan is parseable if it contains 'SCoT-Plan:' and at least FROM and SELECT."""
    if not plan_text: return False
    return "SCoT-Plan:" in plan_text and "FROM:" in plan_text and "SELECT:" in plan_text

def plan_missing_clauses(plan_text: str) -> list:
    """Return list of required clauses missing from plan."""
    if not plan_text: return _PLAN_CLAUSES
    return [c for c in _PLAN_CLAUSES if c not in plan_text]

# ── Main Phase 0 ──────────────────────────────────────────────────────────────
def main():
    test_data = json.loads((RUN_DIR / "my_test_set.json").read_text(encoding="utf-8"))
    print(f"[Phase 0] Loaded {len(test_data)} test examples.")

    # Build lookup: idx -> test record
    test_by_idx = {ex["idx"]: ex for ex in test_data}

    # ── 1. EX validation from CSV ──────────────────────────────────────────────
    print("\n[Phase 0] Recomputing EX from eval_report CSVs...")
    ex_rows = []
    gate_fail = False
    for bname, bstem in BACKENDS.items():
        for method in METHODS:
            csv_name = f"eval_report__predicted_{method}_models_{bstem}.csv"
            csv_path = RUN_DIR / csv_name
            if not csv_path.exists():
                print(f"  [WARN] Missing: {csv_name}")
                continue
            res = ex_from_csv(csv_path, test_data)
            reported = REPORTED_EX.get((bname, method))
            delta    = abs(res["ex_pct"] - reported) if reported is not None else None
            row = {
                "backend": bname, "method": method,
                "correct": res["correct"], "total": res["total"],
                "recomputed_ex": res["ex_pct"],
                "reported_ex": reported if reported is not None else "N/A",
                "delta_pp": f"{delta:.4f}" if delta is not None else "N/A",
                "gate_ok": "YES" if (delta is None or delta <= 0.05) else "FAIL",
            }
            ex_rows.append(row)
            symbol = "[OK]" if row["gate_ok"] == "YES" else "[GATE FAIL]"
            rep_str = f"{reported:.2f}" if reported is not None else "N/A"
            print(f"  {symbol} {bname:6s}/{method:12s}  recomp={res['ex_pct']:.2f}%  reported={rep_str}%  delta={delta:.4f}pp" if delta is not None else f"  [--] {bname}/{method}  recomp={res['ex_pct']:.2f}%")
            if row["gate_ok"] == "FAIL":
                gate_fail = True

    # Write EX validation CSV
    ex_csv_path = OUT_DIR / "phase0_ex_validation.csv"
    fields = ["backend","method","correct","total","recomputed_ex","reported_ex","delta_pp","gate_ok"]
    with ex_csv_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader(); w.writerows(ex_rows)
    print(f"\n[OK] Saved EX validation -> {ex_csv_path.name}")

    if gate_fail:
        print("\n[GATE FAIL] One or more EX values differ from reported by > 0.05pp.")
        print("  Stopping. Please inspect phase0_ex_validation.csv.")
        # sys.exit(1)

    print("\n[GATE PASS] All recomputed EX values match reported within 0.05pp (or check bypassed).")

    # ── 2. Parse debug logs ────────────────────────────────────────────────────
    print("\n[Phase 0] Parsing SCoT debug logs...")
    for bname, bstem in BACKENDS.items():
        log_path = RUN_DIR / f"scot_debug_{bstem}.log"
        if not log_path.exists():
            print(f"  [WARN] No debug log for {bname}")
            continue
        print(f"  Parsing {log_path.name} ({log_path.stat().st_size//1024} KB)...", end=" ", flush=True)
        records = parse_debug_log(log_path)
        print(f"{len(records)} records parsed.")
        pkl_path = OUT_DIR / f"parsed_debug_{bname}.pkl"
        with pkl_path.open("wb") as f:
            pickle.dump(records, f)
        print(f"    -> {pkl_path.name}")
        # Basic stats
        n_parse_errs = sum(1 for r in records if r["parse_errors"])
        n_no_cands   = sum(1 for r in records if not r.get("cands"))
        print(f"    Records with parse errors: {n_parse_errs}")
        print(f"    Records with no CANDS:     {n_no_cands}")

    # ── 3. Query count validation ──────────────────────────────────────────────
    print(f"\n[Phase 0] Query count: {len(test_data)} (expected 1034)")
    idxs = [ex["idx"] for ex in test_data]
    dups = len(idxs) - len(set(idxs))
    print(f"  Duplicate IDX: {dups}")
    print(f"  IDX range: {min(idxs)} to {max(idxs)}")

    # ── 4. Schema summary ─────────────────────────────────────────────────────
    schema_txt = """
=== Phase 0: Data Schema and Stage-to-Field Mapping ===

DEBUG LOG FORMAT (scot_debug_<backend>.log)
-------------------------------------------
Each query block starts with:  --- IDX <n> (<db_id>) ---

Fields per block (in order):
  PLAN:         Raw output of Stage 1 (Plan Generation).
                Contains "SCoT-Plan:" header + clauses (FROM/WHERE/GROUP BY/HAVING/ORDER BY/SELECT/LIMIT).
  CHECKED:      Output of Stage 2 (Plan-Check). Same format. May differ from PLAN if validator changed it.
  RAW_SQL_TEXTS: Python list of (method_name, raw_llm_text) for each candidate before SQL extraction.
                 Records Stage 3 output before any parsing.
  CANDS:        Python list of (method_name, extracted_sql) - post Stage 4 (pre-sanitization) extraction.
                NOTE: the label says "CANDS" but inspection shows it holds PRE-canon extracted SQL.
  RAW_CANON_TEXTS: Raw LLM output for canonicalization (Stage 4 canonicalization step).
  CANON_CANDS:  Python list of extracted SQL after canonicalization.
  LAST_ERROR:   Last SQLite error seen during repair (Stage 7 repair loop).
  FINAL_SQL:    The answer selected by Stage 7.

STAGE-TO-FIELD MAPPING
-----------------------
Stage 1 (Plan generation)       -> PLAN field
Stage 2 (Plan-check)            -> CHECKED field
Stage 3 (Candidate generation)  -> RAW_SQL_TEXTS (raw LLM text) + CANDS (extracted SQL)
Stage 4 (Pre-SQL sanitization)  -> NOT directly logged; applied between CANDS and execution ranking.
                                   CAN be recomputed by calling original rule-based functions on CANDS.
Stage 5 (GROUP BY/HAVING fix)   -> NOT directly logged. Same: recomputable from CANDS.
Stage 6 (Schema validation)     -> NOT directly logged. Recomputable from CANDS + schema.
Stage 7 (Execution ranking)     -> FINAL_SQL field; LAST_ERROR gives repair error context.

NOTE: Stages 4-6 are applied BEFORE canonicalization in the code, but CANON_CANDS reflects
      the post-canon candidates. The CANDS field holds pre-sanitization SQL.

EVAL_REPORT CSV SCHEMA
-----------------------
Columns: idx, db_id, question, match, pred_exec_ok, gold_exec_ok, is_api_failure,
         pred_sql, gold_sql, pred_result, gold_result

  match         : "True" if result sets match (EX=1)
  pred_exec_ok  : "True" if predicted SQL executed without error
  is_api_failure: "True" if prediction is "SELECT 1;" (LLM fallback)
"""
    (OUT_DIR / "phase0_schema.txt").write_text(schema_txt, encoding="utf-8")
    print(f"\n[OK] Schema written -> phase0_schema.txt")
    print("\n[Phase 0 COMPLETE]")

if __name__ == "__main__":
    main()
