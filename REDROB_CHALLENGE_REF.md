# Redrob Hackathon — Complete Reference
> Auto-extracted from all challenge bundle files. Single source of truth for rules, schema, signals, and scoring.
> Last updated: 2026-06-20

---

## 1. THE JOB DESCRIPTION (What we're ranking against)

**Role:** Senior AI Engineer — Founding Team  
**Company:** Redrob AI (Series A)  
**Location:** Pune/Noida, India (Hybrid) | Open to Tier-1 relocation  
**Experience:** 5–9 years  

### Ideal Candidate Profile
- 6–8 years total, of which 4–5 are **applied ML/AI at product companies** (not services)
- Shipped at least one end-to-end **ranking, search, or recommendation system** to real users at scale
- Located in or **willing to relocate to Noida or Pune**
- Active on platform / clear signal of being in job market

### Skills — MUST HAVE
- Production embeddings-based retrieval (sentence-transformers, BGE, E5, OpenAI, etc.)
- Production vector DB / hybrid search (Pinecone, Weaviate, Qdrant, Milvus, FAISS, Elasticsearch)
- Strong Python + code quality
- Eval frameworks for ranking: NDCG, MRR, MAP, A/B testing

### Skills — NICE TO HAVE
- LLM fine-tuning (LoRA, QLoRA, PEFT)
- Learning-to-rank (XGBoost / neural)
- HR-tech / recruiting / marketplace exposure
- Distributed systems / large-scale inference
- Open-source ML contributions

### Explicit Disqualifiers (from JD — used for scoring, NOT hard filters)
1. Pure research only, no production deployment
2. "AI experience" = LangChain + OpenAI calls < 12 months, no pre-LLM history
3. Senior title but no production code written in last 18 months
4. **Only worked at IT consulting firms (TCS, Infosys, Wipro, Accenture, Cognizant, Capgemini, L&T, HCL, Tech Mahindra)** for ENTIRE career
5. Computer vision / speech / robotics primary — no NLP/IR exposure

### Explicit "Do Not Want" (from JD — signals for lower scoring)
- Title-chasers (switching every 1.5 years for promotions)
- Framework enthusiasts (LangChain tutorial-heavy, no systems thinking)
- Only consulting firm experience their whole career
- CV/speech/robotics-primary without NLP/IR crossover

### Hackathon-Specific Note from JD (Line 71–76)
> "The 'right answer' to this JD is not 'find candidates whose skills section contains the most AI keywords.' That's a trap."
> "The right answer involves reasoning about the gap between what the JD says and what it means."
> "A candidate whose title is 'Marketing Manager' is not a fit, no matter how perfect their skill list looks."
> "Weigh behavioral signals — a perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% response rate is not actually available."

---

## 2. SUBMISSION RULES (submission_spec.txt)

### Output Format
- **Exactly 100 rows** (+ 1 header), no more, no less
- Columns (in order): `candidate_id, rank, score, reasoning`
- `rank`: integers 1–100, each used **exactly once**
- `score`: float, **monotonically non-increasing** (score@rank1 ≥ score@rank2 ≥ ... ≥ score@rank100)
- Ties in score → break deterministically using `candidate_id` ascending
- All `candidate_id` values must exist in `candidates.jsonl`

### Compute Constraints (HARD LIMITS)
| Constraint | Limit |
|---|---|
| Total runtime | ≤ 5 minutes wall-clock |
| Memory | ≤ 16 GB RAM |
| Compute | CPU only — no GPU |
| Network | OFF — no external API calls |
| Disk | ≤ 5 GB intermediate state |

### What is NOT allowed during ranking
- Calling hosted LLM APIs (OpenAI, Anthropic, Cohere, Gemini)
- Using GPU
- Exceeding runtime/memory limits

---

## 3. EVALUATION PIPELINE (5 Stages)

| Stage | What Happens | What Gets You Eliminated |
|---|---|---|
| 1. Format Validation | Auto-validator on every submission | Any spec violation |
| 2. Scoring | NDCG@10, NDCG@50, MAP, P@10 vs hidden ground truth | Score below cutoff |
| 3. Code Reproduction + Honeypot Check | Top-N: code reproduced in Docker sandbox | Can't reproduce; honeypot rate >10% in top 100; missing repo |
| 4. Manual Review | Reasoning quality, methodology, git history authenticity | Bad reasoning; flat git history; LLM-only code |
| 5. Defend-Your-Work Interview | 30-min video: explain architecture, defend choices | Can't explain; contradicts code; didn't build it |

### Scoring Metrics
| Metric | Weight | Measures |
|---|---|---|
| NDCG@10 | **0.50** | Quality of top-10 picks |
| NDCG@50 | **0.30** | Quality of top-50 picks |
| MAP | **0.15** | Precision across all relevance levels |
| P@10 | **0.05** | Fraction of top-10 that are "relevant" (tier 3+) |

**Final = 0.50×NDCG@10 + 0.30×NDCG@50 + 0.15×MAP + 0.05×P@10**

Tiebreak order: P@5 → P@10 → earlier timestamp

---

## 4. HONEYPOT RULES (Critical)

> Source: README.txt line 53, submission_spec.txt lines 160–163

- ~80 honeypots with **subtly impossible profiles** in the 100K pool
- Examples: "8 years at a company founded 3 years ago", "expert in 10 skills with 0 years used"
- Forced to **relevance tier 0** in ground truth
- **Submissions with honeypot rate >10% in top 100 are DISQUALIFIED at Stage 3**

### ⚠️ KEY RULE (submission_spec.txt line 163):
> **"We expect a good ranking system to NATURALLY avoid them; you don't need to special-case them."**

This means: **NO hard if-statement blocks**. Your scoring architecture should make honeypots score low naturally.

---

## 5. REASONING COLUMN — Manual Review Criteria (Stage 4)

The reasoning is sampled (10 random rows) and checked for:

| Check | What they look for |
|---|---|
| Specific facts | References years, title, named skills, signal values from the actual profile |
| JD connection | Links to specific JD requirements, not generic praise |
| Honest concerns | Acknowledges gaps / concerns where they exist |
| No hallucination | Every claim must exist in the candidate's profile |
| Variation | 10 sampled reasonings must be substantially different |
| Rank consistency | Tone must match rank (rank-5 with critical reasoning = bad) |

**Penalized:** Empty reasoning, all-identical strings, templated reasoning, hallucinated skills, reasoning that contradicts rank.

---

## 6. BEHAVIORAL SIGNALS REFERENCE (redrob_signals_doc.txt)

All 23 signals in `redrob_signals`:

| # | Signal | Range | What it measures |
|---|---|---|---|
| 1 | profile_completeness_score | 0–100 | Profile fill % |
| 2 | signup_date | date | When they joined Redrob |
| 3 | last_active_date | date | Last login |
| 4 | open_to_work_flag | bool | Are they available |
| 5 | profile_views_received_30d | int ≥ 0 | Recruiter view count (30d) |
| 6 | applications_submitted_30d | int ≥ 0 | Roles applied to recently |
| 7 | recruiter_response_rate | 0.0–1.0 | Fraction of recruiter msgs replied |
| 8 | avg_response_time_hours | number ≥ 0 | Median reply time |
| 9 | skill_assessment_scores | dict[str→0-100] | Per-skill platform test scores |
| 10 | connection_count | int ≥ 0 | Redrob connections |
| 11 | endorsements_received | int ≥ 0 | Skill endorsements |
| 12 | notice_period_days | 0–180 | Stated notice period |
| 13 | expected_salary_range_inr_lpa | {min, max} | Salary expectation (LPA) |
| 14 | preferred_work_mode | onsite/hybrid/remote/flexible | Work mode preference |
| 15 | willing_to_relocate | bool | Will they move |
| 16 | github_activity_score | -1–100 | GitHub contribution score (-1 = none) |
| 17 | search_appearance_30d | int ≥ 0 | Times appeared in recruiter searches |
| 18 | saved_by_recruiters_30d | int ≥ 0 | Recruiter bookmarks (30d) |
| 19 | interview_completion_rate | 0.0–1.0 | Interviews actually attended |
| 20 | offer_acceptance_rate | -1–1.0 | Offer acceptance rate (-1 = no history) |
| 21 | verified_email | bool | Email verified |
| 22 | verified_phone | bool | Phone verified |
| 23 | linkedin_connected | bool | LinkedIn connected |

> Key insight from signals doc: "A perfect-on-paper candidate who hasn't logged in for 6 months and has a 5% response rate is, for hiring purposes, **not actually available**. Down-weight them appropriately."

---

## 7. CANDIDATE SCHEMA — Key Fields

```
candidate_id        → CAND_XXXXXXX (7 digits)

profile:
  current_title     → Job title
  headline          → One-line professional headline
  summary           → Multi-sentence summary
  location          → City, region
  country           → Country
  years_of_experience → float (0–50)
  current_company   → Company name
  current_company_size → enum: "1-10" ... "10001+"
  current_industry  → Industry string

career_history[]:   (1–10 jobs)
  company, title, start_date, end_date
  duration_months, is_current
  industry, company_size, description

education[]:
  institution, degree, field_of_study
  start_year, end_year, grade, tier (tier_1..tier_4)

skills[]:
  name, proficiency (beginner/intermediate/advanced/expert)
  endorsements, duration_months

certifications[]: name, issuer, year
languages[]:       language, proficiency

redrob_signals:    (all 23 signals above)
```

---

## 8. COMMON SUBMISSION MISTAKES (avoid these)

- 99 or 101 rows instead of exactly 100
- Ranks starting at 0 instead of 1
- Duplicate candidate_ids
- candidate_id typos not in candidates.jsonl
- All scores set to same value (no differentiation)
- Scores **increasing** with rank (rank 1 has lowest score)
- Submitting as .xlsx or .json instead of .csv

---

## 9. WHAT TO SUBMIT

1. **CSV file** — top-100 ranking
2. **GitHub repo** with:
   - README with single command to reproduce: `python rank.py --candidates ./candidates.jsonl --out ./submission.csv`
   - Full source code (no hidden steps)
   - Pre-computed artifacts OR script to generate them
   - requirements.txt / pyproject.toml
   - submission_metadata.yaml
3. **Portal metadata** — team name, contact, GitHub URL, sandbox link, AI tools declared

### Sandbox Requirements
- Accept ≤100 candidates as input
- Run ranking end-to-end → ranked CSV
- Complete within 5 min on CPU
- Acceptable: HuggingFace Spaces, Streamlit Cloud, Replit, Colab, Docker, Binder
