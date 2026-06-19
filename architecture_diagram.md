# 📊 Detailed Pipeline Architecture Diagram

This diagram visualizes the end-to-end data flow, dividing the system into the **Pre-computation Phase** and the **Ranking Step** (supporting both Cached and Dynamic modes). Both phases run 100% offline.

```mermaid
flowchart TD
    %% Styling Definitions
    classDef prep fill:#e0f7fa,stroke:#00acc1,stroke-width:2px,color:#004d40;
    classDef rank fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#4a148c;
    classDef filter fill:#ffebee,stroke:#e53935,stroke-width:2px,color:#b71c1c;
    classDef decision fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef output fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20;

    %% ----------------------------------------------------
    %% PRE-COMPUTATION PHASE
    %% ----------------------------------------------------
    subgraph Prep ["Pre-computation Phase (Run Once)"]
        A["Raw Candidates Pool: 100K JSONL"]:::prep --> B["Preprocess & Clean"]:::prep
        B --> C["Honeypot & IT-Service Check"]:::prep
        C --> D["Compute Feature Scores"]:::prep
        D --> E["BGE Small Text Embedder"]:::prep
        E --> F1["embeddings.npy (153MB Matrix)"]:::prep
        D --> F2["features.json (Feature Scores)"]:::prep
    end

    %% ----------------------------------------------------
    %% RANKING STEP
    %% ----------------------------------------------------
    subgraph Rank ["Ranking Step (5-Minute Clock)"]
        G["Input Candidates File"]:::rank --> H{"Does candidate list match 100K pool?"}:::decision
        
        %% Cached Mode (100K Candidates)
        H -- "Yes" --> I1["Load embeddings.npy & features.json"]:::rank
        I1 --> J1["Load BGE Model in CPU RAM"]:::rank
        J1 --> K1["BGE encodes Job Description text"]:::rank
        K1 --> L1["Calculate Cosine Similarity via NumPy Dot Product (0.05s)"]:::rank
        L1 --> M1["Relevance Score Matrix"]:::rank
        
        %% Dynamic Mode (Sandbox / New Test Set)
        H -- "No" --> I2["Load BGE Model in CPU RAM"]:::rank
        I2 --> J2["Generate BGE embeddings on-the-fly"]:::rank
        J2 --> K2["Compute candidate features on-the-fly"]:::rank
        K2 --> L2["Calculate Cosine Similarity via NumPy Dot Product"]:::rank
        L2 --> M1
        
        %% Hard Exclusions & Post-Scoring
        M1 --> N["Exclude Honeypots & IT-Service-Only"]:::filter
        N --> O["Calculate Hybrid Score (0.35 Title + 0.25 Semantic + 0.20 Skill + 0.20 Behavioral)"]:::rank
        O --> P{"Are there score ties within 1e-6?"}:::decision
        
        %% Tie-Breaking & Output
        P -- "Yes" --> Q["Deterministic tie-breaker (candidate_id ascending)"]:::filter
        P -- "No" --> R["Sort by Score descending"]:::rank
        Q --> S["Assign unique monotonic ranks 1-100"]:::rank
        R --> S
        S --> T["Export ranked_output.csv with offline reasoning"]:::output
    end

    %% Phase Connection
    F1 -.-> I1
    F2 -.-> I1
```

---

### 🎨 Color & Component Legend:
* **Blue Nodes (Teal)**: **Pre-computation Phase** – run once beforehand to compress text profiles into lightweight matrices and feature scores.
* **Purple Nodes (Lavender)**: **Ranking Step** – fast execution blocks that load model, vectors, and compute similarity.
* **Yellow Nodes (Gold)**: **Decision Points** – runtime checks that handle input mode branching and score tie-breaking.
* **Red Nodes (Crimson)**: **Exclusions & Bias Checks** – safety filters that prune honeypot/IT service candidates and enforce deterministic sorting.
* **Green Node (Emerald)**: **Final Output** – the verified, monotonic, 100-row submission CSV.
