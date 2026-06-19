# 📊 Detailed Pipeline Architecture Diagram

This diagram visualizes the end-to-end data flow, dividing the system into the **Pre-computation Phase**, the **Ranking Step** (supporting Cached, Hybrid Dynamic, and Full Dynamic modes), and the **Sandbox UI**. All phases run 100% offline.

```mermaid
flowchart TD
    %% Styling Definitions
    classDef prep fill:#e0f7fa,stroke:#00acc1,stroke-width:2px,color:#004d40;
    classDef rank fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#4a148c;
    classDef filter fill:#ffebee,stroke:#e53935,stroke-width:2px,color:#b71c1c;
    classDef decision fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef output fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20;
    classDef logging fill:#fff3e0,stroke:#ef6c00,stroke-width:2px,color:#e65100;
    classDef sandbox fill:#e8eaf6,stroke:#3949ab,stroke-width:2px,color:#1a237e;

    %% ----------------------------------------------------
    %% PRE-COMPUTATION PHASE
    %% ----------------------------------------------------
    subgraph Prep ["Pre-computation Phase (build_cache.py - Run Once)"]
        A["[1.1] Raw Candidates Pool: 100K JSONL"]:::prep --> B["[1.2] Extract Features via offline_utils.py"]:::prep
        B --> C["[1.2.1] Honeypot & IT-Service Flags"]:::prep
        B --> D["[1.2.2] Title, Skills, Exp, Behavioral Scores"]:::prep
        C --> F2["[1.4.2] features.json (disk cache)"]:::prep
        D --> F2
        A --> E["[1.3] BGE Small Embedder (batch_size=256)"]:::prep
        E --> F1["[1.4.1] embeddings.npy (100K x 384)"]:::prep
        B --> F3["[1.4.3] candidate_ids.json"]:::prep
    end

    %% ----------------------------------------------------
    %% RANKING STEP
    %% ----------------------------------------------------
    subgraph Rank ["Ranking Step (rank.py - 5-Minute Clock)"]
        G["[2.1] Input: candidates.jsonl"]:::rank --> H{"[2.2] All IDs in cache?"}:::decision

        %% Cached Mode
        H -- "Yes: CACHED MODE" --> I1["[2.3A] Load cache from RAM"]:::rank
        I1 --> K1["[2.4A] Encode JD with BGE"]:::rank
        K1 --> L1["[2.5A] Cosine Similarity via np.dot"]:::rank
        L1 --> M1["[2.6] Scored Candidate Pool"]:::rank

        %% Hybrid Dynamic Mode
        H -- "No: HYBRID MODE" --> SEP["[2.3B] Split cached vs uncached"]:::rank
        SEP --> CA["[2.4B] Cached: lookup features + embeddings"]:::rank
        SEP --> UC["[2.4C] Uncached: embed on-the-fly + extract features"]:::rank
        CA --> MERGE["[2.5B] Merge scored sets"]:::rank
        UC --> MERGE
        MERGE --> M1

        %% Exclusions & Scoring
        M1 --> N["[2.7] Exclude Honeypots & IT-Service-Only"]:::filter
        N --> EX["[2.8] Log exclusion counts"]:::logging
        EX --> O["[2.9] Hybrid Score: 0.35T + 0.25S + 0.20SK + 0.20B"]:::rank
        O --> MOD["[2.10] Apply Notice & Location Modifiers"]:::rank
        MOD --> P{"[2.11] Score ties?"}:::decision

        %% Tie-Breaking & Output
        P -- "Yes" --> Q["[2.12A] Tie-break: candidate_id ascending"]:::filter
        P -- "No" --> R["[2.12B] Sort by score descending"]:::rank
        Q --> S["[2.13] Assign unique ranks 1-100"]:::rank
        R --> S
        S --> TOP5["[2.14] Log Top 5 Candidates Preview"]:::logging
        TOP5 --> T["[2.15] Export team_redrob.csv with reasoning"]:::output
    end

    %% ----------------------------------------------------
    %% SANDBOX UI
    %% ----------------------------------------------------
    subgraph Sandbox ["Sandbox UI (app.py - HuggingFace Spaces)"]
        U1["[3.1] Upload JSON/JSONL (max 100)"]:::sandbox --> U2["[3.2] @st.cache_resource: Load Model + Cache"]:::sandbox
        U2 --> U3["[3.3] Hybrid Cache Lookup"]:::sandbox
        U3 --> U4["[3.4] Score & Rank"]:::sandbox
        U4 --> U5["[3.5] Generate reasoning (top 100 only)"]:::sandbox
        U5 --> U6["[3.6] Display Table + CSV Download"]:::sandbox
    end

    %% ----------------------------------------------------
    %% ORCHESTRATOR
    %% ----------------------------------------------------
    subgraph Orch ["Pipeline Orchestrator (run_pipeline.py)"]
        O1["[4.1] Verify Challenge Bundle"]:::logging --> O2["[4.2] Ensure Cache Exists"]:::logging
        O2 --> O3["[4.3] Execute rank.py"]:::logging
        O3 --> O4["[4.4] Run validate_submission.py"]:::logging
        O4 --> O5["[4.5] Check submission_metadata.yaml"]:::logging
    end

    %% Phase Connections
    F1 -.-> I1
    F2 -.-> I1
    F3 -.-> I1
    F1 -.-> U2
    F2 -.-> U2
    F3 -.-> U2
```

---

### 🎨 Color & Component Legend:
* **Teal Nodes**: **Pre-computation Phase** – run once to compress 100K text profiles into lightweight matrices and feature scores.
* **Purple Nodes**: **Ranking Step** – fast execution blocks for scoring, similarity computation, and CSV output.
* **Yellow Nodes**: **Decision Points** – runtime checks for cache availability and score tie detection.
* **Red Nodes**: **Exclusions & Bias Checks** – safety filters that prune honeypot/IT-service candidates and enforce deterministic sorting.
* **Orange Nodes**: **Logging** – structured log events written to `artifacts/logs/pipeline.log` for traceability.
* **Indigo Nodes**: **Sandbox UI** – Streamlit web app with cached resource loading, hybrid lookup, and CSV download.
* **Green Node**: **Final Output** – the verified, monotonic, 100-row submission CSV.
