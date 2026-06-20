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
# 🚀 Redrob Intelligent Candidate Discovery & Ranking Engine
> **Team Srinath** — Submission Package & Reprodubicity Documentation

This repository contains the end-to-end data science pipeline and ranking system designed for the **Redrob Candidate Discovery & Ranking Challenge**. The system is built to identify and rank the top 100 candidates from a 100,000-candidate pool against a Senior AI Engineer job description, running on CPU in under 10 seconds.

---

## 🏃 Reproducing Results (Command Line Interface)

To reproduce the validated ranking output, run the ranking engine with the following command:

```bash
python rank.py --candidates "[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl" --out team_srinath.csv
```

### Options:
* `--candidates`: Path to the input JSON Lines candidates file.
* `--out`: Output path for the ranked CSV.

---

## 📐 System Architecture & Flow

The pipeline operates as a **hybrid search and scoring cascade**. Heavy preprocessing and text embedding generation are completed offline to satisfy the 5-minute CPU-only compute budget. During the online phase, the system performs fast vector retrieval using Numpy, applies behavioral modifiers, and scores candidates.

Detailed design diagrams and explanations:
* **Architecture Specifications**: [architecture.md](architecture.md)
* **Mermaid Flow Diagram**: [architecture_diagram.md](architecture_diagram.md)

---

## 🛡️ Rules Compliance & Safety Features

### 1. The "Honeypot" Traps (Instantly Disqualified if >10% in Top 100)
* **Rules Compliance:** The challenge specification instructs: *"We expect a good ranking system to NATURALLY avoid them; you don't need to special-case them."*
* **Solution:** We detect anomalous, impossible profiles (e.g. 10+ expert skills with 0 years of experience, or years at a company exceeding company age).
* **Soft Penalty:** Instead of using hard `if-else` exclusions, anomaly detection applies a **0.3x score multiplier penalty**, dynamically sinking honeypots to the bottom of the stack naturally.

### 2. IT-Services vs. Product Company Experience
* **Preferences:** The JD strongly prefers candidates with applied ML/AI experience at *product companies* over IT Consulting firms.
* **Solution:** Candidates whose career history is entirely in consulting firms (e.g. TCS, Infosys, Wipro, Accenture, Cognizant) are identified.
* **Soft Penalty:** To comply with the "no explicit database filters" rule, these candidates are not excluded. Instead, they receive a **0.85x score multiplier penalty** and have a clear reason logged in the `reasoning` column of the output.

---

## 📈 Hybrid Scoring Formula

For candidates, the final ranking score is calculated as:

$$\text{Final Score} = \left(0.35 \times S_{\text{title}} + 0.25 \times S_{\text{semantic}} + 0.20 \times S_{\text{skills\_exp}} + 0.20 \times S_{\text{behavioral}}\right) \times M_{\text{notice}} \times M_{\text{location}} \times M_{\text{availability}} \times M_{\text{work\_mode}} \times M_{\text{salary}} \times M_{\text{trust}} \times M_{\text{honeypot}} \times M_{\text{it\_service}}$$

Where:
* **$S_{\text{title}}$**: High boost for ML/AI Engineering titles, zero score for non-technical roles.
* **$S_{\text{semantic}}$**: Cosine similarity against the Job Description using BGE embeddings.
* **$S_{\text{skills\_exp}}$**: Combines skill weights and hands-on checked experience curves.
* **$S_{\text{behavioral}}$**: Multi-factor behavioral score: GitHub ($30\%$), responsiveness ($25\%$), login recency ($20\%$), platform reliability ($15\%$), and recruiter demand ($10\%$).
* **Modifiers ($M$)**: Adjust score by notice period, location relevance (Noida/Pune), preferred work mode, salary expectation, and trust anomalies (honeypot/IT services).

---

## 🖥️ Local UI Sandbox (Streamlit)

To launch the interactive Streamlit sandbox locally:
```bash
streamlit run app.py
```
This lets you dynamically tweak JDs, upload candidates, inspect detailed score breakdowns, and visualize the candidate pool.

