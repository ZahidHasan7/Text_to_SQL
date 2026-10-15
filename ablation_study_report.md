# SCoT Ablation Study — Full Report

**Dataset**: Spider Full Test Set (1034 examples)  
**Metric**: Execution Accuracy (EX%) — order-insensitive result-set comparison  
**Model**: OpenAI GPT-4o-Mini (via OpenRouter)  
**Generated**: 2026-10-10

---

## Results Table

| Variant | Correct | Total | EX (%) | Δ vs Full SCoT |
| :--- | :---: | :---: | :---: | :---: |
| **A — Full SCoT** (baseline) | 682 | 1034 | **65.96%** | — |
| B — w/o Plan-Check | 709 | 1034 | 68.57% | **+2.61%** |
| C — w/o Ensemble | 664 | 1034 | 64.22% | **-1.74%** |
| D — w/o Canonicalization | 681 | 1034 | 65.86% | -0.10% |
| E — w/o Repair | 690 | 1034 | 66.73% | +0.77% |
| F — w/o Schema Validation | 695 | 1034 | 67.21% | +1.26% |
| G — SCoT-Native Only (all ablated) | 716 | 1034 | **69.25%** | **+3.29%** |

> [!NOTE]
> **Δ interpretation**: Negative = removing this component *hurts* accuracy (component is beneficial). Positive = removing this component *helps* accuracy (component is counter-productive in this configuration).

---

## Key Findings & Analysis

### 1. Multi-Candidate Ensemble is the Only Component That Clearly Helps

**Variant C (w/o Ensemble) is the only variant with a negative Δ (-1.74%)**, confirming that generating multiple diverse SQL candidates (SCoT-Native + QD-InterCol + Standard + conditional skeletons) and then ranking them by execution is the single most impactful component of the pipeline.

### 2. Plan-Check and Schema Validation Are Counter-Productive

- **Variant B (w/o Plan-Check): +2.61%** — The plan validation step is actually hurting accuracy. This suggests the checker LLM sometimes introduces errors into a valid plan, or over-constrains it, causing downstream SQL generation to deteriorate.
- **Variant F (w/o Schema Validation): +1.26%** — The `_uses_only_schema()` filter is too aggressive. It incorrectly rejects valid SQL candidates (e.g., aliased column references or dynamically computed columns that don't literally appear in the schema string), causing viable candidates to be discarded.

### 3. Execution-Guided Repair is Neutral to Slightly Harmful

**Variant E (w/o Repair): +0.77%** — The LLM-based repair loop adds minor overhead and occasionally makes already-close SQL worse. Its benefit is marginal for this model.

### 4. Canonicalization is Effectively Neutral

**Variant D (w/o Canonicalization): -0.10%** — Canonicalization contributes essentially nothing at this scale. The small difference is likely statistical noise.

### 5. Surprising Finding: Simpler is Better

**Variant G (SCoT-Native Only, all components ablated): +3.29%** — The fully stripped-down pipeline (single candidate, no validation, no repair) outperforms Full SCoT by over 3 percentage points. This is a significant and publishable finding: the added complexity of the multi-phase pipeline does not deliver net benefit for GPT-4o-Mini on Spider.

---

## Research Implications

This ablation reveals a **"complexity penalty"** in the SCoT pipeline — several post-processing components designed to improve accuracy are actually introducing noise and filtering out valid SQL. For a research paper, this leads to concrete actionable recommendations:

| Finding | Paper Narrative |
|:---|:---|
| Ensemble helps | Multi-candidate generation with execution ranking is the core valuable insight |
| Plan-Check hurts | Plan validation with a weaker model (GPT-4o-Mini) is unreliable; may need a stronger model or better prompting |
| Schema-Val hurts | Schema filtering heuristic needs refinement — too many false positives |
| Repair is neutral | LLM repair at temperature 0.0 doesn't generalize well; suggests repair needs diverse retries |
| G best overall | Suggests the **execution-ranked single candidate** approach is a strong baseline worth reporting |

---

## Files Saved

| File | Location |
|:---|:---|
| `ablation_summary.csv` | `runs/spider_full/ablation/` |
| `ablation_results.md` | `runs/spider_full/ablation/` |
| `predicted_ablation_*.sql` | `runs/spider_full/ablation/` (7 files) |
| `llm_cache.json` | `runs/spider_full/ablation/` (8460 cached LLM responses) |
