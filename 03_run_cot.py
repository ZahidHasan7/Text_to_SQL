# 03_run_cot.py
# Run a simple CoT baseline over runs/spider_full/my_test_set.json
# Outputs: runs/spider_full/predicted_cot_models_{modelname}.sql

import os, json, sys, time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from utils_llm import generate_text

# ---- CONFIG ----
PROJ_ROOT = Path(__file__).resolve().parent
RUN_DIR   = PROJ_ROOT / "runs" / "spider_full"
INPUT_TEST_SET = RUN_DIR / "my_test_set.json"

# Model is taken from .env OPENROUTER_MODEL (same as all other 03_run_*.py scripts)
MODEL_ID = (os.getenv("OPENROUTER_MODEL") or os.getenv("GEMINI_MODEL") or "google/gemini-2.5-flash").strip()
MODEL_FILE_STEM = MODEL_ID.replace("/", "_").replace(":", "_").replace(" ", "_")
OUTPUT_FILE = RUN_DIR / f"predicted_cot_models_{MODEL_FILE_STEM}.sql"

TEMPERATURE_PLAN = 0.0
SLEEP_EVERY = 10

def create_cot_prompt(question, schema_str):
    """
    Very simple CoT prompt (logical SQL order).
    """
    p = []
    p.append(schema_str.strip())
    p.append(f"### {question}")
    p.append("A: # Let's think step by step")
    p.append("# 1) Choose tables (FROM/JOIN).")
    p.append("# 2) Filter rows (WHERE).")
    p.append("# 3) Group if needed (GROUP BY).")
    p.append("# 4) Filter groups (HAVING).")
    p.append("# 5) Final columns (SELECT).")
    p.append("# Thus, the answer is:")
    p.append("```sql\nSELECT")  # force SQL block
    prompt = "\n".join(p)
    return prompt

def extract_sql_from_response(text: str) -> str:
    """
    Try to extract a single SQL statement from model output.

    The CoT prompt ends with "```sql\\nSELECT" to force the model into a SQL
    block. The model therefore returns only the CONTINUATION after SELECT
    (e.g. "COUNT(*) FROM flights;\\n```"). We must handle three cases:

      Case A: Model restated the full fence:  "```sql\\nSELECT ...\\n```"
      Case B: Model continued (closing fence only): "COUNT(*) FROM t;\\n```"
      Case C: Model returned plain text with SELECT somewhere inside
    """
    try:
        t = text or ""

        # Case A: full ```sql ... ``` block present
        if "```sql" in t:
            s = t.find("```sql") + len("```sql")
            e = t.find("```", s)
            sql = t[s:e].strip() if e != -1 else t[s:].strip()

        # Case B: closing fence only — model continued from the pre-filled SELECT
        elif "```" in t:
            # Extract everything before the closing fence
            e = t.find("```")
            sql_body = t[:e].strip()
            if sql_body.lower().startswith("select"):
                # Model happened to re-include SELECT
                sql = sql_body
            else:
                # Prepend the SELECT that the prompt already provided
                sql = "SELECT " + sql_body

        # Case C: plain text — search for SELECT keyword (case-insensitive)
        elif "SELECT" in t.upper():
            s = t.upper().find("SELECT")
            sql = t[s:].strip()

        else:
            # Last resort: treat entire response as SELECT continuation
            sql = "SELECT " + t.strip()

        # Keep up to first semicolon
        if ";" in sql:
            sql = sql.split(";", 1)[0] + ";"
        # Flatten to one line
        sql = sql.replace("\n", " ").replace("\r", " ").strip()
        # Final guard
        if not sql.lower().startswith("select"):
            return "SELECT 1;"
        return sql
    except Exception:
        return "SELECT 1;"

def run():
    assert INPUT_TEST_SET.exists(), f"Missing test set: {INPUT_TEST_SET}"
    data = json.loads(INPUT_TEST_SET.read_text(encoding="utf-8"))
    print(f"[i] Loaded {len(data)} items from {INPUT_TEST_SET}")
    print(f"[i] Model : {MODEL_ID}")
    print(f"[i] Output: {OUTPUT_FILE}")

    # ---- Checkpoint / resume (same pattern as 03_run_standard.py) ----
    start_idx = 0
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            existing = [line.strip() for line in f if line.strip()]
        start_idx = len(existing)
        print(f"[i] Found {start_idx} existing predictions. Resuming...")

    out_f = OUTPUT_FILE.open("a", encoding="utf-8")

    for i, ex in enumerate(data, 1):
        if i <= start_idx:
            continue
        q = ex["question"]
        schema = ex["schema_str"]
        prompt = create_cot_prompt(q, schema)

        try:
            resp_text = generate_text(
                prompt,
                timeout=90,
                temperature=TEMPERATURE_PLAN,
            )
        except Exception as e:
            print(f"\n[CRITICAL ERROR] API or Network failure at item {i}: {e}")
            print("Terminating run. Fix the issue and restart to resume from this item.")
            out_f.close()
            sys.exit(1)

        sql = extract_sql_from_response(resp_text)
        out_f.write(sql + "\n")
        out_f.flush()

        if i % SLEEP_EVERY == 0:
            print(f"  ... processed {i}, short pause ...")
            time.sleep(1.0)

    out_f.close()
    print(f"[OK] Saved -> {OUTPUT_FILE}")

if __name__ == "__main__":
    run()
