# 🔍 Redrob Hackathon: Process Audit & Rules Compliance Report
> **Team Srinath** — Candidate Retrieval & Ranking Pipeline

This document contains a comprehensive process audit verifying that our pipeline's design, logic, and output files strictly adhere to the official Redrob Hackathon rules and expectations.

---

## 1. Compliance Checklist (Rules vs. Implementation)

| Rule / Constraint | Spec Requirement | Our Implementation | Status |
|---|---|---|---|
| **CPU Only** | No GPU usage allowed during ranking step | Runs fully on standard CPU using `numpy` and local `sentence-transformers`. | ✅ Compliant |
| **Execution Time** | $\le 5$ minutes wall-clock | **Cached Mode:** Runs in **10 seconds** (100k pool). <br> **Dynamic Mode:** Runs in **<10 seconds** (100 candidates). | ✅ Compliant |
| **Memory Limit** | $\le 16$ GB RAM | Uses **~300 MB RAM** to load the pre-computed embedding cache and JSON features. | ✅ Compliant |
| **Network Access** | Offline ranking — no external API calls (no OpenAI/Gemini/etc.) | Ranker loads `BAAI/bge-small-en-v1.5` from the local `artifacts/bge_model/` folder. No outbound network requests are made. | ✅ Compliant |
| **Output Schema** | Exactly 100 rows, headers: `candidate_id, rank, score, reasoning` | Verified by `validate_submission.py`. Header matches exactly, data is exactly 100 rows. | ✅ Compliant |
| **Score Sorting** | Monotonically non-increasing scores ($S_{\text{rank } i} \ge S_{\text{rank } i+1}$) | Checked and verified. Output is sorted by score descending. | ✅ Compliant |
| **Deterministic Tie-Break** | Ties broken by `candidate_id` ascending | Implemented in sorting key: `sort(key=lambda x: (-round(x["score"]/100.0, 4), x["candidate_id"]))` | ✅ Compliant |
| **Honeypot Exclusions** | Do not hard-exclude honeypots; let the ranker naturally avoid them. | Inconsistent/fake profiles (anomalous dates, expert skill inflation) are detected programmatically and penalized via a **0.3x multiplier**. No hard `if` block removes them. | ✅ Compliant |
| **IT Services Exclusions**| Do not hard-exclude consulting/outsourcing companies. | Identified consulting firms are soft-penalized with a **0.85x multiplier** rather than hard-excluded. | ✅ Compliant |

---

## 2. Metric-Specific Optimization Strategy

Organizers score submissions using:
$$\text{Composite Score} = 0.50 \times \text{NDCG@10} + 0.30 \times \text{NDCG@50} + 0.15 \times \text{MAP} + 0.05 \times \text{P@10}$$

### How Our Process Optimizes for This Formula:
1. **Maximizing NDCG@10 & P@10 (Top 10):**
   * The top 10 candidates have the highest weights in scoring. We enforce a high threshold for **Title Fit** (35% weight) and **Semantic Match** (25% weight).
   * Candidates with unrelated titles (e.g. Marketing, Customer Support) are immediately given a $0.0$ Title score, dropping them far out of the top 100.
2. **Behavioral Availability Filter:**
   * Ground truth relevance assumes a candidate must be contactable and active. We incorporate all 23 platform signals. An unresponsive candidate (low response rate, inactive for >6 months) gets their score penalized. This protects our NDCG scores from being ruined by "dead" profiles.
3. **Logistics Penalties:**
   * Candidates located outside Pune/Noida who are unwilling to relocate receive a heavy location penalty ($0.40$ or $0.10$ multiplier), preventing them from polluting the top 10/50.

---

## 3. Detailed Scoring Pipeline Process

For every candidate, the engine executes the following logic:

```
                  [Candidate JSON Data]
                           │
             ┌─────────────┴─────────────┐
             ▼                           ▼
    [Extract Text Summary]     [Extract 23 Signals]
             │                           │
    [BGE Embedding Vector]               ├─► Title Fit Score (35%)
             │                           ├─► Semantic Similarity (25%)
             ▼                           ├─► Skill Depth & Assessment (20%)
   [Cosine Similarity (Numpy)]           └─► Behavioral Score (20%)
             │                                       │
             └───────────────────┬───────────────────┘
                                 ▼
                         [Composite Score]
                                 │
             ┌───────────────────┴───────────────────┐
             ▼                                       ▼
  [Logistics Modifiers]                     [Trust Modifiers]
  - Notice Period (1.0 - 0.40)              - Profile Completeness
  - Location Relocation (1.0 - 0.10)        - Email/Phone Verified
  - Work Mode (0.85 if Remote)              - Honeypot Penalty (0.30x)
  - Salary Cap (0.90 if >80 LPA)            - IT-Service Penalty (0.85x)
             │                                       │
             └───────────────────┬───────────────────┘
                                 ▼
                           [Final Score]
                                 │
                                 ▼
                     [Deterministic Sorting]
             (Score Descending -> Candidate ID Ascending)
```

---

## 4. Reasoning Quality Process (Manual Review Safeguard)

The organizers manual review (Stage 4) samples 10 random candidates. Our generator prevents common automated rejection reasons:
* **Specific Facts:** Mentions years of experience, actual city location, and specific top skills.
* **Rank Consistency:** Lower-ranked candidates (rank > 60) have phrases explaining gaps (e.g. *"While their profile shows some relevant adjacent skills, there are notable gaps..."*).
* **Transparency:** Candidates penalized for IT-service company history explicitly show: *"Note: Their background is primarily in IT Services..."* so the reason for their lower rank is transparent.
