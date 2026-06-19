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
        A["Raw Candidates Pool: 100K JSONL"]:::prep --> B["Extract Features via offline_utils.py"]:::prep
        B --> C["Honeypot & IT-Service Flags"]:::prep
        B --> D["Title, Skills, Experience, Behavioral Scores"]:::prep
        C --> F2["features.json"]:::prep
        D --> F2
        A --> E["BGE Small Embedder (batch_size=256)"]:::prep
        E --> F1["embeddings.npy (100K x 384)"]:::prep
        B --> F3["candidate_ids.json"]:::prep
    end

    %% ----------------------------------------------------
    %% RANKING STEP
    %% ----------------------------------------------------
    subgraph Rank ["Ranking Step (rank.py - 5-Minute Clock)"]
        G["Input: candidates.jsonl"]:::rank --> H{"All IDs in cache?"}:::decision

        %% Cached Mode
        H -- "Yes: CACHED MODE" --> I1["Load cache from RAM"]:::rank
        I1 --> K1["Encode JD with BGE"]:::rank
        K1 --> L1["Cosine Similarity via np.dot"]:::rank
        L1 --> M1["Scored Candidate Pool"]:::rank

        %% Hybrid Dynamic Mode
        H -- "No: HYBRID MODE" --> SEP["Split cached vs uncached"]:::rank
        SEP --> CA["Cached: lookup features + embeddings"]:::rank
        SEP --> UC["Uncached: embed on-the-fly + extract_all_features"]:::rank
        CA --> MERGE["Merge scored sets"]:::rank
        UC --> MERGE
        MERGE --> M1

        %% Exclusions & Scoring
        M1 --> N["Exclude Honeypots & IT-Service-Only"]:::filter
        N --> EX["Log exclusion counts"]:::logging
        EX --> O["Hybrid Score: 0.35T + 0.25S + 0.20SK + 0.20B"]:::rank
        O --> MOD["Apply Notice & Location Modifiers"]:::rank
        MOD --> P{"Score ties?"}:::decision

        %% Tie-Breaking & Output
        P -- "Yes" --> Q["Tie-break: candidate_id ascending"]:::filter
        P -- "No" --> R["Sort by score descending"]:::rank
        Q --> S["Assign unique ranks 1-100"]:::rank
        R --> S
        S --> TOP5["Log Top 5 Candidates Preview"]:::logging
        TOP5 --> T["Export team_redrob.csv with reasoning"]:::output
    end

    %% ----------------------------------------------------
    %% SANDBOX UI
    %% ----------------------------------------------------
    subgraph Sandbox ["Sandbox UI (app.py - HuggingFace Spaces)"]
        U1["Upload JSON/JSONL (max 100 candidates)"]:::sandbox --> U2["@st.cache_resource: Load Model + Cache"]:::sandbox
        U2 --> U3["Hybrid Cache Lookup"]:::sandbox
        U3 --> U4["Score & Rank"]:::sandbox
        U4 --> U5["Generate reasoning (top 100 only)"]:::sandbox
        U5 --> U6["Display Table + CSV Download"]:::sandbox
    end

    %% ----------------------------------------------------
    %% ORCHESTRATOR
    %% ----------------------------------------------------
    subgraph Orch ["Pipeline Orchestrator (run_pipeline.py)"]
        O1["Verify Challenge Bundle"]:::logging --> O2["Ensure Cache Exists"]:::logging
        O2 --> O3["Execute rank.py"]:::logging
        O3 --> O4["Run validate_submission.py"]:::logging
        O4 --> O5["Check submission_metadata.yaml"]:::logging
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
