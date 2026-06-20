---
title: Redrob Talent Sandbox
emoji: 🤖
colorFrom: blue
colorTo: purple
sdk: streamlit
sdk_version: 1.35.0
app_file: app.py
pinned: false
license: mit
---

# 🚀 Redrob Intelligent Candidate Ranking Engine

> **Team Srinath** · India Runs Data & AI Challenge · Candidate Discovery Track

An offline, CPU-only hybrid ranking pipeline that identifies and ranks the top 100 candidates from a 100,000-candidate pool against a **Senior AI Engineer** job description — completing in under 10 seconds at inference time.

---

## ⚡ Quick Start — Reproduce Results

### Step 1 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Build the offline cache (run once, ~43 mins on CPU)
```bash
python build_cache.py
```
This generates three files in `artifacts/`:
- `embeddings.npy` — 100K × 384 BGE embedding matrix
- `features.json` — pre-computed scores for all candidates
- `candidate_ids.json` — ID-to-index lookup map

### Step 3 — Rank candidates
```bash
python rank.py \
  --candidates "[PUB] India_runs_data_and_ai_challenge/India_runs_data_and_ai_challenge/candidates.jsonl" \
  --out team_srinath.csv
```

### Step 4 — Run the full automated pipeline (optional)
```bash
python run_pipeline.py
```
This verifies the challenge bundle, checks the cache, runs ranking, and validates the output CSV format.

---

## 🗂️ Repository Structure

```
redrob/
├── rank.py                  # Main ranking engine (CPU-only, ~10s inference)
├── build_cache.py           # Offline pre-computation — run once
├── run_pipeline.py          # End-to-end automated orchestrator
├── offline_utils.py         # All scoring functions, signal extractors, modifiers
├── app.py                   # Streamlit sandbox UI (HuggingFace Spaces)
├── extract_docs.py          # Resume/doc extraction utility
│
├── requirements.txt         # Python dependencies
├── submission_metadata.yaml # Team info, compute spec, declarations
│
├── artifacts/               # Pre-computed cache (not committed to git)
│   ├── embeddings.npy       # BGE embeddings matrix (100K × 384, ~147 MB)
│   ├── features.json        # Structured feature scores per candidate
│   ├── candidate_ids.json   # ID → matrix-row index map
│   └── logs/                # Pipeline execution logs
│
├── docs/                    # Technical documentation
│   ├── architecture.md      # System design & component specs
│   ├── architecture_diagram.md  # Mermaid flow diagrams
│   ├── process_audit.md     # Rules compliance audit
│   ├── DEVLOG.md            # Development log
│   └── REDROB_CHALLENGE_REF.md  # Challenge spec reference
│
└── [PUB] India_runs_data_and_ai_challenge/  # Challenge bundle (not committed)
```

---

## 🧠 How It Works

### Two-Phase Architecture

**Phase 1 — Offline Pre-computation (`build_cache.py`)**
All heavy work is done once before the clock starts:
- 100K candidate profiles are embedded using `BAAI/bge-small-en-v1.5` (384-dim)
- 23 behavioral and structural signals are extracted per candidate
- Results serialised to disk as `.npy` and `.json` files

**Phase 2 — Online Ranking (`rank.py`)**
At inference time the system chooses one of two execution paths:

| Mode | Trigger | Speed |
|---|---|---|
| **CACHED** | All input IDs present in cache | ~10 seconds |
| **HYBRID DYNAMIC** | Some IDs not in cache | Encodes unknowns on-the-fly, merges results |

### Scoring Formula

```
Final Score = (0.35 × T + 0.25 × S + 0.20 × K + 0.20 × B)
              × M_notice × M_location × M_availability
              × M_work_mode × M_salary × M_trust
              × M_honeypot × M_it_service
```

| Component | Description |
|---|---|
| **T** — Title Score | High boost for ML/AI/Data Engineering titles; zero for non-technical disciplines |
| **S** — Semantic Score | Cosine similarity (BGE embedding of candidate profile vs. JD) × 100 |
| **K** — Skills + Exp | Weighted skill match (23 AI/ML skills) combined with experience curve |
| **B** — Behavioral | GitHub activity (30%) + Recruiter responsiveness (25%) + Login recency (20%) + Platform reliability (15%) + Demand (10%) |
| **M_notice** | 1.2× ≤30 days · 1.0× ≤60 · 0.85× >60 days |
| **M_location** | 1.15× Noida/Pune · 0.9× other India · 0.75× international |
| **M_honeypot** | **0.3×** if anomalous profile detected (never excluded, naturally demoted) |
| **M_it_service** | **0.85×** if career entirely in IT consulting (TCS, Infosys, Wipro, etc.) |

### Tie-breaking
Scores rounded to 4 decimal places. Ties broken by `candidate_id` ascending (deterministic).

---

## 🛡️ Rules Compliance

| Rule | Requirement | Implementation |
|---|---|---|
| **No hard filters** | Ranking must be natural, not exclusion-based | Honeypot & IT-service penalties are **score multipliers only** (0.3× and 0.85×) — no candidate is removed |
| **CPU-only** | No GPU at inference | `SentenceTransformer(..., device="cpu")` enforced in `rank.py`, `build_cache.py`, `app.py` |
| **No network** | Ranking must work offline | All models and data are local; no API calls during inference |
| **Monotonic ranks** | No score ties in output | 4-decimal rounding + ascending `candidate_id` tie-break guarantees uniqueness |
| **100 rows** | CSV must have exactly 100 rows | Loop pads with placeholder rows if input < 100 candidates |

---

## 🖥️ Interactive Sandbox (Streamlit)

```bash
streamlit run app.py
```

Upload candidates (JSON or JSONL, up to 100), inspect detailed score breakdowns per component, and download a ranked CSV. The sandbox uses the same cached embeddings and feature files as the CLI pipeline.

🌐 Live demo: [huggingface.co/spaces/srinath2934/redrob-ranker](https://huggingface.co/spaces/srinath2934/redrob-ranker)

---

## 📚 Further Reading

| Document | Description |
|---|---|
| [docs/architecture.md](docs/architecture.md) | Full component-level architecture spec |
| [docs/architecture_diagram.md](docs/architecture_diagram.md) | Mermaid pipeline flow diagrams |
| [docs/process_audit.md](docs/process_audit.md) | Line-by-line hackathon rules compliance audit |
| [submission_metadata.yaml](submission_metadata.yaml) | Team info, compute env, AI tool declarations |
