# 📊 Pipeline Architecture Diagrams

Mermaid diagrams for the Redrob ranking system. Three views: the end-to-end data flow, the scoring formula breakdown, and the execution mode decision tree.

---

## Diagram 1 — End-to-End Pipeline Flow

```mermaid
flowchart TD
    classDef prep   fill:#e0f7fa,stroke:#00acc1,stroke-width:2px,color:#004d40
    classDef rank   fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#4a148c
    classDef score  fill:#ede7f6,stroke:#5e35b1,stroke-width:2px,color:#311b92
    classDef mod    fill:#fff8e1,stroke:#f9a825,stroke-width:2px,color:#e65100
    classDef decide fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#f57f17
    classDef output fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20
    classDef log    fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#e65100
    classDef ui     fill:#e8eaf6,stroke:#3949ab,stroke-width:2px,color:#1a237e

    %% ── PRE-COMPUTATION (build_cache.py) ──────────────────────────────
    subgraph Prep ["🏗️ Phase 1 — Offline Pre-computation  (build_cache.py · run once)"]
        direction TB
        P1["100K Candidates\ncandidates.jsonl"]:::prep
        P2["Extract Features\noffline_utils.py"]:::prep
        P3["BGE Embedder\nbge-small-en-v1.5\nbatch_size=256 · CPU"]:::prep
        P4["features.json\n23 signals per candidate"]:::prep
        P5["embeddings.npy\n100K × 384 float32"]:::prep
        P6["candidate_ids.json\nID → row-index map"]:::prep

        P1 --> P2
        P1 --> P3
        P2 --> P4
        P3 --> P5
        P2 --> P6
    end

    %% ── RANKING (rank.py) ─────────────────────────────────────────────
    subgraph Rank ["⚡ Phase 2 — Online Ranking  (rank.py · ≤ 10 seconds on CPU)"]
        direction TB
        R1["Input: candidates.jsonl"]:::rank
        R2{"All IDs\nin cache?"}:::decide

        %% Cached path
        R3A["CACHED MODE\nLoad features + embeddings\nfrom disk"]:::rank
        R4A["Encode JD with BGE\nnp.dot → cosine similarity"]:::rank

        %% Hybrid path
        R3B["HYBRID DYNAMIC MODE\nSplit cached / uncached"]:::rank
        R4B["Encode uncached\ncandidates on-the-fly"]:::rank
        R4C["Merge cached +\non-the-fly results"]:::rank

        %% Scoring
        R5["Compute Composite Score\n0.35T + 0.25S + 0.20K + 0.20B"]:::score
        R6["Apply Modifiers\nNotice · Location · Availability\nWork-mode · Salary · Trust"]:::mod
        R7["Apply Safety Penalties\nHoneypot × 0.3 · IT-Service × 0.85\n(soft multipliers — no hard exclusions)"]:::mod
        R8["Sort descending\nTie-break: candidate_id ascending"]:::rank
        R9["Top 100 + reasoning"]:::rank
        R10["team_srinath.csv"]:::output

        R1 --> R2
        R2 -- "Yes" --> R3A --> R4A --> R5
        R2 -- "No"  --> R3B --> R4B --> R4C --> R5
        R5 --> R6 --> R7 --> R8 --> R9 --> R10
    end

    %% ── ORCHESTRATOR (run_pipeline.py) ────────────────────────────────
    subgraph Orch ["🔁 Orchestrator  (run_pipeline.py)"]
        direction LR
        O1["Verify\nchallenge bundle"]:::log
        O2["Check\ncache exists"]:::log
        O3["Run\nrank.py"]:::log
        O4["Validate\nCSV format"]:::log
        O5["Check\nmetadata.yaml"]:::log
        O1 --> O2 --> O3 --> O4 --> O5
    end

    %% ── SANDBOX UI (app.py) ───────────────────────────────────────────
    subgraph UI ["🖥️ Sandbox UI  (app.py · Streamlit · HuggingFace Spaces)"]
        direction LR
        U1["Upload JSON/JSONL\n≤ 100 candidates"]:::ui
        U2["Cache lookup\n+ on-the-fly encoding"]:::ui
        U3["Score & Rank"]:::ui
        U4["Display table\n+ CSV download"]:::ui
        U1 --> U2 --> U3 --> U4
    end

    %% Cross-phase connections
    P4 -. "pre-computed features" .-> R3A
    P5 -. "embedding matrix"      .-> R3A
    P6 -. "ID → index map"        .-> R3A
    P4 -. "pre-computed features" .-> U2
    P5 -. "embedding matrix"      .-> U2
```

---

## Diagram 2 — Scoring Formula Breakdown

```mermaid
flowchart LR
    classDef comp fill:#e8eaf6,stroke:#3949ab,color:#1a237e
    classDef mod  fill:#fff8e1,stroke:#f9a825,color:#e65100
    classDef out  fill:#e8f5e9,stroke:#43a047,color:#1b5e20

    T["T — Title Score\n100 = ML/AI Engineer\n50 = Adjacent tech\n0 = Non-technical"]:::comp
    S["S — Semantic Score\nBGE cosine(candidate, JD)\n× 100"]:::comp
    K["K — Skills + Experience\n0.5 × skill_match\n+ 0.5 × exp_curve"]:::comp
    B["B — Behavioral\nGitHub 30%\nResponsiveness 25%\nLogin recency 20%\nReliability 15%\nRecruiter demand 10%"]:::comp

    COMP["Composite\n0.35T + 0.25S + 0.20K + 0.20B"]:::out

    T --> COMP
    S --> COMP
    K --> COMP
    B --> COMP

    MN["M_notice\n1.2× ≤30d\n1.0× ≤60d\n0.85× >60d"]:::mod
    ML["M_location\n1.15× Noida/Pune\n0.90× other India\n0.75× international"]:::mod
    MA["M_availability\nopen_to_work boost"]:::mod
    MW["M_work_mode\nhybrid/remote match"]:::mod
    MS["M_salary\nexpectation fit"]:::mod
    MT["M_trust\nplatform signals"]:::mod
    MH["M_honeypot\n0.3× if anomalous\n(soft penalty only)"]:::mod
    MI["M_it_service\n0.85× if purely\nIT consulting career"]:::mod

    FINAL["Final Score\n(0.0 – 1.0)"]:::out

    COMP --> FINAL
    MN --> FINAL
    ML --> FINAL
    MA --> FINAL
    MW --> FINAL
    MS --> FINAL
    MT --> FINAL
    MH --> FINAL
    MI --> FINAL
```

---

## Diagram 3 — Execution Mode Decision Tree

```mermaid
flowchart TD
    classDef decide fill:#fffde7,stroke:#fbc02d,color:#f57f17
    classDef fast   fill:#e8f5e9,stroke:#43a047,color:#1b5e20
    classDef slow   fill:#fce4ec,stroke:#e91e63,color:#880e4f
    classDef hybrid fill:#e3f2fd,stroke:#1e88e5,color:#0d47a1

    A["rank.py invoked"]
    B{"artifacts/embeddings.npy\nfeatures.json\ncandidate_ids.json\nexist?"}:::decide
    C{"All input\ncandidate_ids\nin cache?"}:::decide

    FAST["CACHED MODE ✅\nLoad matrix from RAM\nnp.dot cosine sim\n~10 seconds total"]:::fast

    HYB["HYBRID DYNAMIC MODE 🔄\nSplit input into\ncached + uncached sets\nEncode uncached on-the-fly\nMerge & score combined"]:::hybrid

    FULL["FULL DYNAMIC MODE ⚠️\n(no cache at all)\nEmbed all candidates live\nmuch slower"]:::slow

    A --> B
    B -- "Yes" --> C
    B -- "No"  --> FULL
    C -- "All cached"     --> FAST
    C -- "Partial / none" --> HYB
```

---

### 🎨 Colour Legend

| Colour | Phase |
|---|---|
| 🟦 Teal | Pre-computation (build_cache.py) |
| 🟪 Purple | Ranking engine steps (rank.py) |
| 🟨 Yellow | Decision / branch points |
| 🟧 Amber | Score modifiers |
| 🟩 Green | Outputs |
| 🔵 Blue | Sandbox UI (Streamlit) |
| 🟠 Orange | Logging / orchestration |
