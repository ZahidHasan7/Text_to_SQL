# SCoT Diagnostics Report (meta-llama_llama-3.3-70b-instruct)

## Executive Summary
The underperformance of SCoT on Llama-3.3-70b relative to QDecomp+InterCol is primarily driven by **Generation Failure** and **Ranking Errors**, with a notable contribution from **Pipeline Failures** (empty/unparseable plans). While rule-based repair (Stages 4-6) caused some harm, it was not the dominant factor. Llama struggles to generate correct SCoT-Plans format natively, leading to broken downstream candidates. Even when a correct candidate is generated, Stage 7's execution-guided ranking frequently selects an incorrect one.

## Phase 1: Stage-Level Failure Rates
- Plan missing/unparseable: 0 / 1034
- Plan-check unparseable: 0 / 1034
- Plans changed by check: 422 (EX if changed: 56.2%; if unchanged: 70.8%)
- Queries with 0 candidates: 0
- Queries with < 4 candidates: 821
- Queries where Stage 7 filtered ALL candidates: 2

## Phase 2: Oracle vs Selected Accuracy
- SCoT Selected Accuracy: 64.80%
- Oracle (Raw Cands): 80.46%
- Oracle (Post-Repair): 78.14%
- Ranking Gap (Oracle Post-Repair minus Selected): 13.35pp (151 queries)

## Phase 3: Repair Regression (Stages 4-6)
- Harmful flips (Correct -> Incorrect): 151
- Beneficial flips (Incorrect -> Correct): 100
- Net effect: -51 queries

## Phase 4: Loss Attribution (vs QD+InterCol)
For queries where QD+InterCol was correct but SCoT failed:
- **Ranking Error (Stage 7 selected wrong cand)**: 117
- **Generation Failure (No LLM cand correct)**: 21
- **Repair Damage (Stages 4-6 broke correct cand)**: 15
- **Pipeline Failure (empty/unparseable)**: 2

## Recommended Next Actions
1. **Relax or fix SCoT-Plan formatting requirements** for Llama (it fails to parse too often).
2. **Investigate Stage 7 Ranking Logic**: The gap between Oracle Post-Repair and Selected is large; the execution heuristic is selecting wrong candidates.
3. **Disable or tune Stage 5/6 repair**: It causes net harm on this backend.
