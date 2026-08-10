# Quick Start Guide: Enhanced SCoT Pipeline

## Prerequisites

```powershell
# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Verify dependencies
python -c "import sqlite3, json, re; print('All imports OK')"
```

## Running SCoT

### Standard Execution

```powershell
# Run on dev_600 dataset
python 3_run_scot_sql.py
```

**Expected Output:**

- Predictions saved to: `runs/dev_600/predicted_scot_models_gemini-2.5-pro.sql`
- Debug log: `runs/dev_600/scot_debug.log`
- Processing time: ~30-40 minutes (600 queries)

### Evaluation

```powershell
# Compute execution accuracy
python 4_eval_exec_acc.py

# Or quick check
python -c @"
import csv, pathlib
p=pathlib.Path(r'runs/dev_600/exec_eval_report__predicted_scot_models_gemini-2.5-pro.csv')
rows=list(csv.DictReader(open(p,encoding='utf-8')))
corr=sum(r['match'].strip().lower()=='true' for r in rows)
print('SCoT Native:',corr,'/',len(rows),'=',round(corr*100/len(rows),2),'%')
"@
```

**Target Metric:** ≥84% accuracy (504+ correct out of 600)

---

## Key Configuration Points

### Temperature Settings (Line 1280+)

```python
temperature=0.2  # Slight diversity while maintaining determinism
```

**Tuning guidance:**

- 0.0 = fully deterministic (lower diversity)
- 0.2 = balanced (recommended)
- 0.4 = higher diversity (may reduce consistency)

### Candidate Count

The pipeline generates **4-7 candidates** based on question patterns:

- Always: SCoT-Native, QD-InterCol, Standard
- Conditional: NOT EXISTS, INTERSECT, UNION, SUBQUERY

### Timeout Settings (Line 1282+)

```python
timeout=30  # seconds per LLM call
```

---

## Troubleshooting

### Issue: "No candidates generated"

**Cause:** All candidates filtered out by validators  
**Fix:** Check debug log for validation failures; may need schema format adjustment

### Issue: Low accuracy (<80%)

**Possible causes:**

1. Schema format not matching expected pattern `# table (col1, col2, ...)`
2. FK relationships not explicitly defined in schema
3. Database path issues in test set

**Diagnostic:**

```powershell
# Check debug log for common errors
Select-String -Path "runs/dev_600/scot_debug.log" -Pattern "LAST_ERROR:" | Group-Object | Sort-Object Count -Descending
```

### Issue: Execution timeout

**Cause:** LLM API slow or rate-limited  
**Fix:** Increase `timeout=30` → `timeout=60` or add `time.sleep(2.0)` in loop

---

## Feature Flags

### Disable Canonicalization (if needed for speed)

**Line 1392-1405:** Comment out the canonicalization loop

```python
# canon_candidates = []
# for cand in candidate_sqls:
#     canon_candidates.append(cand)  # Skip canonicalization
```

### Disable Specific Candidate Types

**Lines 1310-1355:** Comment out unwanted candidate blocks:

```python
# # Candidate 5: INTERSECT skeleton
# if _needs_intersect(q):
#     # ... (comment entire block)
```

---

## Performance Optimization

### For Large Datasets (1000+ queries)

1. Enable batch caching more aggressively
2. Reduce candidate count to 4 (disable UNION/SUBQUERY)
3. Increase `SLEEP_EVERY` from 10 to 5

### For Maximum Accuracy (slower)

1. Increase temperature to 0.3 for more diversity
2. Generate 2 candidates per pattern (remove dedup temporarily)
3. Add third repair attempt in repair loop

---

## Output Files

| File                                                         | Purpose                  | Format                |
| ------------------------------------------------------------ | ------------------------ | --------------------- |
| `predicted_scot_models_gemini-2.5-pro.sql`                   | Final SQL predictions    | One SQL per line      |
| `scot_debug.log`                                             | Detailed execution trace | Text blocks per query |
| `exec_eval_report__predicted_scot_models_gemini-2.5-pro.csv` | Per-query results        | CSV with match column |
| `exec_eval_summary.csv`                                      | Overall accuracy         | CSV with all methods  |

---

## Validation Checklist

Before claiming ≥84% accuracy:

- [ ] Run completed without crashes
- [ ] All 600 queries processed
- [ ] No queries returned "SELECT 1;" as final output
- [ ] Debug log shows candidate diversity (not all SCoT-Native)
- [ ] Execution accuracy >= 504/600 (84%)
- [ ] Results reproducible across runs (deterministic with same seed)

---

## Advanced: Pattern Detection Tuning

If accuracy is high but specific patterns fail:

### Add Custom Negation Tokens

**Line 30:** Extend `_NEG_TOKENS_EXPANDED`

```python
_NEG_TOKENS_EXPANDED = {
    # ... existing tokens ...
    "absent", "lacking", "excluding",  # Add custom tokens
}
```

### Adjust INTERSECT Detection

**Line 53:** Modify `_needs_intersect()` regex

```python
# More aggressive detection
if re.search(r"\bboth\b.*\band\b", s):
    return True
```

---

## Support

**Issues to report:**

1. Syntax errors in generated SQL (attach debug log snippet)
2. Pattern detection false positives/negatives (share question)
3. Schema parsing failures (share schema format)

**Expected behavior:**

- No Python exceptions during run
- All queries produce valid SQL (may be incorrect but syntactically valid)
- Execution-guided ranking always selects executable candidate if one exists

---

## Quick Commands Reference

```powershell
# Full pipeline
python 3_run_scot_sql.py && python 4_eval_exec_acc.py

# Check syntax only
python -m py_compile 3_run_scot_sql.py

# View debug log tail
Get-Content runs/dev_600/scot_debug.log -Tail 50

# Count pattern triggers
Select-String -Path "runs/dev_600/scot_debug.log" -Pattern "NOT-EXISTS|INTERSECT|UNION|SUBQUERY" | Measure-Object

# Compare with baselines
python 5_diff_methods.py
```

---

**Last Updated:** November 21, 2025  
**Version:** 2.0 (Ensemble with validators)  
**Status:** Production ready
