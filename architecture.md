# System Architecture & Pipeline Design: Redrob Candidate Ranker

This document details the system design, processing stages, and mathematical formulations for the candidate ranking pipeline. The pipeline is designed to process 100,000 candidate profiles against a Senior AI Engineer job description, running on a standard CPU within a 5-minute window.

---

## 1. High-Level Data Flow

The ranking pipeline operates as a **relevance-availability cascade**, similar to search ranking architectures used at Google and Meta. Rather than scoring all candidates on all dimensions (which is computationally expensive and prone to noise), the system filters out invalid or highly unavailable candidates first, then performs deep scoring on the remaining high-potential pool.

```
       [Raw Candidates (100K JSONL)]
                     │
                     ▼
          ┌─────────────────────┐
          │  1. Safety Filters  │ ──> Discards: Honeypots & IT-Service-Only
          └──────────┬──────────┘
                     │ (Remaining candidates: ~5K - 10K)
                     ▼
          ┌─────────────────────┐
          │  2. Technical Fit   │ ──> Scores skills, titles, descriptions
          └──────────┬──────────┘
                     │
                     ▼
          ┌─────────────────────┐
          │  3. Availability    │ ──> Modifies scores by response rate,
          └──────────┬──────────┘     notice period, location, recency
                     │
                     ▼
          ┌─────────────────────┐
          │ 4. Sorting & Output │ ──> Deterministic tie-break, generates
          └─────────────────────┘     reasoning, outputs top 100 CSV
```

---

## 2. Stage 1: Safety Filters (Honeypot & IT-Service Exclusions)

To protect the ranking from disqualified candidates and meet the honeypot threshold limit ($<10\%$ in the top 100), the system evaluates each candidate against three safety checkers. If a candidate triggers any of these checkers, they are assigned a score of `0` and immediately pruned.

### A. Honeypot Profiling Heuristics
Honeypots are synthetic profiles designed with impossible data patterns. The system flags a profile as a honeypot if it triggers any of the following:
1.  **Expert Skill Inflation**: The count of skills marked `"expert"` with `duration_months == 0` is $\ge 10$.
2.  **Job Duration Anomaly**: For any role in `career_history`:
    *   Let $D_{\text{calc}}$ be the calculated duration in months between `start_date` and `end_date` (or `2026-06-17` if `is_current` is true or `end_date` is null).
    *   Let $D_{\text{stated}}$ be the candidate's reported `duration_months`.
    *   If $|D_{\text{calc}} - D_{\text{stated}}| > 3$ months, the candidate is flagged.
3.  **Future Dates**: Any start or end date in career history that falls after the reference date `2026-06-17`.
4.  **Skill Duration Over-inflation**: Any individual skill where `duration_months` is greater than the total career experience (sum of all job durations) plus a 12-month grace period.

### B. IT Consulting Services Exclusion
The Job Description explicitly disqualifies candidates who have *only* worked at IT outsourcing/consulting firms. 
*   **Definition of IT Service Firms**: `["TCS", "Infosys", "Wipro", "Accenture", "Cognizant", "Capgemini", "L&T", "Larsen & Toubro", "Tech Mahindra", "Mindtree", "HCL"]` (case-insensitive substring matches).
*   **Rule**: If the candidate has $\ge 1$ job in their career history, and **every single job** is at one of these service firms, the candidate is disqualified.
*   *Note*: If a candidate is currently at a service firm but has prior product-company experience (e.g. Acme Corp, Pied Piper, Stark Industries, Zomato, etc.), they remain in the pipeline.

---

## 3. Stage 2: Technical & Experience Scoring (Relevance Fit)

For candidates passing Stage 1, we compute a raw **Relevance Fit Score** ($S_{\text{fit}} \in [0, 100]$):

$$S_{\text{fit}} = 0.50 \times S_{\text{skills}} + 0.30 \times S_{\text{experience}} + 0.20 \times S_{\text{context}}$$

### A. Technical Skills Score ($S_{\text{skills}}$)
To avoid keyword-stuffers, we do not simply count matching terms. We verify skill presence and apply a **Skills Trust Modifier**:
*   For each skill $s$ in the candidate's `skills` list, we define its raw weight $W_s$ based on keyword matching:
    *   **Core Retrieval/Vector DBs (Weight = 1.0)**: Pinecone, Milvus, FAISS, Qdrant, Weaviate, BGE, E5, sentence-transformers, embeddings, vector search, hybrid search, dense retrieval.
    *   **Ranking & Evaluation (Weight = 0.8)**: learning-to-rank, NDCG, MAP, MRR, ranking, hybrid search, Elasticsearch, FAISS.
    *   **Applied ML/NLP (Weight = 0.5)**: NLP, machine learning, deep learning, PyTorch, HuggingFace, fine-tuning.
*   **Trust Multiplier**:
    $$T_s = \min\left(1.0, \frac{\text{duration\_months}}{12}\right) \times \left(1.0 + \log_{10}(1 + \text{endorsements})\right)$$
*   **Proficiency Weight**: `expert` = 1.0, `advanced` = 0.8, `intermediate` = 0.5, `beginner` = 0.2.
*   The final $S_{\text{skills}}$ is the sum of $(W_s \times T_s \times \text{Proficiency})$ across matched skills, normalized to a maximum of 100.

### B. Experience Fit Score ($S_{\text{experience}}$)
The Job Description targets 5–9 years of experience, with a sweet spot of 6–8 years. We map the total reported `years_of_experience` ($Y$) using a trapezoidal membership function:
*   If $6.0 \le Y \le 8.0$: $S_{\text{experience}} = 100$
*   If $5.0 \le Y < 6.0$: $S_{\text{experience}} = 100 - (6.0 - Y) \times 40$ (smooth decay to 60 at 5 years)
*   If $8.0 < Y \le 9.0$: $S_{\text{experience}} = 100 - (Y - 8.0) \times 20$ (smooth decay to 80 at 9 years)
*   If $Y < 5.0$ or $Y > 9.0$: Scale down exponentially (heavy penalty for $<3$ or $>12$ years).

### C. Contextual Title & Description Alignment ($S_{\text{context}}$)
We check job titles and descriptions in `career_history` for active hands-on ranking/retrieval roles:
*   If the **current job title** contains `"Machine Learning"`, `"ML"`, `"AI"`, `"Search"`, `"Ranking"`, or `"Retrieval"`, candidate receives a major bonus (+30 points).
*   If recent job descriptions contain phrases like `"built search"`, `"deployed recommendation"`, `"optimized NDCG"`, `"vector indexing"`, candidate receives a bonus (+20 points).
*   If the headline or summary explicitly matches the founding-engineer profile, candidate receives +10 points.

---

## 4. Stage 3: Availability & Logistics Modifiers

A perfect-on-paper candidate who cannot be hired must be down-ranked. The final score is adjusted using multiplicative modifiers:

$$\text{Final Score} = S_{\text{fit}} \times M_{\text{activity}} \times M_{\text{notice}} \times M_{\text{location}}$$

### A. Activity Multiplier ($M_{\text{activity}}$)
Measures platform presence. If inactive, the candidate is likely passive.
*   Let $Days$ be the number of days between `last_active_date` and `2026-06-17`.
*   If $Days \le 30$: $M_{\text{activity}} = 1.0$
*   If $30 < Days \le 90$: $M_{\text{activity}} = 0.9$
*   If $90 < Days \le 180$: $M_{\text{activity}} = 0.7$
*   If $Days > 180$: $M_{\text{activity}} = 0.4$ (heavy decay)

### B. Notice Period Multiplier ($M_{\text{notice}}$)
Redrob prefers sub-30-day notice.
*   If `notice_period_days` $\le 30$: $M_{\text{notice}} = 1.0$
*   If $30 < \text{notice\_period\_days} \le 60$: $M_{\text{notice}} = 0.9$
*   If $60 < \text{notice\_period\_days} \le 90$: $M_{\text{notice}} = 0.75$
*   If `notice_period_days` $> 90$: $M_{\text{notice}} = 0.4$ (substantial penalty)

### C. Location Fit Multiplier ($M_{\text{location}}$)
Pune/Noida hybrid is preferred. Outside India is penalized due to lack of visa sponsorship.
*   If `country` is NOT `"India"` (or analogous matching for location):
    *   If `willing_to_relocate` is False: $M_{\text{location}} = 0.1$
    *   If `willing_to_relocate` is True: $M_{\text{location}} = 0.4$
*   If `country` is `"India"`:
    *   If `location` is Pune or Noida: $M_{\text{location}} = 1.0$
    *   If `location` is a Tier-1 city (Bangalore, Mumbai, Delhi, Gurgaon, Hyderabad) AND `willing_to_relocate` is True: $M_{\text{location}} = 0.95$
    *   If `location` is Tier-1 but `willing_to_relocate` is False: $M_{\text{location}} = 0.6$
    *   Other Indian cities: $M_{\text{location}} = 0.7$ if relocating, $0.5$ if not.

---

## 5. Stage 4: Post-Processing & Tie-Breaking

Once scores are computed:
1.  **Sorting**: The candidate list is sorted by `Final Score` descending.
2.  **Tie-Breaking**: If multiple candidates share the same final score, the rank order is broken deterministically by checking their `candidate_id` in alphabetical ascending order (e.g. `CAND_0000010` ranks ahead of `CAND_0000020`).
3.  **Top 100 Selection**: The top 100 candidates are sliced from the sorted list.
4.  **Reasoning Generation**: For each of the top 100, we assemble a fact-grounded reasoning sentence:
    *   *Formula*: `"{Title} with {Experience} years of experience; possesses verified skills in {Skill_1} and {Skill_2} with strong platform activity; notice period is {Notice} days."`
    *   This ensures 100% profile alignment (no hallucinations) and natural variation because it uses candidate-specific facts.

---

## 6. Pipeline Validation (CI/CD)

The pipeline is wrapped in `run_pipeline.py` which automatically runs the following validations:
*   Checks that the output file contains exactly 100 data rows and 1 header.
*   Checks that ranks are unique integers 1–100.
*   Verifies that scores are monotonically non-increasing.
*   Validates candidate IDs against the database.
*   Confirms the compute profile runs under 5 minutes on CPU.
