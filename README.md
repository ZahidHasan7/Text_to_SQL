# SCoT: Structured Chain-of-Thought Prompting for Text-to-SQL

> **Journal Paper Codebase** — A scientifically rigorous, reproducible implementation of Structured Chain-of-Thought (SCoT) prompting for cross-domain Text-to-SQL generation, evaluated on the Spider benchmark.

---

## Overview

This repository contains the complete research codebase for the journal paper:

> **"Exploring Chain-of-Thought Style Prompting for Text-to-SQL"**  
> Evaluated on the **Spider** benchmark (Cross-Domain Text-to-SQL)  
> Metric: **Execution Accuracy (EX)**

The codebase includes:
- A unified LLM pipeline supporting **OpenRouter**, **Gemini**, and **OpenAI** models via a single API
- Strict **database-level data splitting** to prevent prompt contamination
- Automated **data integrity and leakage tests**
- Five evaluation methods: **SCoT**, **CoT**, **Standard**, **QDecomp**, **QDecomp-InterCol**
- Complete **experiment logging and audit trail** for journal reproducibility

---

## Repository Structure

```
.
├── utils_llm.py              # Unified LLM API (OpenRouter + Gemini + OpenAI, retry, cache)
│
├── 01_data_split.py          # Spider dev set preparation + audit manifest
├── 02_leakage_tests.py       # Automated data integrity & leakage tests
├── 03_run_scot.py            # SCoT (Structured Chain-of-Thought) runner  ← Main Method
├── 03_run_standard.py        # Standard prompting baseline
├── 03_run_cot.py             # Chain-of-Thought baseline
├── 03_run_qdecomp.py         # Question Decomposition baseline
├── 03_run_qd_intercol.py     # QDecomp + Inter-Column baseline
├── 04_evaluation.py          # Execution Accuracy evaluator + experiment log
│
├── utils_gemini_rest.py      # Backward-compatible wrapper that delegates to utils_llm.py
├── openai_gpt/               # Legacy OpenAI utilities (kept for reference)
│
├── diagrams/                 # Architecture and result figures
├── main.tex                  # LaTeX journal paper source
│
├── Thesis_Report_*.pdf       # Original thesis report
├── Exploring Chain of Thought*.pdf  # Journal paper draft
├── QUICK_START_GUIDE.md      # Setup and run instructions
└── requirements.txt          # Python dependencies
```

> **Note:** `data/` (Spider dataset) and `runs/` (experiment outputs) are excluded from the repository due to size. See setup instructions below.

---

## Experimental Setup

| Parameter | Value |
|---|---|
| Dataset | Spider Dev Set |
| Evaluation Examples | 1,034 |
| Random Seed | 42 |
| Metric | Execution Accuracy (EX) |
| Primary Model | OpenRouter model selected via `OPENROUTER_MODEL` |
| Baseline Model | OpenRouter, Gemini, or OpenAI depending on `LLM_PROVIDER` |
| SQLite Timeout | 10 seconds per query |

---

## Setup

### 1. Clone the Repository
```bash
git clone https://github.com/ZahidHasan7/Text_to_SQL.git
cd Text_to_SQL
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Download the Spider Dataset
Download from [Yale Spider](https://yale-seas.github.io/spider/) and place it as:
```
data/
└── spider/
    ├── dev.json
    ├── dev_gold.sql
    ├── tables.json
    └── database/
```

### 4. Configure API Keys
Create a local `.env` file in the project root. The recommended setup uses a single OpenRouter API key:
```env
# Recommended: OpenRouter
OPENROUTER_API_KEY=your_openrouter_api_key_here
OPENROUTER_MODEL=google/gemini-2.5-pro

# Optional: force OpenRouter explicitly if you want to override auto-detection
LLM_PROVIDER=openrouter

# Legacy direct providers are still supported if you explicitly configure them:
# GEMINI_API_KEY=your_gemini_api_key_here
# OPENAI_API_KEY=your_openai_api_key_here
```

> **Important:** `.env` is local only and must not be committed to GitHub. The repository includes `.env.example` as a placeholder template, not a secret-bearing file.

The active LLM path is:

`runner -> utils_gemini_rest.py (legacy compatibility only, where used) -> utils_llm.py -> OpenRouter`

For OpenRouter, you only need to change `OPENROUTER_MODEL` to switch models. No Python source changes are required.

---

## Running the Experiment

Execute the pipeline in order:

```bash
# Step 1: Prepare the dataset (writes runs/spider_full/my_test_set.json)
python 01_data_split.py

# Step 2: Validate data integrity (must pass all 6 tests)
python 02_leakage_tests.py

# Step 3: Run the SCoT method (main contribution)
python 03_run_scot.py

# Step 3b: Run baselines (optional, for comparison)
python 03_run_standard.py
python 03_run_cot.py
python 03_run_qdecomp.py
python 03_run_qd_intercol.py

# Step 4: Evaluate all methods
python 04_evaluation.py
```

---

## Output Files

After running the full pipeline, the following audit trail files are generated in `runs/spider_full/`:

| File | Description |
|---|---|
| `split_manifest.json` | Dataset split details: seed, counts, DB distribution |
| `leakage_test_log.json` | Results of all 6 integrity tests (A–F) |
| `predicted_scot_*.sql` | Per-item SQL predictions from each method |
| `eval_report__<method>.csv` | Per-question breakdown: match, SQL, result rows |
| `eval_summary.csv` | Cross-model EX accuracy comparison table |
| `experiment_log.json` | Full evaluation protocol + final results |

---

## Data Integrity & Leakage Prevention

A key contribution of this codebase is the **explicit prevention of prompt contamination**. The original thesis codebase contained a data leakage issue where few-shot demonstration databases (e.g., `tvshow`, `concert_singer`) appeared in the evaluation test set. This has been corrected as follows:

- `01_data_split.py` performs **database-level** data splitting with a fixed random seed
- `02_leakage_tests.py` runs **6 automated integrity tests** and writes a JSON audit log
- All splits are **deterministically reproducible** using `random.seed(42)`

Reviewers can verify the exact split by inspecting `runs/spider_full/split_manifest.json`.

---

## Requirements

```
requests
python-dotenv
```

> Python 3.10+ recommended. SQLite is part of the Python standard library.

---

## Citation

If you use this code, please cite:

```bibtex
@article{scot_texttosql_2026,
  title   = {Exploring Chain-of-Thought Style Prompting for Text-to-SQL},
  author  = {[Authors]},
  journal = {[Journal Name]},
  year    = {2026}
}
```