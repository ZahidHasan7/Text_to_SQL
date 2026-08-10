# Text-to-SQL SCoT Pipeline - AI Agent Instructions

This is a research codebase for comparing Text-to-SQL prompting methods, with focus on a novel Structured Chain-of-Thought (SCoT) approach.

## Project Architecture

### Core Pipeline (Sequential Execution)

1. **Data Preparation** (`1_prepare_data.py`) → Creates test sets from Spider dataset
2. **Method Execution** (`2_run_*.py`, `3_run_scot_sql.py`) → Generates SQL predictions
3. **Evaluation** (`4_eval_exec_acc.py`) → Measures execution accuracy
4. **Analysis** (`5_diff_methods.py`, `analyze_scot_failures.py`) → Comparative error analysis

### Directory Structure

- `runs/dev_600/` - Gemini 2.5 Pro experiments (600 samples)
- `runs/dev_500/` - GPT-4o-mini experiments (500 samples)
- `openai_gpt/` - GPT-specific scripts (mirrors root structure)
- `data/spider/` - Spider benchmark (dev.json, tables.json, database/)

## Key Technical Patterns

### Schema Format Convention

Spider schemas are converted to text format with explicit foreign keys:

```python
# table_name (col1, col2, col3)
# FK: table1.fk_col -> table2.pk_col
```

This format is used in ALL prompts. See `format_schema_api_docs()` in `1_prepare_data.py`.

### LLM API Wrapper Pattern (`utils_gemini_rest.py`, `utils_openai_rest.py`)

- **Fallback chain**: Try gemini-2.5-pro → gemini-2.5-flash → gemini-2.5-flash-lite
- **In-memory cache**: Prevents duplicate API calls (256 entry LRU cache)
- **Connection pooling**: Reuses HTTP session for efficiency
- **Retry logic**: 3 attempts with exponential backoff

```python
# Standard usage pattern across all scripts:
from utils_gemini_rest import gemini_generate_text

text = gemini_generate_text(
    prompt,
    timeout=30,
    temperature=0.2,
    max_output_tokens=1024
)
```

### Temperature Strategy (Critical for SCoT)

- **Plan generation**: 0.3 (slight diversity)
- **Validation/repair**: 0.0 (deterministic)
- **Candidate generation**: 0.0-0.2 (balanced)
- **Baselines (CoT/QDecomp/Standard)**: 0.0 or 0.2

### SQL Extraction Pattern

ALL methods use similar regex extraction from LLM responses:

````python
def extract_sql(text: str) -> str:
    # Try fenced block first: ```sql\nSELECT ...\n```
    # Fallback: search for SELECT...;
    # Last resort: "SELECT 1;" (safe fallback)
````

## SCoT Implementation Deep Dive (`3_run_scot_sql.py`)

### Seven-Stage Pipeline

1. **Plan Generation** (`build_plan_prompt`) - Structured JSON-like format
2. **Plan Check** (`build_check_prompt`) - Schema validation
3. **Multi-Candidate** - 4-7 SQL variants per query
4. **Sanitization** - Regex cleanup (trailing commas, syntax fixes)
5. **Canonicalization** (`build_canon_prompt`) - Normalize formatting
6. **Execution Ranking** (`try_exec`) - Run against Spider database
7. **Repair** (`build_repair_prompt`) - Fix failed queries with error context

### Pattern Detection for Candidate Selection

```python
_NEG_TOKENS = {"no", "without", "none", "exclude", "missing"}
_INTERSECT_TOKENS = {"both", "and", "common", "shared"}
_UNION_TOKENS = {"or", "either", "any"}
_EXTREMUM_TOKENS = {"most", "least", "highest", "top", "maximum"}
```

When question matches patterns, generate specialized templates:

- `build_not_exists_template()` - For negation queries
- `build_intersect_skeleton()` - For "both X and Y"
- `build_union_skeleton()` - For "either X or Y"
- `build_subquery_extremum_skeleton()` - For "most/least per group"

### Candidate Ensemble Strategy

Always generate:

1. **SCoT-Native** (plan-based)
2. **QD-InterCol** (decomposition with column grounding)
3. **Standard** (direct SQL, no reasoning)

Conditionally add (based on question analysis): 4. NOT EXISTS template 5. INTERSECT skeleton 6. UNION skeleton 7. Subquery for extremum

### Validation Helpers

```python
def _enumerate_pk_fk_paths(schema_str) -> dict
# Parses schema to extract all FK relationships

def _validate_sql_structure(sql, schema_map) -> bool
# Checks: table.column existence, GROUP BY correctness, JOIN keys
```

## Evaluation Methodology

### Execution Accuracy (`4_eval_exec_acc.py`)

1. Execute predicted SQL → get result set
2. Execute gold SQL → get result set
3. Normalize (lowercase text, sort rows)
4. Compare: if identical → correct

**Critical**: Uses `norm_cell()` to handle None, numbers, strings consistently.

### Output Format

- **Per-method CSV**: `exec_eval_report__predicted_<method>.csv`
- **Summary CSV**: `exec_eval_summary.csv` (all methods, accuracy comparison)

## Common Modification Patterns

### Adding a New Prompting Method

1. Create `2_run_<method>.py` using template from `2_run_standard.py`
2. Implement `build_prompt()` and `extract_sql()` functions
3. Output predictions to `runs/dev_600/predicted_<method>.sql`
4. Add to `PRED_FILES` list in `4_eval_exec_acc.py`

### Adjusting SCoT Pipeline

- **Change plan format**: Edit `FEW_SHOT_PLAN` examples in `3_run_scot_sql.py` (line ~670)
- **Add validation rule**: Modify `build_check_prompt()` or add regex in sanitization
- **New candidate pattern**: Add detection function (`_needs_<pattern>()`) and template builder

### Modifying Schema Format

- **Change only in**: `format_schema_api_docs()` in `1_prepare_data.py`
- **Impacts**: All prompts across all methods (they read `schema_str` from test set)

## Testing and Debugging

### Quick Accuracy Check

```powershell
python -c "
import csv
p='runs/dev_600/exec_eval_report__predicted_scot_models_gemini-2.5-pro.csv'
rows=list(csv.DictReader(open(p,encoding='utf-8')))
corr=sum(r['match'].strip().lower()=='true' for r in rows)
print(f'{corr}/{len(rows)} = {corr*100/len(rows):.2f}%')
"
```

### Debug Logging

- SCoT writes detailed logs to `runs/dev_600/scot_debug.log`
- Check for: validation failures, execution errors, candidate counts

### Compare Methods

```powershell
python 5_diff_methods.py runs/dev_600/exec_eval_report__predicted_scot*.csv runs/dev_600/exec_eval_report__predicted_standard.csv
```

Outputs indices where one method wins over the other.

## Critical Constraints

### SQL Dialect

- **Spider uses SQLite** - No CTEs, no window functions (SQL-92 only)
- All prompts must specify: "SQL-92 only, no CTE/window"
- Use LIMIT instead of TOP, use || for concatenation

### API Rate Limiting

- `SLEEP_EVERY = 10` - Pause every 10 queries
- Adjust if hitting rate limits (increase sleep duration)

### Timeout Settings

- Individual LLM calls: 30-120s (varies by complexity)
- Database execution: 30s per query (`try_exec()`)
- Total SCoT runtime: ~30-40 minutes for 600 queries

## Dependencies and Environment

### Required Environment Variables (`.env`)

```
GEMINI_API_KEY=your_key_here
GEMINI_BASE=https://generativelanguage.googleapis.com/v1beta
OPENAI_API_KEY=your_key_here  # For GPT experiments
```

### Python Requirements

- Python 3.8+ (uses `typing._t`, pathlib)
- Core: `requests`, `python-dotenv`
- Built-in: `sqlite3`, `json`, `re`, `csv`, `time`

### Virtual Environment Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Reproducibility Notes

### Fixed Elements

- Dataset: `my_test_set.json` (deterministic subset)
- Hyperparameters: Temperatures, timeouts documented in code
- Evaluation: Deterministic SQL execution + comparison

### Variable Elements

- LLM responses vary slightly even at temperature=0.0 (API non-determinism)
- Expect ±1-2% accuracy variation across runs
- Relative rankings (SCoT > baselines) are stable

### Cache Behavior

- Enable: Faster re-runs, exact reproducibility within session
- Disable: `GEMINI_CACHE_MAX=0` for fresh API calls every run

## Code Style Conventions

- **Imports**: Standard library → third-party → local utils
- **Path handling**: Use `pathlib.Path` (not os.path)
- **String formatting**: f-strings preferred over .format()
- **SQL formatting**: Triple-quoted strings for readability
- **Error handling**: Try-except with fallback to "SELECT 1;" for safety

## Common Pitfalls

1. **Schema changes**: If you modify schema format, regenerate test set (run step 1 again)
2. **File paths**: All scripts assume they're run from project root
3. **Database location**: Spider `database/` folder must be in `data/spider/`
4. **Prediction line count**: Must match test set size (600 for dev_600)
5. **Temperature=0.0 ≠ deterministic**: LLMs still vary slightly—run multiple times for confidence

## Extension Points

### Supporting New LLMs

1. Create `utils_<provider>_rest.py` mirroring existing wrappers
2. Implement same interface: `<provider>_generate_text(prompt, temperature, ...)`
3. Duplicate scripts in `<provider>/` subdirectory (follow `openai_gpt/` pattern)

### Adding New Validation Rules

- For syntactic checks: Add regex in sanitization stage (line ~1100 in `3_run_scot_sql.py`)
- For semantic checks: Modify `build_check_prompt()` or `build_canon_prompt()`
- For execution checks: Extend `try_exec()` with additional cardinality heuristics

### Optimizing Performance

- **Parallelize candidates**: Use threading for independent LLM calls (currently sequential)
- **Smart caching**: Cache plan + check results, only regenerate candidates
- **Model routing**: Use cheaper models for simple queries, expensive for complex ones
