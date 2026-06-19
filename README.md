# 🚀 Redrob Intelligent Candidate Discovery & Ranking Ranker

This repository contains the end-to-end data science pipeline and ranking system designed for the **Redrob Candidate Discovery & Ranking Challenge**. The system is built to identify and rank the top 100 candidates from a 100,000-candidate pool against a Senior AI Engineer job description, running on CPU in under 5 seconds.

---

## 📐 System Architecture

The pipeline operates as a **hybrid search and scoring cascade**. Heavy preprocessing and text embedding generation are completed offline to satisfy the 5-minute CPU-only compute budget. During the online phase, the system performs fast vector retrieval using Numpy, filters out honeypots, and scores candidates.

Detailed design diagrams and explanations:
* **Architecture Specifications**: [architecture.md](architecture.md)
* **Mermaid Flow Diagram**: [architecture_diagram.md](architecture_diagram.md)

---

## 🏃 Execution Modes

The ranking engine (`rank.py`) supports two execution modes, automatically branching based on the input candidates file:

1. **🚀 Cached Mode (Fast Path)**
   * **Use Case**: Runs on the full 100,000 candidate dataset.
   * **Mechanism**: Loads the pre-computed 153MB Numpy matrix (`embeddings.npy`) and pre-calculated feature scores.
   * **Speed**: Cosine similarity is calculated via a single Numpy dot product in **0.05 seconds**. Total execution time is **$< 5$ seconds**.

2. **⚙️ Dynamic Mode (Sandbox / New Test Sets)**
   * **Use Case**: Runs on small samples (e.g. sandbox tests of $\le 100$ candidates) or new candidate files.
   * **Mechanism**: Loads the local BGE Small model, generates text representations and embeddings, and calculates features on-the-fly.
   * **Speed**: Runs dynamically in **$< 10$ seconds** for a 100-candidate pool.

---

## 📊 Exploratory Data Analysis (EDA)

We conducted **8 core analyses** on the 100,000 candidate pool to understand distributions and protect against disqualifications:
1. **Data Integrity & Schema Check**
2. **Honeypot Profiling & Exclusions** (Identifying and pruning the $9.35\%$ synthetic fake profiles)
3. **IT Services Only Exclusions** (Pruning the $8.99\%$ consulting-only profiles)
4. **Experience Fit Curve** (Sweet-spot curve for 6-8 years, validating hands-on coding for $>8$ years)
5. **Availability & Behavioral Signal Modeling** (Integrating platform activity, notice periods, and relocation logistics)
6. **NLP Text & Keyword-Stuffer Analysis** (N-grams on headlines and catching non-tech keyword stuffers)
7. **Tie-Breaker Analysis** (Deterministic `candidate_id` ascending sorting)
8. **Latency & Compute budget simulation**

To run these analyses and view the visualization charts, open and run the Jupyter notebook:
👉 **[data/understanding/data.ipynb](data/understanding/data.ipynb)**

---

## 🛠️ Environment Setup & Installation

### 1. Activate Virtual Environment
Navigate to the project root and activate `red_env`:

* **PowerShell (Windows)**:
  ```powershell
  .\red_env\Scripts\Activate.ps1
  ```
* **Command Prompt (CMD)**:
  ```cmd
  .\red_env\Scripts\activate.bat
  ```

### 2. Install Dependencies
Install all package requirements:
```bash
pip install -r requirements.txt
```

---

## 📈 Hybrid Scoring Formula

For candidates passing the exclusions, the final ranking score is calculated as:

$$\text{Final Score} = \left(0.35 \times S_{\text{title}} + 0.25 \times S_{\text{semantic}} + 0.20 \times S_{\text{skill\_depth}} + 0.20 \times S_{\text{behavioral}}\right) \times M_{\text{notice}} \times M_{\text{location}}$$

Where:
* **$S_{\text{title}}$**: High boost for ML/AI Engineering titles, zero score for non-technical roles.
* **$S_{\text{semantic}}$**: Cosine similarity against the Job Description using `BAAI/bge-small-en-v1.5`.
* **$S_{\text{skill\_depth}}$**: Combines skill weights and hands-on checked experience curves.
* **$S_{\text{behavioral}}$**: Multi-factor behavioral score: GitHub ($30\%$), responsiveness ($25\%$), login recency ($20\%$), platform reliability ($15\%$), and recruiter demand ($10\%$).
* **Modifiers ($M$)**: Adjust score by notice period (sub-30 days preferred) and location/visa status (Pune/Noida local or Tier-1 India relocation).
