# SCoT Diagnostics Report (All Backends)

## Backend: llama

### Phase 1: Stage-Level Failure Rates
- Plan missing/unparseable: 0 / 1034
- Plan-check unparseable: 0 / 1034
- Plans changed by check: 422 (EX if changed: 56.2%; if unchanged: 70.8%)
- Queries with 0 candidates: 0
- Queries with < 4 candidates: 821
- Queries where Stage 7 filtered ALL candidates: 2

### Phase 2: Oracle vs Selected Accuracy
- SCoT Selected Accuracy: 64.80%
- Oracle (Raw Cands): 80.46%
- Oracle (Post-Repair): 78.14%
- Ranking Gap (Oracle Post-Repair minus Selected): 13.35pp (151 queries)

### Phase 3: Repair Regression (Stages 4-6)
- Harmful flips (Correct -> Incorrect): 151
- Beneficial flips (Incorrect -> Correct): 100
- Net effect: -51 queries

### Phase 4: Loss Attribution (vs QD+InterCol)
For queries where QD+InterCol was correct but SCoT failed:
- **Ranking Error (Stage 7 selected wrong cand)**: 117
- **Generation Failure (No LLM cand correct)**: 21
- **Repair Damage (Stages 4-6 broke correct cand)**: 15
- **Pipeline Failure (empty/unparseable)**: 2

---

## Backend: haiku

### Phase 1: Stage-Level Failure Rates
- Plan missing/unparseable: 0 / 1034
- Plan-check unparseable: 0 / 1034
- Plans changed by check: 426 (EX if changed: 60.8%; if unchanged: 72.9%)
- Queries with 0 candidates: 0
- Queries with < 4 candidates: 821
- Queries where Stage 7 filtered ALL candidates: 2

### Phase 2: Oracle vs Selected Accuracy
- SCoT Selected Accuracy: 67.89%
- Oracle (Raw Cands): 79.98%
- Oracle (Post-Repair): 77.27%
- Ranking Gap (Oracle Post-Repair minus Selected): 9.38pp (108 queries)

### Phase 3: Repair Regression (Stages 4-6)
- Harmful flips (Correct -> Incorrect): 117
- Beneficial flips (Incorrect -> Correct): 43
- Net effect: -74 queries

### Phase 4: Loss Attribution (vs QD+InterCol)
For queries where QD+InterCol was correct but SCoT failed:
- **Ranking Error (Stage 7 selected wrong cand)**: 80
- **Repair Damage (Stages 4-6 broke correct cand)**: 19
- **Generation Failure (No LLM cand correct)**: 11
- **Pipeline Failure (empty/unparseable)**: 1

---

## Backend: gemini

### Phase 1: Stage-Level Failure Rates
- Plan missing/unparseable: 1 / 1034
- Plan-check unparseable: 0 / 1034
- Plans changed by check: 136 (EX if changed: 80.1%; if unchanged: 77.1%)
- Queries with 0 candidates: 0
- Queries with < 4 candidates: 821
- Queries where Stage 7 filtered ALL candidates: 2

### Phase 2: Oracle vs Selected Accuracy
- SCoT Selected Accuracy: 77.47%
- Oracle (Raw Cands): 83.46%
- Oracle (Post-Repair): 84.14%
- Ranking Gap (Oracle Post-Repair minus Selected): 6.67pp (71 queries)

### Phase 3: Repair Regression (Stages 4-6)
- Harmful flips (Correct -> Incorrect): 48
- Beneficial flips (Incorrect -> Correct): 66
- Net effect: 18 queries

### Phase 4: Loss Attribution (vs QD+InterCol)
For queries where QD+InterCol was correct but SCoT failed:
- **Ranking Error (Stage 7 selected wrong cand)**: 43
- **Generation Failure (No LLM cand correct)**: 12
- **Repair Damage (Stages 4-6 broke correct cand)**: 5

---

## Backend: gpt4o

### Phase 1: Stage-Level Failure Rates
- Plan missing/unparseable: 0 / 1034
- Plan-check unparseable: 0 / 1034
- Plans changed by check: 638 (EX if changed: 56.1%; if unchanged: 52.3%)
- Queries with 0 candidates: 0
- Queries with < 4 candidates: 791
- Queries where Stage 7 filtered ALL candidates: 3

### Phase 2: Oracle vs Selected Accuracy
- SCoT Selected Accuracy: 54.64%
- Oracle (Raw Cands): 76.02%
- Oracle (Post-Repair): 73.89%
- Ranking Gap (Oracle Post-Repair minus Selected): 19.25pp (214 queries)

### Phase 3: Repair Regression (Stages 4-6)
- Harmful flips (Correct -> Incorrect): 132
- Beneficial flips (Incorrect -> Correct): 110
- Net effect: -22 queries

### Phase 4: Loss Attribution (vs QD+InterCol)
For queries where QD+InterCol was correct but SCoT failed:
- **Ranking Error (Stage 7 selected wrong cand)**: 175
- **Generation Failure (No LLM cand correct)**: 17
- **Repair Damage (Stages 4-6 broke correct cand)**: 13

---

## Phase 5: Cross-Backend Loss Analysis

| Backend | Pipeline Failure | Generation Failure | Repair Damage | Ranking Error |
|:---|:---:|:---:|:---:|:---:|
| llama | 2 | 21 | 15 | 117 |
| haiku | 1 | 11 | 19 | 80 |
| gemini | 0 | 12 | 5 | 43 |
| gpt4o | 0 | 17 | 13 | 175 |
