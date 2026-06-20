# 🧩 Redrob Hackathon — Rules & Specification

This document summarizes the core rules, formatting requirements, constraints, and scoring mechanisms for the Intelligent Candidate Discovery & Ranking Challenge.

---

## 1️⃣ Deliverable & File Format
- **Filename**: Your team’s registered participant ID + `.csv` (e.g. `team_xxx.csv`).
- **Encoding**: UTF‑8.
- **Header Row**: Must be exactly `candidate_id,rank,score,reasoning` (all lowercase, no spaces).
- **Rows**: Exactly 100 rows of data + 1 header row (total 101 rows).
- **Ranks**: Ranks 1 to 100 must appear exactly once. 1 = best fit; 100 = 100th best fit. No ranking beyond 100.
- **Scores**: Must be monotonically non-increasing (score at rank $i \ge$ score at rank $i+1$). Ties are allowed, but unique ranks must be assigned.
- **Tie-breaker**: Break score ties deterministically using candidate_id ascending (alphabetical order) or a secondary model signal.

---

## 2️⃣ Compute Constraints
During the ranking step, the system must conform to:
- **Runtime**: $\le 5$ minutes (wall-clock time).
- **Memory**: $\le 16$ GB RAM.
- **GPU**: ❌ Not allowed (CPU execution only).
- **Network**: ❌ Forbidden (No external API calls during ranking, no hosted LLMs like OpenAI, Anthropic, Gemini, etc.).
- **Disk**: $\le 5$ GB intermediate state.

---

## 3️⃣ Honeypots & Traps (Critical Filters)
- **Honeypots**: The dataset contains ~80 honeypot profiles (impossible dates, expert skills with 0 months duration, etc.).
  - **Disqualification Threshold**: If the top 100 contains $>10\%$ honeypots, the submission is disqualified.
- **Keyword-Stuffer Traps**: Candidates who stuff keywords in their skills list but have irrelevant titles (e.g., Marketing Manager with ML skills) or lack actual project experience.
- **IT Service Company Trap**: Candidates who have worked *only* at consulting/service firms (TCS, Infosys, Wipro, Accenture, Cognizant, etc.) are a mismatch unless they have prior product-company experience.

---

## 4️⃣ Reasoning Column Guidelines
The reasoning column is heavily evaluated at Stage 4 (Manual Review). Rules to prevent penalties:
- **Specific Facts**: Must reference specific years, titles, skills, or platform metrics.
- **JD Connection**: Must connect explicitly to founding AI engineer requirements.
- **Honest Gaps**: Must call out concerns where applicable (e.g., long notice period, relocation need).
- **No Hallucinations**: Do not mention skills, companies, or experience not present in the profile.
- **Variation**: No templates, boilerplate sentences, or copy-pasted patterns across rows.
- **Rank Consistency**: Tone of reasoning must match the rank (e.g., rank 1 is glowing, rank 100 notes gaps/filler nature).

---

## 5️⃣ Scoring & Tiebreaks
**Final Composite Score Formula**:
$$Score = 0.50 \times NDCG@10 + 0.30 \times NDCG@50 + 0.15 \times MAP + 0.05 \times P@10$$

**Tiebreak Order**:
1. Higher $P@5$ wins.
2. Higher $P@10$ wins.
3. Earlier submission timestamp wins.

---

## 6️⃣ Submission Checklist
- [ ] Exactly 100 rows + 1 header.
- [ ] Unique ranks 1–100.
- [ ] Valid candidate IDs existing in `candidates.jsonl`.
- [ ] Non-increasing scores by rank.
- [ ] UTF-8 `.csv` file.
- [ ] Pass the local validation tool (`validate_submission.py`).
- [ ] Working sandbox link (HuggingFace Spaces, Streamlit, etc.).
- [ ] Metadata YAML file matching Portal inputs.
- [ ] Git history with incremental iteration commits (Stage 4 check).
