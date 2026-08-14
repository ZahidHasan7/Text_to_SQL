# 2_run_standard.py
# Standard: no reasoning. Direct SQL only (fenced), temp=0.0
import json, sys, time, re
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

from utils_llm import generate_text

PROJ_ROOT = Path(__file__).resolve().parent
RUN_DIR   = PROJ_ROOT / "runs" / "spider_full"
INPUT_TEST_SET = RUN_DIR / "my_test_set.json"
OUTPUT_FILE    = RUN_DIR / "predicted_standard.sql"
SLEEP_EVERY = 10

def build_prompt(schema_str: str, question: str) -> str:
    # (A) UPDATE: The prompt format has been updated as per your instructions.
    # The "SELECT ..." part has been moved out of the example.
    return f"""{schema_str.strip()}

Return ONLY the final SQL for the question below, wrapped in a fenced block like:

```sql
SELECT ...
```
Rules:

Use only the tables/columns that appear in the schema above.
Define aliases in FROM/JOIN before using them.
SQL-92 only (no CTE/window).
No explanation outside the fenced block.
Question: {question}

"""

def extract_sql(text: str) -> str:
    # (B) UPDATE: The Regex logic has been updated as per your instructions.
    t = text or ""
    
    # 1) First, search for the complete fenced block (```sql ... ```).
    m = re.search(r"```sql\s*(.*?)```", t, flags=re.DOTALL | re.IGNORECASE)
    
    if m:
        sql = m.group(1).strip()
    else:
        # 2) If no fenced block is found, fallback to searching for a plain "SELECT ... ;".
        m2 = re.search(r"(SELECT\b.*?;)", t, flags=re.DOTALL | re.IGNORECASE)
        sql = (m2.group(1).strip() if m2 else "SELECT 1;")

    if ";" in sql:
        sql = sql.split(";", 1)[0] + ";"
        
    return sql.replace("\n", " ").replace("\r", " ").strip()

def main():
    data = json.loads(INPUT_TEST_SET.read_text(encoding="utf-8"))
    print(f"[i] Loaded {len(data)} items")
    start_idx = 0
    preds = []
    if OUTPUT_FILE.exists():
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            preds = [line.strip() for line in f if line.strip()]
        start_idx = len(preds)
        print(f"[i] Found {start_idx} existing predictions. Resuming...")
    
    out_f = OUTPUT_FILE.open("a", encoding="utf-8")

    for i, ex in enumerate(data, 1):
        if i <= start_idx:
            continue
        p = build_prompt(ex["schema_str"], ex["question"])
        try:
            txt = generate_text(p, temperature=0.0, max_output_tokens=600, timeout=30)
            sql = extract_sql(txt)
        except Exception as e:
            print(f"\n[CRITICAL ERROR] API or Network failure at item {i}: {e}")
            print("Terminating run. Fix the issue and restart to resume from this item.")
            sys.exit(1)
        preds.append(sql)
        out_f.write(sql + "\n")
        out_f.flush()
        if i % SLEEP_EVERY == 0:
            print(f" ... processed {i}, pause ...")
            time.sleep(1.0)
    out_f.close()
    print(f"[OK] Saved -> {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
