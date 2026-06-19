# 📊 Detailed Pipeline Architecture Diagram

This diagram visualizes the end-to-end data flow, dividing the system into the **Offline Pre-computation Phase** and the **Online Ranking Phase** (supporting both Cached and Dynamic modes).

```mermaid
flowchart TD
    %% Styling Definitions
    classDef offline fill:#e0f7fa,stroke:#00acc1,stroke-width:2px,color:#004d40;
    classDef online fill:#f3e5f5,stroke:#8e24aa,stroke-width:2px,color:#4a148c;
    classDef filter fill:#ffebee,stroke:#e53935,stroke-width:2px,color:#b71c1c;
    classDef decision fill:#fffde7,stroke:#fbc02d,stroke-width:2px,color:#f57f17;
    classDef output fill:#e8f5e9,stroke:#43a047,stroke-width:2px,color:#1b5e20;

    %% ----------------------------------------------------
    %% OFFLINE PHASE
    %% ----------------------------------------------------
    subgraph Offline ["Offline Pre-computation Phase"]
        A[Raw Candidates Pool: 100K JSONL]:::offline --> B[Preprocess & Clean]:::offline
        B --> C[Honeypot & IT-Service Check]:::offline
        C --> D[Compute Feature Scores]:::offline
        D --> E[BGE Small Text Embedder]:::offline
        E --> F1[embeddings.npy\n153MB Matrix]:::offline
        D --> F2[features.json\nFeature Scores]:::offline
    end

    %% ----------------------------------------------------
    %% ONLINE PHASE
    %% ----------------------------------------------------
    subgraph Online ["Online Ranking Phase (5-Minute Clock)"]
        G[Input Candidates File]:::online --> H{Does candidate list\nmatch our 100K pool?}:::decision
        
        %% Cached Mode (100K Candidates)
        H -- Yes --> I1[Load embeddings.npy & features.json]:::online
        I1 --> J1[Load BGE Model in CPU RAM]:::online
        J1 --> K1[BGE encodes Job Description text]:::online
        K1 --> L1["Calculate Cosine Similarity\nvia Numpy Dot Product (0.05s)"]:::online
        L1 --> M1[Relevance Score Matrix]:::online
        
        %% Dynamic Mode (Sandbox / New Test Set)
        H -- No --> I2[Load BGE Model in CPU RAM]:::online
        I2 --> J2[Generate BGE embeddings for sample on-the-fly]:::online
        J2 --> K2[Compute candidate features on-the-fly]:::online
        K2 --> L2[Calculate Cosine Similarity via Numpy Dot Product]:::online
        L2 --> M1
        
        %% Hard Exclusions & Post-Scoring
        M1 --> N[Exclude Honeypots & IT-Service-Only]:::filter
        N --> O["Calculate Hybrid Score:\nScore = 0.35*Title + 0.25*Semantic\n+ 0.20*Skill/Exp + 0.20*Behavioral"]:::online
        O --> P{Are there score ties\nwithin 1e-6?}:::decision
        
        %% Tie-Breaking & Output
        P -- Yes --> Q[deterministic tie-breaker:\nSort by candidate_id ascending]:::filter
        P -- No --> R[Sort by Score descending]:::online
        Q --> S[Assign unique monotonic ranks 1-100]:::online
        R --> S
        S --> T[Export ranked_output.csv]:::output
    end

    %% Phase Connection
    F1 -.-> I1
    F2 -.-> I1

```

---

### 🎨 Color & Component Legend:
* **Blue Nodes (Teal)**: **Offline Pre-computation** – run once beforehand to compress text profiles into lightweight matrices and feature scores.
* **Purple Nodes (Lavender)**: **Online Ranking Pipeline** – fast execution blocks that load model, vectors, and compute similarity.
* **Yellow Nodes (Gold)**: **Decision Points** – runtime checks that handle input mode branching and score tie-breaking.
* **Red Nodes (Crimson)**: **Exclusions & Bias Checks** – safety filters that prune honeypot/IT service candidates and enforce deterministic sorting.
* **Green Node (Emerald)**: **Final Output** – the verified, monotonic, 100-row submission CSV.
