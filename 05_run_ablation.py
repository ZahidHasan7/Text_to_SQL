"""
05_run_ablation.py
==================
SCoT Ablation Study — evaluates the contribution of each pipeline component.

Ablation variants:
  A) Full SCoT          — all components ON (baseline)
  B) w/o Plan-Check     — skip Step 2 (plan validation); use raw plan directly
  C) w/o Ensemble       — only SCoT-Native candidate (no QD/Standard/etc.)
  D) w/o Canonicalization — skip the canonicalization step
  E) w/o Repair         — skip execution-guided LLM repair
  F) w/o Schema-Val     — skip _uses_only_schema() filtering
  G) SCoT-Native Only   — all ablations combined (pure single-path SCoT)

KEY OPTIMIZATION: Disk-based LLM cache
  All LLM responses are cached to disk (runs/spider_full/ablation/llm_cache.json).
  Variant A populates the cache; variants B-G re-use it at zero API cost.
  This means the full 7-variant ablation costs no more than running SCoT once.

Outputs (all in runs/spider_full/ablation/):
  predicted_ablation_<variant>.sql  — one SQL per line
  ablation_summary.csv             — EX%, correct, total for all variants
  llm_cache.json                   — disk cache of all LLM prompts/responses
  ablation_results.md              — human-readable results table

Usage:
  python 05_run_ablation.py
"""

import re, os, json, time, csv, datetime, sys, sqlite3, hashlib
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

PROJ_ROOT = Path(__file__).resolve().parent
sys.path.append(str(PROJ_ROOT))

from utils_llm import generate_text

# ─── Import 03_run_scot as a module ──────────────────────────────────────────
import importlib.util
spec = importlib.util.spec_from_file_location("scot", PROJ_ROOT / "03_run_scot.py")
scot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scot)

# ─── Paths ────────────────────────────────────────────────────────────────────
RUN_DIR        = PROJ_ROOT / "runs" / "spider_full"
ABLATION_DIR   = RUN_DIR / "ablation"
INPUT_TEST_SET = RUN_DIR / "my_test_set.json"
DISK_CACHE_FILE = ABLATION_DIR / "llm_cache.json"
ABLATION_DIR.mkdir(parents=True, exist_ok=True)

QUERY_TIMEOUT_SEC = 10
MAX_SQL_LEN       = 4000

# ─── Ablation variant flags ───────────────────────────────────────────────────
VARIANTS = {
    "A_full_scot":          {"plan_check": True,  "ensemble": True,  "canon": True,  "repair": True,  "schema_val": True},
    "B_no_plan_check":      {"plan_check": False, "ensemble": True,  "canon": True,  "repair": True,  "schema_val": True},
    "C_no_ensemble":        {"plan_check": True,  "ensemble": False, "canon": True,  "repair": True,  "schema_val": True},
    "D_no_canonicalization":{"plan_check": True,  "ensemble": True,  "canon": False, "repair": True,  "schema_val": True},
    "E_no_repair":          {"plan_check": True,  "ensemble": True,  "canon": True,  "repair": False, "schema_val": True},
    "F_no_schema_val":      {"plan_check": True,  "ensemble": True,  "canon": True,  "repair": True,  "schema_val": False},
    "G_scot_native_only":   {"plan_check": False, "ensemble": False, "canon": False, "repair": False, "schema_val": False},
}

# ─── Disk-based LLM cache ────────────────────────────────────────────────────
_disk_cache: dict = {}

def _load_disk_cache():
    global _disk_cache
    if DISK_CACHE_FILE.exists():
        try:
            _disk_cache = json.loads(DISK_CACHE_FILE.read_text(encoding="utf-8"))
            print(f"[cache] Loaded {len(_disk_cache)} cached responses from disk.")
        except Exception:
            _disk_cache = {}
    else:
        _disk_cache = {}

def _save_disk_cache():
    try:
        DISK_CACHE_FILE.write_text(json.dumps(_disk_cache), encoding="utf-8")
    except Exception as e:
        print(f"[cache] WARNING: failed to save cache: {e}")

def _cache_key(prompt: str, temperature: float, max_tokens: int) -> str:
    h = hashlib.sha256()
    h.update(prompt.encode("utf-8", errors="ignore"))
    h.update(str(float(temperature)).encode())
    h.update(str(int(max_tokens)).encode())
    return h.hexdigest()

def cached_llm_call(prompt: str, temperature: float, max_output_tokens: int, timeout: int) -> str:
    """LLM call with disk-backed cache. Zero API cost on cache hit."""
    key = _cache_key(prompt, temperature, max_output_tokens)
    if key in _disk_cache:
        return _disk_cache[key]
    # Cache miss — call the API
    result = scot._to_text(scot.ask_with_retry_cached(
        prompt, temperature=temperature, max_output_tokens=max_output_tokens, timeout=timeout))
    _disk_cache[key] = result
    return result

# ─── Evaluation helpers ───────────────────────────────────────────────────────
def norm_cell(x) -> str:
    try:
        if x is None: return ""
        s = str(x).strip()
        try: float(s); return s
        except ValueError: return s.lower()
    except Exception: return str(x)

def run_query(db_path: str, sql: str):
    import time as _t
    try:
        con = sqlite3.connect(db_path)
        _start = _t.monotonic()
        def _check():
            return 1 if _t.monotonic() - _start > QUERY_TIMEOUT_SEC else 0
        con.set_progress_handler(_check, 1000)
        cur = con.cursor()
        cur.execute(sql)
        rows = cur.fetchall()
        cur.close(); con.close()
        norm = [tuple(norm_cell(c) for c in r) for r in rows]
        norm.sort()
        return True, norm
    except Exception as e:
        return False, str(e)

def evaluate_predictions(pred_file: Path, test_data: list) -> dict:
    print(f"\n  {'-'*55}")
    print(f"  Evaluating : {pred_file.stem}")
    print(f"  {'-'*55}")
    preds = [ln.strip() for ln in pred_file.read_text(encoding="utf-8").splitlines()]
    total = len(test_data)
    while len(preds) < total: preds.append("SELECT 1;")
    preds = preds[:total]
    correct = api_failures = exec_errors = 0
    for i, (ex, pred_sql) in enumerate(zip(test_data, preds), 1):
        db = ex["db_path"].replace("C:\\Users\\Pathao Ltd\\Desktop\\Text_to_SQL-main", str(PROJ_ROOT))
        gold_sql = ex["gold_query"].strip().rstrip(";") + ";"
        pred_sql = pred_sql.strip().rstrip(";") + ";"
        if pred_sql.strip().lower() in ("select 1;", ""): api_failures += 1
        ok_g, gold_res = run_query(db, gold_sql)
        ok_p, pred_res = run_query(db, pred_sql)
        if not ok_p: exec_errors += 1
        if ok_g and ok_p and gold_res == pred_res: correct += 1
        if i % 200 == 0:
            print(f"    Progress: {i}/{total} | Running EX: {correct/i*100:.1f}%")
    acc = correct / total * 100 if total else 0
    print(f"  [OK] Final EX: {correct}/{total} = {acc:.2f}%  (api_failures={api_failures}, exec_errors={exec_errors})")
    return {
        "variant":      pred_file.stem.replace("predicted_ablation_", ""),
        "pred_file":    pred_file.name,
        "total":        total,
        "correct":      correct,
        "exec_acc_pct": round(acc, 4),
        "api_failures": api_failures,
        "exec_errors":  exec_errors,
        "evaluated_at": datetime.datetime.utcnow().isoformat() + "Z",
    }

# ─── Single-question SCoT with ablation flags ─────────────────────────────────
def run_scot_ablated(ex: dict, flags: dict) -> str:
    schema = ex["schema_str"]
    q      = ex["question"]
    schema_tables, schema_cols = scot._collect_schema_symbols(schema)

    # Step 1: PLAN
    try:
        plan = cached_llm_call(scot.build_plan_prompt(schema, q), 0.3, 800, 30)
    except Exception:
        return "SELECT 1;"

    # Step 2: PLAN-CHECK (ablatable)
    if flags["plan_check"]:
        try:
            checked = cached_llm_call(scot.build_check_prompt(schema, plan), 0.0, 800, 30)
            checked = scot._fix_incomplete_plan(checked)
            checked = scot._normalize_plan(checked)
            if "SCoT-Plan:" not in checked: checked = plan
        except Exception:
            checked = plan
    else:
        checked = plan

    schema_map = scot._enumerate_pk_fk_paths(schema)

    # Step 3: CANDIDATE GENERATION
    candidates = []
    try:
        sql_text = cached_llm_call(scot.build_sql_prompt(schema, checked), 0.2, 1024, 30)
        cand_sql = scot.extract_sql(sql_text)
        if cand_sql.strip().lower() != "select 1;":
            candidates.append(("SCoT-Native", cand_sql))
    except Exception: pass

    if flags["ensemble"]:
        try:
            qd_text = cached_llm_call(scot.build_qd_intercol_candidate_prompt(schema, q, schema_map), 0.2, 1200, 30)
            qd_sql = scot.extract_sql(qd_text)
            if qd_sql.strip().lower() != "select 1;": candidates.append(("QD-InterCol", qd_sql))
        except Exception: pass
        try:
            std_text = cached_llm_call(scot.build_standard_sql_prompt(schema, q), 0.0, 1024, 30)
            std_sql = scot.extract_sql(std_text)
            if std_sql.strip().lower() != "select 1;": candidates.append(("Standard", std_sql))
        except Exception: pass
        if scot._needs_negation(q):
            try:
                neg_text = cached_llm_call(scot.build_not_exists_template(schema, q, schema_map), 0.2, 1024, 30)
                neg_sql = scot.extract_sql(neg_text)
                if neg_sql.strip().lower() != "select 1;": candidates.append(("NOT-EXISTS", neg_sql))
            except Exception: pass
        if scot._needs_intersect(q):
            try:
                i_text = cached_llm_call(scot.build_intersect_skeleton(schema, q), 0.2, 1200, 30)
                i_sql = scot.extract_sql(i_text)
                if i_sql.strip().lower() != "select 1;": candidates.append(("INTERSECT", i_sql))
            except Exception: pass
        if scot._needs_union(q) and not scot._needs_intersect(q):
            try:
                u_text = cached_llm_call(scot.build_union_skeleton(schema, q), 0.2, 1200, 30)
                u_sql = scot.extract_sql(u_text)
                if u_sql.strip().lower() != "select 1;": candidates.append(("UNION", u_sql))
            except Exception: pass
        if scot._needs_subquery(q):
            try:
                sq_text = cached_llm_call(scot.build_subquery_extremum_skeleton(schema, q), 0.2, 1200, 30)
                sq_sql = scot.extract_sql(sq_text)
                if sq_sql.strip().lower() != "select 1;": candidates.append(("SUBQUERY", sq_sql))
            except Exception: pass

    candidate_sqls = [sql for _, sql in candidates]
    candidate_sqls = [scot._remove_dangling_keywords(c) for c in candidate_sqls]
    candidate_sqls = [scot._balance_parens(c) for c in candidate_sqls]
    candidate_sqls = [c[:MAX_SQL_LEN] for c in candidate_sqls]
    candidate_sqls = scot._dedup_preserve_order(candidate_sqls)
    candidate_sqls = [c for c in candidate_sqls if scot._is_viable_sql(c)]
    validated = []
    for c in candidate_sqls:
        _, f1 = scot._validate_group_by(c)
        _, f2 = scot._validate_having(f1)
        validated.append(f2)
    candidate_sqls = validated

    if flags["schema_val"]:
        candidate_sqls = [c for c in candidate_sqls if scot._uses_only_schema(c, schema_tables, schema_cols)]

    if not candidate_sqls:
        try:
            fallback_text = cached_llm_call(scot.build_sql_prompt(schema, checked), 0.0, 1024, 30)
            fallback_sql = scot.extract_sql(fallback_text)
            if fallback_sql.strip().lower() != "select 1;": candidate_sqls.append(fallback_sql)
        except Exception: pass

    # Step 5: CANONICALIZATION (ablatable)
    if flags["canon"] and candidate_sqls:
        canon_candidates = []
        for cand in candidate_sqls:
            try:
                canon_text = cached_llm_call(scot.build_canon_prompt(schema, cand), 0.0, 800, 30)
                canon_sql = scot.extract_sql(canon_text)
                canon_candidates.append(canon_sql if canon_sql.strip().lower() != "select 1;" else cand)
            except Exception:
                canon_candidates.append(cand)
    else:
        canon_candidates = list(candidate_sqls)

    canon_candidates = [scot._enforce_plan(scot._add_nocase(c), checked) for c in canon_candidates]
    candidate_sqls   = [scot._enforce_plan(scot._add_nocase(c), checked) for c in candidate_sqls]
    if scot._needs_negation(q):
        canon_candidates = [scot._prefer_setdiff(c, q) for c in canon_candidates]
        candidate_sqls   = [scot._prefer_setdiff(c, q) for c in candidate_sqls]

    canon_candidates = [c[:MAX_SQL_LEN] for c in canon_candidates]
    canon_candidates = scot._dedup_preserve_order(canon_candidates)
    canon_candidates = [c for c in canon_candidates if scot._is_viable_sql(c)]
    if flags["schema_val"]:
        canon_candidates = [c for c in canon_candidates if scot._uses_only_schema(c, schema_tables, schema_cols)]
    canon_candidates = scot._filter_by_plan_tables(canon_candidates, checked)
    candidate_sqls   = scot._filter_by_plan_tables(candidate_sqls, checked)

    all_candidates = list(set(canon_candidates + candidate_sqls))

    # Step 6: EXECUTION-GUIDED RANKING
    db_path = ex["db_path"].replace("C:\\Users\\Pathao Ltd\\Desktop\\Text_to_SQL-main", str(PROJ_ROOT))
    scored = []
    for cand in all_candidates:
        ok, err_msg = scot.try_exec(db_path, cand)
        exec_ok = 1 if ok else 0
        sanity = scot._check_result_sanity(cand, q, db_path, checked) if ok else 0
        plan_score = scot._score_against_plan(cand, checked)
        scored.append((exec_ok, -sanity, plan_score, cand, "" if ok else err_msg))
    scored.sort(key=lambda x: (x[0], x[1], x[2]), reverse=True)

    if scored and scored[0][0] == 1:
        return scored[0][3]

    # Step 7: REPAIR (ablatable)
    if not flags["repair"]:
        return scored[0][3] if scored else "SELECT 1;"

    last_error = scored[0][4] if scored else "no candidates"
    failed_sql = scored[0][3] if scored else "SELECT 1;"

    if "incomplete input" in (last_error or "").lower():
        quick = scot._clean_bad_tail(failed_sql)
        ok_q, _ = scot.try_exec(db_path, quick)
        if ok_q: return quick

    try:
        fixed = scot._enforce_plan(scot._add_nocase(scot.extract_sql(
            cached_llm_call(scot.build_repair_prompt(schema, q, checked, failed_sql, last_error), 0.0, 800, 30)
        )), checked)
        ok2, err2 = scot.try_exec(db_path, fixed)
        if ok2: return fixed
        fixed2 = scot._enforce_plan(scot._add_nocase(scot.extract_sql(
            cached_llm_call(scot.build_repair_prompt(schema, q, checked, fixed, err2), 0.0, 800, 30)
        )), checked)
        ok3, _ = scot.try_exec(db_path, fixed2)
        return fixed2 if ok3 else "SELECT 1;"
    except Exception:
        return "SELECT 1;"


# ─── Main ─────────────────────────────────────────────────────────────────────
def main():
    print("=" * 65)
    print("05_run_ablation.py — SCoT Ablation Study")
    print(f"Timestamp : {datetime.datetime.utcnow().isoformat()}Z")
    print("=" * 65)
    print("Disk cache: LLM responses shared across all variants (zero redundant API calls).")
    print()

    assert INPUT_TEST_SET.exists(), f"Missing: {INPUT_TEST_SET}"
    data = json.loads(INPUT_TEST_SET.read_text(encoding="utf-8"))
    print(f"[i] Loaded {len(data)} test examples.\n")

    _load_disk_cache()
    summary_rows = []

    for variant_name, flags in VARIANTS.items():
        out_path = ABLATION_DIR / f"predicted_ablation_{variant_name}.sql"
        print(f"\n{'='*65}")
        print(f"VARIANT : {variant_name}")
        print(f"FLAGS   : plan_check={flags['plan_check']} | ensemble={flags['ensemble']} | "
              f"canon={flags['canon']} | repair={flags['repair']} | schema_val={flags['schema_val']}")
        print(f"{'='*65}")

        # Resume support
        existing = []
        if out_path.exists():
            existing = [ln.strip() for ln in out_path.read_text(encoding="utf-8").splitlines() if ln.strip()]
        start_idx = len(existing)
        if start_idx >= len(data):
            print(f"[i] Already complete ({start_idx} predictions). Skipping generation.")
        else:
            if start_idx > 0:
                print(f"[i] Resuming from Q{start_idx + 1} ({start_idx} already done).")
            with out_path.open("a", encoding="utf-8") as f:
                for i, ex in enumerate(data, 1):
                    if i <= start_idx:
                        continue
                    try:
                        sql = run_scot_ablated(ex, flags)
                    except Exception as e:
                        print(f"  [ERR] Q{i}: {e}")
                        sql = "SELECT 1;"
                    f.write(sql + "\n")
                    f.flush()
                    if i % 50 == 0:
                        # Save disk cache every 50 questions
                        _save_disk_cache()
                        print(f"  [GEN] {i}/{len(data)} done  | cache size: {len(_disk_cache)} entries")
            _save_disk_cache()
            print(f"[OK] Generation done -> {out_path.name}")

        # Evaluate
        result = evaluate_predictions(out_path, data)
        result["flags"] = str(flags)
        summary_rows.append(result)

    # ── Save summary CSV ───────────────────────────────────────────────────────
    summary_path = ABLATION_DIR / "ablation_summary.csv"
    fields = ["variant", "exec_acc_pct", "correct", "total",
              "api_failures", "exec_errors", "flags", "evaluated_at"]
    with summary_path.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(summary_rows)

    # ── Save markdown results table ────────────────────────────────────────────
    baseline_acc = next((r["exec_acc_pct"] for r in summary_rows if "A_full" in r["variant"]), None)
    md_lines = [
        "# SCoT Ablation Study Results",
        "",
        f"**Dataset**: Spider Full Test Set ({summary_rows[0]['total'] if summary_rows else '?'} examples)",
        f"**Metric**: Execution Accuracy (EX%)",
        f"**Generated**: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "| Variant | Correct | Total | EX (%) | Δ vs Full SCoT |",
        "| :--- | :---: | :---: | :---: | :---: |",
    ]
    for r in summary_rows:
        if baseline_acc is not None and "A_full" not in r["variant"]:
            delta = f"{r['exec_acc_pct'] - baseline_acc:+.2f}%"
        else:
            delta = "—"
        label = r["variant"].replace("_", " ").replace("A full scot", "**A Full SCoT (baseline)**")
        label = label.replace("B no plan check", "B w/o Plan-Check")
        label = label.replace("C no ensemble", "C w/o Ensemble")
        label = label.replace("D no canonicalization", "D w/o Canonicalization")
        label = label.replace("E no repair", "E w/o Repair")
        label = label.replace("F no schema val", "F w/o Schema Validation")
        label = label.replace("G scot native only", "G SCoT-Native Only")
        md_lines.append(f"| {label} | {r['correct']} | {r['total']} | {r['exec_acc_pct']:.2f}% | {delta} |")

    md_lines += ["", "## Interpretation", ""]
    md_lines += ["- **Negative Δ** = component helps accuracy (removing it hurts)"]
    md_lines += ["- **Positive Δ** = component may be hurting accuracy"]
    md_lines += ["- The largest negative delta identifies the most impactful component"]

    md_path = ABLATION_DIR / "ablation_results.md"
    md_path.write_text("\n".join(md_lines), encoding="utf-8")

    # ── Print final table ──────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print("ABLATION STUDY — FINAL RESULTS")
    print(f"{'='*65}")
    print(f"  {'Variant':<30} {'EX (%)':<10} {'Correct':<9} {'Delta'}")
    print(f"  {'-'*60}")
    for r in summary_rows:
        if baseline_acc is not None and "A_full" not in r["variant"]:
            delta = f"{r['exec_acc_pct'] - baseline_acc:+.2f}%"
        else:
            delta = "baseline"
        print(f"  {r['variant']:<30} {r['exec_acc_pct']:<10.2f} {r['correct']:<9} {delta}")
    print(f"{'='*65}")
    print(f"\n[OK] Summary CSV     -> {summary_path}")
    print(f"[OK] Results MD      -> {md_path}")
    print(f"[OK] LLM Disk Cache  -> {DISK_CACHE_FILE}  ({len(_disk_cache)} entries)")
    print("[DONE] Ablation complete.")


if __name__ == "__main__":
    main()
