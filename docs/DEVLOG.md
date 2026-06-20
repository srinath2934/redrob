# 🧠 Redrob AI Ranker — Developer Log

> **Team:** Redrob AI  
> **Challenge:** Intelligent Candidate Discovery & Ranking  
> **Started:** 2026-06-17 | **Last Updated:** 2026-06-19  
> **Status:** ✅ Pipeline passing validator | 🔧 Scoring accuracy in active improvement

---

## 📅 Day 1 (2026-06-17) — Foundation & Architecture

### What We Built
- Read all challenge docs: job_description.txt, submission_spec.txt, redrob_signals_doc.txt, candidate_schema.json
- Designed a **5-component hybrid scoring pipeline** running 100% offline on CPU
- Wrote `offline_utils.py` (scoring functions + honeypot detectors)
- Wrote `rank.py` (ranking engine with cached + dynamic mode)
- Wrote `build_cache.py` (pre-computation: BGE embeddings + feature extraction for 100K candidates)
- Wrote `run_pipeline.py` (end-to-end orchestrator: cache → rank → validate → metadata)
- Wrote `app.py` (Streamlit sandbox UI with file upload and CSV download)
- Pre-computed all 100K candidate embeddings and features → saved to `artifacts/`

### Key Architectural Decisions

| Decision | Rationale |
|---|---|
| BGE Small (BAAI/bge-small-en-v1.5) | Best CPU-speed vs quality tradeoff for semantic matching |
| Pre-compute all embeddings in `build_cache.py` | Guarantees ranking step runs in <5 seconds |
| NumPy dot product (no Qdrant/FAISS daemon) | Avoids external process dependency; works offline |
| Hybrid cache + dynamic mode | Sample file (50 cands) uses dynamic; full 100K pool uses cache |
| Deterministic tie-breaking by candidate_id ASC | Reproducible, auditable, no randomness |

### Formula
```
Final Score = (0.35 × Title) + (0.25 × Semantic) + (0.20 × SkillDepth) + (0.20 × Behavioral)
Final Score × M_notice × M_location
```

---

## 📅 Day 2 (2026-06-18) — Streamlit Integration & Git Push

### What We Did
- Installed all dependencies in `red_env` virtual env (Python 3.12)
- Launched local Streamlit server: `python -m streamlit run app.py` at **localhost:8501**
- Verified pipeline on sample_candidates.json (50 candidates)
- Confirmed validator passes: `validate_submission.py team_redrob.csv` → **Submission is valid**
- Populated `submission_metadata.yaml` with team info, GitHub repo, sandbox link
- Pushed all code to GitHub: `srinath2934/redrob`

### Git Push Commands Used
```bash
git add -A
git commit -m "feat: initial pipeline - BGE ranker, honeypot detector, streamlit sandbox"
git push origin main
```

---

## 📅 Day 3 (2026-06-19) — Bug Fix Sprint: Scoring Accuracy

### 🐛 Critical Bug #1: Title Score "engineer" Keyword Pollution

**Problem Found:**  
`calculate_title_score()` used a generic `"engineer"` keyword to give 70 points.  
This caused `Civil Engineer`, `Mechanical Engineer`, `Electrical Engineer` to all score 70.0 — the same as a real `Backend Engineer`.

**Root Cause:**  
```python
# OLD (BROKEN)
tech_keywords = {"software", "backend", "data", "fullstack", "systems", "developer", "engineer"}
```
The bare word `"engineer"` matches ANY engineering discipline.

**Fix Applied:**  
```python
# NEW (FIXED) - Explicit qualified-title matching
hard_trap_keywords = [
    "civil engineer", "mechanical engineer", "chemical engineer",
    "electrical engineer", "aerospace engineer", ...
]

tech_keywords = [
    "software engineer", "backend engineer", "data engineer",
    "cloud engineer", "devops engineer", ...
]
```
- All non-software disciplines explicitly mapped to `0.0` (disqualified)
- Only named software disciplines get `70.0`
- Bare `"engineer"` with no qualifier now gets `60.0` (moderate, not reward)

---

### 🐛 Critical Bug #2: Disqualified Titles Still Scoring From Semantic Similarity

**Problem Found:**  
Even when `title_score = 0.0`, candidates were still getting a composite score because the BGE semantic similarity (25% weight) kept their overall score above 0.  
A `Business Analyst` with a good summary could score `0.30+` in the final output.

**Root Cause:**  
The scoring gate only excluded `is_honeypot` and `is_it_service_only` — but NOT `title_score == 0`.

```python
# OLD (BROKEN) - no title gate
if feats["is_honeypot"] or feats["is_it_service_only"]:
    final_score = 0.0
else:
    # Business Analyst still reaches here and gets scored!
    composite = (0.35 * title_score) + (0.25 * semantic_score) + ...
```

**Fix Applied in `rank.py` and `app.py`:**  
```python
# NEW (FIXED) - hard title gate added
if feats["is_honeypot"] or feats["is_it_service_only"]:
    final_score = 0.0
elif feats.get("title_score", 50.0) == 0.0:
    # Hard gate: non-tech role ALWAYS gets 0 regardless of semantic score
    final_score = 0.0
else:
    composite = ...
```

**Impact:** All non-tech titles (accountants, graphic designers, civil engineers, etc.) now score exactly `0.0000` and rank at the bottom.

---

### 🐛 Critical Bug #3: Honeypot Summary-Title Mismatch Not Detected

**Problem Found:**  
~56% of candidates in the first 1000 JSONL lines had profiles where the **summary text** was copied from a `"marketing manager"` template, but the **current title** was something like `Civil Engineer` or `Software Developer`.  
These candidates were bypassing `check_honeypot()` entirely.

**Root Cause:**  
The original honeypot detector only checked for:
1. Expert skill inflation (≥10 expert skills with 0 months)
2. Job duration anomalies
3. Future dates
4. Skill duration over-inflation

It did NOT check for summary-vs-title content mismatches.

**Fix Applied in `offline_utils.py`:**  
```python
# NEW — Check 5: Summary-Title Mismatch Detection
mismatch_patterns = [
    ("marketing manager", ["marketing", "sales", "brand"]),
    ("customer support", ["support", "customer", "service"]),
    ("graphic designer", ["graphic", "design", "visual"]),
    ("content writer", ["content", "writing", "copywrite"]),
    ("sales manager", ["sales", "revenue", "business development"]),
    ("hr manager", ["hr", "human resource", "recruitment"]),
]

for inject_keyword, valid_title_terms in mismatch_patterns:
    if inject_keyword in summary:
        title_matches = any(term in current_title for term in valid_title_terms)
        if not title_matches:
            reasons.append(f"summary_title_mismatch ...")
            break
```

---

### ✅ Verification After Fixes

- **Features Cache Rebuilt**: Successfully regenerated feature extraction for all 100,000 candidates with updated title scoring rules and summary-title mismatch checks.
- **Tie-Breaker Bug Fix**: Fixed a critical tie-breaker sorting error in `rank.py` and `app.py`. Previously, sorting on unrounded scores resulted in out-of-order `candidate_id` listings for matching rounded scores in the output CSV. Changed sorting keys to use the 4-decimal rounded score first.
- **Final Validation Status**: Ran `run_pipeline.py` successfully. Format validator reports: `Submission is valid.`.

---

## 📊 Pipeline Performance

| Metric | Value |
|---|---|
| Total Candidates | 100,000 |
| Honeypots Blocked | 73,496 (73.50%) |
| IT-Service-Only Excluded | 8,991 (8.99%) |
| Ranking Runtime | ~7.2 sec (cached mode) |
| Total Pipeline Time | ~15.5 sec |
| Wall-Clock Limit | 300 sec |
| Validator Status | ✅ PASS |

---

## 🗂️ Files in This Repository

| File | Purpose |
|---|---|
| `offline_utils.py` | Safety filters (honeypot, IT-service), scoring functions, logging setup |
| `build_cache.py` | Pre-computation: BGE embeddings + features for 100K candidates → `artifacts/` |
| `rank.py` | Ranking engine: cached/dynamic modes, CSV output, tie-breaking |
| `app.py` | Streamlit sandbox UI with file upload and CSV download |
| `run_pipeline.py` | Orchestrator: verify → cache → rank → validate → metadata |
| `submission_metadata.yaml` | Team metadata (name, contact, GitHub, compute env, AI tools) |
| `architecture.md` | Full system design document (formulas, scoring logic, data flow) |
| `DEVLOG.md` | This file — daily developer log |
| `requirements.txt` | Python dependencies |
| `artifacts/` | Pre-computed embeddings.npy, features.json, candidate_ids.json, bge_model/ |

---

## 🔮 What's Next

- [x] Re-run `build_cache.py` to re-index features with fixed `calculate_title_score()` and new `check_honeypot()` logic
- [x] Verify sample_candidates.json top 10 shows ONLY ML/AI/Software engineers
- [x] Fix tie-breaker sorting logic mismatch on rounded vs unrounded scores
- [x] Final run of `validate_submission.py` on final `team_redrob.csv`
- [ ] Push all fixes to GitHub with descriptive commit message
- [ ] Deploy updated app to HuggingFace Spaces

---

## 🤖 AI Tools Declaration

- **Antigravity IDE (Google DeepMind)** — Used for architectural reasoning, code generation, and debugging
- **No candidate data was fed to any external LLM at inference time**
- All ranking runs fully offline on local CPU
