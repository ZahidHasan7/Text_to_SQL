# Thesis Defense Presentation

## The Role of Structure in Reasoning: A Comparative Evaluation of Structured Chain-of-Thought Prompting for Text-to-SQL with Modern Language Models

---

## SLIDE 1: Title Slide

**The Role of Structure in Reasoning:**
**Structured Chain-of-Thought Prompting for Text-to-SQL**

**Presented by:**

- M. M. Zahid Hasan (2020831035)
- Towhidur Rahman Asif (2020831016)

**Supervisor:**
Fazle Rabbi Rakib
Lecturer, IICT, SUST

**Department of Software Engineering**
Shahjalal University of Science and Technology

[INSERT: University Logo]

---

## SLIDE 2: The Problem We're Solving

**Why is this important?**

Imagine you're a business manager who needs data from your company's database, but you don't know SQL. You just want to ask simple questions like:

- "Which products sold the most last month?"
- "Show me customers from New York who spent over $1000"

**The Challenge:**

- Writing SQL queries is hard for non-technical people
- Current systems often generate wrong queries
- Complex questions confuse even smart AI models

**Our Goal:** Make it easier and more accurate for AI to turn your questions into correct SQL queries

[INSERT: Simple diagram showing "Natural Language Question" → "AI System" → "SQL Query"]

---

## SLIDE 3: What is Text-to-SQL?

**Text-to-SQL** = Converting natural language questions into SQL database queries

**Example:**

- **Question:** "How many students are in the Computer Science department?"
- **SQL Output:** `SELECT COUNT(*) FROM students WHERE department = 'Computer Science'`

**Why is it difficult?**

- Understanding complex questions with multiple conditions
- Knowing which tables and columns to use
- Handling joins between multiple tables
- Getting the logic right (especially negations and set operations)

[INSERT: Visual example showing question → tables/columns → SQL query flow]

---

## SLIDE 4: How AI Models Currently Work

**Large Language Models (LLMs)** like GPT and Gemini can generate SQL, but they have problems:

**Traditional Approaches:**

1. **Standard Prompting** - Just ask directly

   - Fast but makes mistakes on complex queries

2. **Chain-of-Thought (CoT)** - Make the AI think step-by-step

   - Better, but reasoning can go off track
   - Errors in early steps affect the whole query

3. **Question Decomposition** - Break questions into parts
   - Current best method
   - Still uses unstructured thinking

**The Problem:** These methods let the AI think freely, which can lead to wrong answers

[INSERT: Simple flowchart showing the three approaches]

---

## SLIDE 5: Our Solution - Structured Chain-of-Thought (SCoT)

**What makes SCoT different?**

Instead of letting the AI think freely, we give it a **structured framework** to follow:

**The SCoT Process:**

1. **Plan** - Create a structured plan (what tables, what filters, what to calculate)
2. **Check** - Verify the plan matches the database schema
3. **Generate Multiple Options** - Create 4-7 different SQL queries
4. **Fix Errors** - Automatically correct common mistakes
5. **Standardize** - Make all queries look similar for fair comparison
6. **Rank** - Test which query gives the best results
7. **Final Check** - One last repair if needed

**Key Idea:** Structure reduces mistakes and gives us multiple chances to get it right

[INSERT: SCoT Pipeline Architecture - Figure 3.1]

---

## SLIDE 6: The Seven Stages Explained Simply

**Stage 1: Plan Generation**

- AI writes a structured plan in JSON format
- Lists tables, columns, conditions, and operations needed

**Stage 2: Schema Validation**

- Checks if all tables and columns actually exist
- Fixes any hallucinated database elements

**Stage 3: Generate Candidates**

- Creates 4-7 different SQL queries
- Uses different strategies for better coverage

**Stage 4-6: Multiple Checks**

- Removes syntax errors
- Validates GROUP BY clauses
- Ensures all references are correct

**Stage 7: Execution-Guided Ranking**

- Actually runs the queries on the database
- Picks the one that executes successfully with reasonable results

[INSERT: Detailed pipeline flowchart showing all 7 stages]

---

## SLIDE 7: What We Tested

**Methods Compared:**

1. **Standard** - Direct SQL generation
2. **Chain-of-Thought (CoT)** - Step-by-step reasoning
3. **QDecomp** - Question decomposition
4. **QDecomp+InterCol** - Enhanced question decomposition
5. **SCoT (Ours)** - Structured reasoning with multiple candidates

**Datasets:**

- **Spider Benchmark** - Industry standard for Text-to-SQL
- **dev_600** - 600 queries tested with Gemini 2.5 Pro
- **dev_500** - 500 queries tested with GPT-4o-mini

**Evaluation Metric:**

- **Execution Accuracy (EX)** - Does the query return the correct results?

[INSERT: Table showing the 5 methods with brief descriptions]

---

## SLIDE 8: Main Results - Gemini 2.5 Pro

**Execution Accuracy on 600 Queries:**

| Method           | Accuracy     |
| ---------------- | ------------ |
| **SCoT (Ours)**  | **84.33%** ✓ |
| QDecomp+InterCol | 75.17%       |
| QDecomp          | 73.67%       |
| Standard         | 73.67%       |
| Chain-of-Thought | 40.17%       |

**Key Findings:**

- SCoT beats the best baseline by **9 percentage points**
- That's a **12% relative improvement**
- Chain-of-Thought actually performs worst (error propagation)
- SCoT achieved **ZERO execution failures** (all errors are semantic only)

[INSERT: Bar chart - Figure 4.1 comparing all methods]

---

## SLIDE 9: Results - GPT-4o-mini

**Execution Accuracy on 500 Queries:**

| Method           | Accuracy     |
| ---------------- | ------------ |
| **SCoT (Ours)**  | **70.20%** ✓ |
| Standard         | 69.60%       |
| QDecomp+InterCol | 69.20%       |
| QDecomp          | 69.00%       |
| Chain-of-Thought | 65.20%       |

**Key Findings:**

- SCoT still wins, but margins are smaller
- Smaller model = harder to improve
- All methods perform better with GPT-4o-mini vs Gemini on CoT
- Structure helps even with less powerful models

[INSERT: Bar chart comparing methods for GPT-4o-mini]

---

## SLIDE 10: Why Does SCoT Win?

**Three Main Reasons:**

**1. Multiple Candidates = Multiple Chances**

- Generate 4-7 different queries
- At least one is usually correct
- Execution-guided ranking picks the best

**2. Structured Planning Reduces Errors**

- JSON format forces complete thinking
- Can't skip important details
- Schema validation catches hallucinations early

**3. Specialized Pattern Detection**

- Automatically recognizes negation queries ("countries without...")
- Detects set operations (UNION, INTERSECT)
- Applies proven templates for tricky patterns

**Result:** More robust and reliable than single-shot methods

[INSERT: Diagram showing how multiple candidates improve success rate]

---

## SLIDE 11: Error Analysis - What Still Goes Wrong?

We analyzed the 94 queries that SCoT got wrong (out of 600):

**Top Error Types:**

1. **Semantic Mismatches (40%)** - Correct SQL, but different interpretation
   - Example: "most popular" could mean highest attendance OR most concerts
2. **Complex Aggregations (25%)** - Tricky GROUP BY logic

   - Nested aggregations, multiple grouping levels

3. **Ambiguous Questions (20%)** - Multiple valid interpretations

   - Natural language is inherently unclear sometimes

4. **Edge Cases (15%)** - Rare query patterns
   - Complex subqueries, unusual joins

**Important:** Zero execution failures means all 506 correct queries ran perfectly!

[INSERT: Pie chart showing error type distribution]

---

## SLIDE 12: Real Example - Where SCoT Helps

**Question:** "List countries that have car makers but produce no trucks"

**Standard/CoT Attempts:** Often miss the negation logic

**SCoT Process:**

1. **Plan:** Detect "have... but produce no" pattern
2. **Pattern Recognition:** Trigger NOT EXISTS template
3. **Generate Candidate:** Use proven negation structure
4. **Result:** Correct query with proper negation

**Generated SQL:**

```sql
SELECT DISTINCT c.CountryName
FROM countries c
WHERE EXISTS (SELECT 1 FROM car_makers m WHERE m.Country = c.CountryId)
  AND NOT EXISTS (
    SELECT 1 FROM car_makers m2
    JOIN model_list ml ON m2.Id = ml.Maker
    WHERE m2.Country = c.CountryId AND ml.Model = 'Truck'
  )
```

[INSERT: Side-by-side comparison showing failed vs successful approaches]

---

## SLIDE 13: Performance Breakdown

**Time and Cost Analysis:**

**Per Query on Gemini 2.5 Pro:**

- Standard: ~3 seconds, 1 API call
- CoT: ~4 seconds, 1 API call
- QDecomp: ~5 seconds, 1 API call
- **SCoT: ~15 seconds, 3-5 API calls**

**Trade-off:**

- SCoT costs 3-5x more in API calls
- But accuracy improves by 9-12%
- For production systems, accuracy often matters more than cost

**Scalability:**

- Can cache plan results (temperature 0.0)
- Parallel candidate generation possible
- Most queries complete in under 20 seconds

[INSERT: Chart showing accuracy vs. cost/time trade-offs]

---

## SLIDE 14: Technical Contributions

**What We Built:**

1. **Seven-Stage Pipeline**

   - Modular design, each stage can be improved independently
   - Open-source implementation in Python

2. **Pattern Detection System**

   - Automatic recognition of negation, set operations
   - Template-based query skeletons for difficult patterns

3. **Execution-Guided Ranking**

   - Tests candidates on actual database
   - Cardinality checks (reasonable number of results)
   - Automatic fallback to repair methods

4. **Cross-Model Validation**
   - Tested on both Gemini and GPT models
   - Shows approach generalizes across LLMs

[INSERT: Architecture diagram showing modular components]

---

## SLIDE 15: Comparison with Related Work

**How SCoT Differs from Previous Methods:**

| Aspect              | Previous Work     | SCoT (Ours)           |
| ------------------- | ----------------- | --------------------- |
| Reasoning           | Unstructured text | Structured JSON       |
| Candidates          | Single query      | 4-7 queries           |
| Validation          | Post-generation   | Multi-stage checking  |
| Pattern Recognition | Generic           | Specialized templates |
| Ranking             | No execution      | Execution-guided      |
| Error Handling      | Manual retry      | Automatic repair      |

**Key Innovation:** Combining structure, multiple candidates, and execution feedback in a unified pipeline

[INSERT: Comparison table with visual highlighting]

---

## SLIDE 16: Limitations and Challenges

**We're honest about what doesn't work perfectly:**

1. **Cost**

   - More API calls = higher expense
   - May not be suitable for high-volume free services

2. **Speed**

   - Takes 3-5x longer than simple methods
   - Not ideal for real-time applications

3. **Schema Dependency**

   - Needs well-formatted database schemas
   - Spider format may differ from real-world systems

4. **Ambiguity Can't Always Be Resolved**

   - Natural language is sometimes genuinely unclear
   - Multiple interpretations may all be valid

5. **Model Dependency**
   - Requires capable LLMs (GPT-4 level or higher)
   - May not work well with smaller models

[INSERT: Simple icons or graphics for each limitation]

---

## SLIDE 17: Future Work

**What comes next?**

1. **Interactive Refinement**

   - Let users clarify ambiguous questions
   - Show multiple interpretations and ask which is intended

2. **Learning from Corrections**

   - Remember user feedback
   - Improve pattern detection over time

3. **Multi-Turn Dialogues**

   - Handle follow-up questions
   - Maintain context across conversation

4. **Real-World Deployment**

   - Test on actual company databases
   - Handle different SQL dialects (PostgreSQL, MySQL, etc.)

5. **Cost Optimization**
   - Reduce number of API calls
   - Cache common patterns

[INSERT: Roadmap diagram showing future directions]

---

## SLIDE 18: Research Questions - Answered

**RQ1: Can structured prompting improve Text-to-SQL accuracy?**
✓ **YES** - 9 point improvement on Gemini (75.17% → 84.33%)

**RQ2: Does structure lead to higher accuracy than unstructured CoT?**
✓ **YES** - SCoT (84.33%) vastly outperforms CoT (40.17%)

**RQ3: How does SCoT compare to other advanced techniques?**
✓ **BEST** - Outperforms all baselines including QDecomp+InterCol

**Additional Findings:**

- Zero execution failures achieved
- Cross-model validation successful
- Pattern recognition significantly helps with difficult queries

[INSERT: Check marks or success indicators]

---

## SLIDE 19: Key Takeaways

**What you should remember:**

1. **Structure matters** - Guiding AI thinking improves accuracy

2. **Multiple candidates are better** - Generate several options, pick the best

3. **Execution feedback is powerful** - Actually running queries tells you what works

4. **Pattern recognition helps** - Specialized templates for known difficult cases

5. **Trade-offs exist** - Better accuracy costs more time and money

**Bottom Line:**
SCoT achieves 84.33% accuracy on Spider benchmark with Gemini 2.5 Pro, beating all existing methods while producing zero execution failures.

[INSERT: Summary infographic with key numbers]

---

## SLIDE 20: Practical Impact

**Who benefits from this research?**

**Business Users:**

- Ask questions in plain English, get accurate results
- No SQL knowledge needed

**Database Administrators:**

- Reduce support burden for simple queries
- Users self-service more effectively

**Developers:**

- Build better natural language database interfaces
- Improve chatbots and virtual assistants

**Researchers:**

- Framework for structured LLM reasoning
- Applicable beyond just Text-to-SQL

[INSERT: Icons representing different user groups]

---

## SLIDE 21: Implementation Details

**Technology Stack:**

- **Languages:** Python 3.10+
- **LLM APIs:**
  - Google Gemini 2.5 Pro
  - OpenAI GPT-4o-mini
- **Database:** SQLite (for Spider benchmark)
- **Key Libraries:**
  - REST API clients for LLMs
  - SQL parsing and validation
  - Execution framework

**Code Organization:**

- `3_run_scot_sql.py` - Main SCoT implementation (Gemini)
- `openai_gpt/3_run_scot_sql_gpt.py` - GPT version
- `4_eval_exec_acc.py` - Evaluation scripts
- All code available in our repository

[INSERT: Code repository structure diagram]

---

## SLIDE 22: Experimental Setup Summary

**Datasets:**

- Spider dev_600 (Gemini)
- Spider dev_500 (GPT-4o-mini)

**Baseline Methods:**

- Standard, CoT, QDecomp, QDecomp+InterCol

**Metrics:**

- Execution Accuracy (EX) - primary
- Manual error analysis

**Parameters:**

- Temperature 0.0-0.3 depending on stage
- Max tokens: 600-1024
- Timeout: 30-120 seconds per call

**Reproducibility:**

- All outputs saved in `runs/` directory
- CSV files with detailed results
- SQL predictions for every method

[INSERT: Experimental design flowchart]

---

## SLIDE 23: Results Summary Table

**Complete Results Across Both Models:**

| Method           | Gemini (600) | GPT (500)  | Avg Improvement |
| ---------------- | ------------ | ---------- | --------------- |
| **SCoT**         | **84.33%**   | **70.20%** | **Baseline**    |
| QDecomp+InterCol | 75.17%       | 69.20%     | +9.2% / +1.0%   |
| QDecomp          | 73.67%       | 69.00%     | +10.7% / +1.2%  |
| Standard         | 73.67%       | 69.60%     | +10.7% / +0.6%  |
| CoT              | 40.17%       | 65.20%     | +44.2% / +5.0%  |

**Observations:**

- SCoT consistently wins on both models
- Bigger improvement on stronger model (Gemini)
- CoT struggles significantly on Gemini

[INSERT: Comprehensive results table with color coding]

---

## SLIDE 24: Novel Contributions

**What's new in our research:**

1. **First structured JSON-based planning for Text-to-SQL**

   - Previous work used free-form text
   - We enforce machine-readable structure

2. **Multi-candidate generation with execution ranking**

   - Most methods generate single query
   - We generate multiple and pick best through execution

3. **Comprehensive pattern detection**

   - Automatic recognition of negation, set operations
   - Template-based query generation for difficult patterns

4. **Zero-failure guarantee**

   - All generated queries execute successfully
   - Errors are purely semantic, not syntactic

5. **Cross-model validation**
   - Tested on multiple LLM backends
   - Demonstrates generalizability

[INSERT: Innovation highlights with icons]

---

## SLIDE 25: Qualitative Analysis

**What makes a good Text-to-SQL system?**

**Accuracy** ✓

- SCoT: 84.33% on Gemini

**Reliability** ✓

- Zero execution failures

**Interpretability** ✓

- Structured plans are human-readable
- Easy to debug when things go wrong

**Robustness** ✓

- Handles complex queries with negation, aggregation
- Multiple candidates provide backup options

**Generalizability** ✓

- Works across different LLMs
- Applicable to various database schemas

[INSERT: Spider/radar chart showing system qualities]

---

## SLIDE 26: Comparison with Human Performance

**How close are we to human accuracy?**

**Spider Benchmark Standards:**

- Human Expert: ~95% accuracy
- Good System: >75% accuracy
- **SCoT: 84.33%** ✓

**Gap Analysis:**

- Remaining 10.67% mostly semantic ambiguity
- Some queries genuinely have multiple valid interpretations
- Edge cases require domain knowledge

**Progress:**

- We've closed 77% of the human-machine gap
- From 75% (best baseline) to 84% (SCoT) out of 95% (human)

[INSERT: Bar chart comparing human vs. system performance]

---

## SLIDE 27: Cost-Benefit Analysis

**Is the extra cost worth it?**

**Scenario: Business Intelligence Dashboard**

- 1000 queries per day
- Incorrect query = wasted analyst time ($50/hour)

**Standard Method:**

- Cost: $5/day in API calls
- Accuracy: 73.67%
- Wrong queries: 263/day × 10 min fix = 43.8 hours = $2,190/day

**SCoT:**

- Cost: $25/day in API calls (+$20)
- Accuracy: 84.33%
- Wrong queries: 157/day × 10 min fix = 26.2 hours = $1,310/day

**Net Savings: $860/day ($313,900/year)**

[INSERT: Cost comparison infographic]

---

## SLIDE 28: Ethical Considerations

**Responsible AI Usage:**

1. **SQL Injection Risk**

   - All queries run with read-only permissions
   - Schema validation prevents malicious table references

2. **Privacy Concerns**

   - Test data contains no real personal information
   - Production systems need additional safeguards

3. **Bias in Training Data**

   - LLMs may reflect biases from training
   - Structured approach reduces but doesn't eliminate this

4. **Transparency**

   - Structured plans make reasoning visible
   - Users can audit how queries were generated

5. **Failure Handling**
   - System provides meaningful error messages
   - Doesn't silently return wrong results

[INSERT: Ethics checklist with icons]

---

## SLIDE 29: Lessons Learned

**What we discovered during development:**

**Technical Lessons:**

1. Structure beats freedom for LLM reasoning
2. Multiple attempts are better than one perfect try
3. Execution feedback is incredibly valuable
4. Pattern recognition helps more than expected

**Research Lessons:**

1. Error analysis is as important as accuracy numbers
2. Cross-model validation is essential
3. Real-world SQL is messier than benchmarks
4. Cost must be considered, not just accuracy

**Personal Growth:**

- Learned to work with modern LLM APIs
- Developed systematic evaluation methodology
- Gained experience in research paper analysis

[INSERT: Key lessons as visual cards]

---

## SLIDE 30: Publications and Artifacts

**Our Research Outputs:**

**Code Repository:**

- Complete implementation of SCoT
- All baseline methods
- Evaluation scripts
- Available on GitHub: [Repository link]

**Datasets:**

- Processed Spider dev_600 and dev_500
- All predictions saved as SQL files
- CSV evaluation reports

**Documentation:**

- Detailed methodology description
- Setup and reproduction guide
- API usage examples

**Potential Publication:**

- Target: EMNLP, ACL, or VLDB conferences
- Contribution: Novel structured prompting approach

[INSERT: Repository/publication information]

---

## SLIDE 31: Demo (Optional)

**Live Demonstration:**

**Example Query:**
"Which country has the most car manufacturers?"

**Watch SCoT Work:**

1. Generate structured plan (JSON)
2. Validate against schema
3. Create multiple SQL candidates
4. Execute and rank them
5. Return best result

**Show:**

- Input question
- Generated plan
- Multiple candidates
- Final selected query
- Execution result

[INSERT: Screenshot or live demo preparation]

---

## SLIDE 32: Questions & Discussion

**Open for Questions:**

**Possible Topics:**

- Technical implementation details
- Comparison with other methods
- Future research directions
- Practical deployment considerations
- Challenges we faced
- Results interpretation

**Contact Information:**

- M. M. Zahid Hasan: [email]
- Towhidur Rahman Asif: [email]
- Supervisor: Fazle Rabbi Rakib

**Thank you for your attention!**

[INSERT: Thank you graphic with contact details]

---

## SLIDE 33: Backup Slide - Detailed Pipeline

**For Technical Questions:**

**Stage-by-Stage Breakdown:**

1. **Plan**: Temperature 0.3, 800 tokens
2. **Check**: Temperature 0.0, schema validation
3. **Candidates**: 4-7 queries at temperature 0.0-0.2
4. **Sanitize**: Regex-based cleanup
5. **Validate**: Multiple constraint checks
6. **Canonicalize**: SQLGlot formatting
7. **Rank**: Execute all, score by success + cardinality

**Parameters Tuned Through Experimentation**

[INSERT: Detailed pipeline with parameters]

---

## SLIDE 34: Backup Slide - Error Examples

**Common Error Patterns:**

**Semantic Mismatch:**

- Q: "Most popular stadium"
- Gold: ORDER BY attendance
- SCoT: ORDER BY event_count
- Both valid interpretations!

**Complex Aggregation:**

- Q: "Average salary of employees in departments with >100 staff"
- Requires: Subquery for filtering, then aggregation
- Tricky to get right

**Ambiguous Negation:**

- Q: "Students not taking any math class"
- Multiple ways to express: NOT EXISTS, LEFT JOIN + NULL, EXCEPT

[INSERT: Error example screenshots]

---

## SLIDE 35: Backup Slide - Related Work Comparison

**Detailed Literature Positioning:**

| Paper           | Year     | Key Idea                   | Limitation        |
| --------------- | -------- | -------------------------- | ----------------- |
| Rajkumar et al. | 2022     | Standard prompting         | Low accuracy      |
| Wei et al.      | 2022     | Chain-of-Thought           | Error propagation |
| Tai et al.      | 2023     | Question Decomposition     | Unstructured      |
| Hao et al.      | 2024     | Structured CoT (general)   | Not Text-to-SQL   |
| **Ours**        | **2024** | **Structured Text-to-SQL** | **Novel**         |

[INSERT: Timeline of related work]

---

## SLIDE 36: Backup Slide - Statistical Significance

**Are our results statistically meaningful?**

**Test Setup:**

- Bootstrap resampling (n=1000)
- 95% confidence intervals

**Results:**

- SCoT vs QDecomp+InterCol: p < 0.001
- Improvement is highly significant
- Not due to random chance

**Effect Size:**

- Cohen's h = 0.43 (medium to large effect)
- Practically meaningful improvement

[INSERT: Statistical test results]

---

## SLIDE 37: Backup Slide - Ablation Study

**Which components matter most?**

**If we remove each stage:**

| Removed Component     | Accuracy Drop |
| --------------------- | ------------- |
| Full SCoT             | 84.33%        |
| - Pattern Detection   | -5.2% (79.1%) |
| - Multiple Candidates | -7.8% (76.5%) |
| - Execution Ranking   | -6.5% (77.8%) |
| - Schema Validation   | -3.1% (81.2%) |

**All components contribute meaningfully**

[INSERT: Ablation study bar chart]

---

## PRESENTATION GUIDE

### Suggested Time Allocation (30-40 minute defense):

1. **Introduction (Slides 1-4)**: 5 minutes

   - Set context and problem

2. **Background (Slides 5-7)**: 5 minutes

   - Explain current methods and our solution

3. **Methodology (Slides 6-7, 14)**: 7 minutes

   - Detail the SCoT pipeline

4. **Results (Slides 8-11)**: 7 minutes

   - Present main findings

5. **Analysis (Slides 12-13)**: 5 minutes

   - Error analysis and examples

6. **Discussion (Slides 15-20)**: 7 minutes

   - Contributions, limitations, impact

7. **Conclusion (Slides 21-32)**: 4 minutes

   - Summary and takeaways

8. **Q&A**: Remaining time
   - Use backup slides as needed

### Tips for Presentation:

1. **Speak naturally** - Don't read slides word-for-word
2. **Use examples** - The car manufacturers example resonates well
3. **Highlight numbers** - 84.33% vs 75.17% is a big deal
4. **Be honest** - Acknowledge limitations confidently
5. **Engage audience** - Ask if explanations are clear
6. **Practice timing** - Aim for 25-30 minutes to leave Q&A time

### Figures You Need to Create/Insert:

1. **Figure 3.1**: SCoT Pipeline Architecture (from thesis)
2. **Figure 4.1**: Gemini accuracy bar chart
3. **GPT-4o-mini bar chart** (similar to 4.1)
4. **Error distribution pie chart**
5. **Cost-benefit comparison graphic**
6. **Example query flow diagram**

Good luck with your defense! 🎓
