import os
import json
import csv
import io
import pandas as pd
import numpy as np
import streamlit as st
from sentence_transformers import SentenceTransformer
import offline_utils
import rank

# Set page configurations
st.set_page_config(
    page_title="Redrob Talent Intel Sandbox",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Premium Sleek CSS Styles (Dark Mode, Card layouts, Custom Buttons)
st.markdown("""
<style>
    /* Main App Background */
    .stApp {
        background: linear-gradient(135deg, #0f0c1b 0%, #15102a 50%, #06020f 100%);
        color: #e2e1e9;
        font-family: 'Inter', sans-serif;
    }
    
    /* Title and Header Styles */
    h1, h2, h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    
    .main-title {
        font-size: 3rem !important;
        background: linear-gradient(45deg, #00f2fe 0%, #4facfe 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem !important;
        text-shadow: 0px 4px 20px rgba(0, 242, 254, 0.2);
    }
    
    .subtitle {
        font-size: 1.1rem;
        color: #a09eb5;
        margin-bottom: 2.5rem;
    }
    
    /* Metrics / Cards styling */
    .metric-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        transition: all 0.3s ease;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.4);
        backdrop-filter: blur(5px);
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        border-color: rgba(0, 242, 254, 0.4);
        box-shadow: 0 8px 30px rgba(0, 242, 254, 0.1);
    }
    
    .metric-title {
        color: #8a88a0;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.1rem;
        margin-bottom: 0.5rem;
    }
    
    .metric-value {
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
    }
    
    /* File Uploader styling */
    .stFileUploader {
        border: 2px dashed rgba(79, 172, 254, 0.3);
        border-radius: 12px;
        padding: 1.5rem;
        background: rgba(255, 255, 255, 0.02);
    }
    
    /* Sidebar Details */
    .sidebar-section {
        background: rgba(255, 255, 255, 0.02);
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
        border: 1px solid rgba(255, 255, 255, 0.03);
    }
    
    /* Style Table rows */
    .stTable {
        background-color: transparent !important;
    }
    
    /* Table Header customization */
    thead th {
        background-color: rgba(79, 172, 254, 0.1) !important;
        color: #00f2fe !important;
        font-weight: 600 !important;
    }
    
    /* Highlights top candidates */
    .candidate-rank-1 {
        background: linear-gradient(90deg, rgba(255, 215, 0, 0.1) 0%, transparent 100%) !important;
        border-left: 4px solid #ffd700 !important;
    }
    .candidate-rank-2 {
        background: linear-gradient(90deg, rgba(192, 192, 192, 0.1) 0%, transparent 100%) !important;
        border-left: 4px solid #c0c0c0 !important;
    }
</style>
""", unsafe_allow_html=True)

logger = offline_utils.setup_logging("app")

@st.cache_resource
def load_ranking_resources():
    # Load Model
    bge_dir = "artifacts/bge_model"
    if os.path.exists(bge_dir):
        logger.info(f"Loading local BGE model from {bge_dir}...")
        model = SentenceTransformer(bge_dir, device="cpu")
    else:
        logger.info("Local BGE model not found. Downloading BAAI/bge-small-en-v1.5...")
        model = SentenceTransformer("BAAI/bge-small-en-v1.5", device="cpu")

    cached_ids = {}
    features_cache = {}
    embeddings_matrix = None
    
    ids_path = "artifacts/candidate_ids.json"
    features_path = "artifacts/features.json"
    embeddings_path = "artifacts/embeddings.npy"
    
    if os.path.exists(ids_path) and os.path.exists(features_path) and os.path.exists(embeddings_path):
        try:
            logger.info("Loading pre-computed cache files for Streamlit engine...")
            with open(ids_path, "r", encoding="utf-8") as ih:
                cached_ids = json.load(ih)
            with open(features_path, "r", encoding="utf-8") as fh:
                features_cache = json.load(fh)
            embeddings_matrix = np.load(embeddings_path)
            logger.info("Cache files loaded successfully.")
        except Exception as e:
            logger.error(f"Error loading cache files in app: {e}")
    else:
        logger.warning("Cache files not found. App will run in Dynamic Mode (On-the-fly execution).")
        
    return model, cached_ids, features_cache, embeddings_matrix

def compute_semantic_title_score(model, title_text, target_title_vector):
    if not title_text or not isinstance(title_text, str):
        return 0.0
    query = "Represent this sentence for searching relevant passages: " + title_text.strip()
    title_vector = model.encode(query, convert_to_numpy=True)
    norm = np.linalg.norm(title_vector)
    if norm == 0:
        return 0.0
    title_vector = title_vector / norm
    similarity = float(np.dot(title_vector, target_title_vector))
    # Normalize relative to 0.75 (expected similarity of a perfect match) and raise to power of 10
    score = (min(1.0, max(0.0, similarity / 0.75)) ** 10) * 100.0
    return score

# Helper function to load local assets or default JD
def get_jd_text():
    jd_file = "job_description.txt"
    challenge_jd = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\job_description.txt"
    
    if os.path.exists(jd_file):
        with open(jd_file, "r", encoding="utf-8") as f:
            return f.read()
    elif os.path.exists(challenge_jd):
        with open(challenge_jd, "r", encoding="utf-8") as f:
            return f.read()
    else:
        return "Founding Senior AI Engineer - 5-9 years, Pune/Noida, ML retrieval search."

def run_ranking_engine(uploaded_candidates_list, jd_text):
    model, cached_ids, features_cache, embeddings_matrix = load_ranking_resources()
        
    jd_vector = model.encode(jd_text, convert_to_numpy=True)
    jd_vector = jd_vector / np.linalg.norm(jd_vector)
    
    # Precompute target title vector with BGE prefix
    target_title = "Represent this sentence for searching relevant passages: Senior AI Engineer, Machine Learning retrieval search ranking recommendation systems"
    target_vector = model.encode(target_title, convert_to_numpy=True)
    target_vector = target_vector / np.linalg.norm(target_vector)
    
    use_cache = len(cached_ids) > 0 and features_cache and embeddings_matrix is not None
    
    scored_candidates = []
    
    # Separate cached vs uncached candidates
    uncached_indices = []
    uncached_summaries = []
    
    for i, cand in enumerate(uploaded_candidates_list):
        cid = cand.get("candidate_id")
        if use_cache and cid in cached_ids:
            continue
        else:
            uncached_indices.append(i)
            uncached_summaries.append(rank.get_candidate_summary_text(cand))
            
    # Generate embeddings for uncached candidates in a single optimized batch
    uncached_embeddings = {}
    if uncached_summaries:
        logger.info(f"Encoding {len(uncached_summaries)} uncached candidates on-the-fly...")
        encoded = model.encode(uncached_summaries, batch_size=256, show_progress_bar=False, convert_to_numpy=True)
        for idx_in_uncached, orig_idx in enumerate(uncached_indices):
            uncached_embeddings[orig_idx] = encoded[idx_in_uncached]
            
    for i, cand in enumerate(uploaded_candidates_list):
        cid = cand.get("candidate_id")
        
        # Fetch features
        if use_cache and cid in cached_ids:
            feats = features_cache[cid]
        else:
            feats = offline_utils.extract_all_features(cand)
            # Overwrite title_score semantically using BGE model
            title = cand.get("profile", {}).get("current_title", "")
            feats["title_score"] = compute_semantic_title_score(model, title, target_vector)
            
        # Fetch embedding
        if use_cache and cid in cached_ids:
            idx = cached_ids[cid]
            cand_vector = embeddings_matrix[idx]
        else:
            cand_vector = uncached_embeddings[i]
            
        cand_vector = cand_vector / np.linalg.norm(cand_vector)
        similarity = float(np.dot(cand_vector, jd_vector))
        semantic_score = ((similarity - 0.70) / 0.15) * 100.0
        
        title_score = feats.get("title_score", 30.0)
        exp_score = feats.get("experience_score", 0.0)
        skills_score = feats.get("skills_score", 0.0)
        behavioral_score = feats.get("behavioral_score", 0.0)
        m_notice = feats.get("notice_modifier", 1.0)
        m_location = feats.get("location_modifier", 1.0)
        m_availability = feats.get("availability_modifier", 1.0)
        m_work_mode = feats.get("work_mode_modifier", 1.0)
        m_salary = feats.get("salary_modifier", 1.0)
        m_trust = feats.get("trust_modifier", 1.0)
        m_consistency = feats.get("consistency_modifier", 1.0)
        
        # Multiplicative Title Gate Formula:
        title_mult = title_score / 100.0
        core_score = (0.55 * semantic_score) + (0.25 * (0.5 * skills_score + 0.5 * exp_score)) + (0.20 * behavioral_score)
        composite = title_mult * core_score
        # Apply logistics and consistency modifiers
        final_score = composite * m_notice * m_location * m_availability * m_work_mode * m_salary * m_trust * m_consistency
            
        scored_candidates.append({
            "candidate": cand,
            "score": final_score,
            "features": feats
        })
        
    # Sort and deterministic tie break
    scored_candidates.sort(key=lambda x: (-round(x["score"] / 100.0, 4), x["candidate"]["candidate_id"]))
    return scored_candidates

# --- App Header ---
st.markdown("<h1 class='main-title'>🤖 Redrob Talent Intelligence</h1>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>Founding AI Engineer - Sandbox Discovery Environment</div>", unsafe_allow_html=True)

# --- Sidebar Layout ---
st.sidebar.markdown("### 🛠️ Sandbox Control Panel")
st.sidebar.markdown("<div class='sidebar-section'><b>Local Engine Info</b><br>BGE Small Embedder v1.5<br>CPU-only execution</div>", unsafe_allow_html=True)

# Add sample data load button
load_sample = st.sidebar.button("📂 Load Hackathon Sample (50 Candidates)")

st.sidebar.markdown("### 📋 Rules Compliance")
st.sidebar.markdown("- **0% Honeypot Target**<br>- **IT Consulting Exclusion**<br>- **Deterministic Tie-Breaking**<br>- **Factual Offline Reasoning**", unsafe_allow_html=True)

# --- Main Layout ---
col_left, col_right = st.columns([1, 2])

with col_left:
    st.markdown("### 💼 Job Description Details")
    jd_text = get_jd_text()
    # Read first 12 lines for preview
    jd_lines = jd_text.split('\n')
    jd_preview = "\n".join(jd_lines[:15]) + "\n..."
    st.text_area("Founding Team Profile", value=jd_preview, height=260, disabled=True)
    
    st.markdown("### 📤 Upload Candidate Pool")
    uploaded_file = st.file_uploader("Upload candidates.json or candidates.jsonl", type=["json", "jsonl"])

candidates_data = []

# Resolve data source
if uploaded_file is not None:
    content = uploaded_file.read().decode("utf-8")
    try:
        if content.strip().startswith("["):
            candidates_data = json.loads(content)
        else:
            candidates_data = []
            for line in content.split("\n"):
                if line.strip():
                    candidates_data.append(json.loads(line))
        st.success(f"Successfully loaded {len(candidates_data)} candidates.")
    except Exception as e:
        st.error(f"Error parsing candidates file: {e}")
elif load_sample:
    sample_path = "sample_candidates.json"
    if os.path.exists(sample_path):
        with open(sample_path, "r", encoding="utf-8") as sf:
            candidates_data = json.load(sf)
        st.success(f"Successfully loaded {len(candidates_data)} sample candidates.")
    else:
        st.error("Sample candidates file not found locally.")

with col_right:
    st.markdown("### 🏆 Discovery & Ranking Results")
    
    if len(candidates_data) > 0:
        with st.spinner("Processing embeddings and scoring candidates..."):
            try:
                scored = run_ranking_engine(candidates_data, jd_text)
                
                # Print Metrics
                m_col1, m_col2, m_col3 = st.columns(3)
                
                total_cand = len(scored)
                honeypots = sum(1 for c in scored if c["features"]["is_honeypot"])
                it_services = sum(1 for c in scored if c["features"]["is_it_service_only"])
                
                with m_col1:
                    st.markdown(f"<div class='metric-card'><div class='metric-title'>Processed Pool</div><div class='metric-value'>{total_cand}</div></div>", unsafe_allow_html=True)
                with m_col2:
                    st.markdown(f"<div class='metric-card'><div class='metric-title'>Traps Identified</div><div class='metric-value'>{honeypots}</div></div>", unsafe_allow_html=True)
                with m_col3:
                    st.markdown(f"<div class='metric-card'><div class='metric-title'>IT Services Scaled</div><div class='metric-value'>{it_services}</div></div>", unsafe_allow_html=True)
                
                # Build CSV
                csv_buffer = io.StringIO()
                writer = csv.writer(csv_buffer, quoting=csv.QUOTE_MINIMAL)
                writer.writerow(["candidate_id", "rank", "score", "reasoning"])
                
                table_rows = []
                
                # CSV outputs exactly 100 rows, or caps at candidate count if less
                csv_limit = 100
                for r_idx in range(csv_limit):
                    if r_idx < len(scored):
                        item = scored[r_idx]
                        cid = item["candidate"]["candidate_id"]
                        score = round(item["score"] / 100.0, 4)
                        rank_num = r_idx + 1
                        reasoning = rank.generate_reasoning(item["candidate"], rank_num, score, item["features"])
                        
                        # Save to CSV string
                        writer.writerow([cid, rank_num, f"{score:.4f}", reasoning])
                            
                        # Save to preview table (first 10)
                        if r_idx < 10:
                            table_rows.append({
                                "Rank": rank_num,
                                "Candidate ID": cid,
                                "Current Title": item["features"]["raw_profile"]["current_title"],
                                "Exp (Yrs)": item["features"]["raw_profile"]["years_of_experience"],
                                "Final Score": f"{score:.4f}",
                                "Reasoning": reasoning
                            })
                    else:
                        # Pad CSV if less than 100 candidates input
                        pad_cid = f"CAND_{9999999-r_idx:07d}"
                        pad_rank = r_idx + 1
                        pad_score = "0.0000"
                        pad_reason = "Placeholder candidate due to small input list."
                        writer.writerow([pad_cid, pad_rank, pad_score, pad_reason])
                
                # Show results table
                df_preview = pd.DataFrame(table_rows)
                st.table(df_preview)
                
                # Provide CSV Download
                csv_data = csv_buffer.getvalue()
                st.download_button(
                    label="📥 Download Ranked CSV Submission",
                    data=csv_data,
                    file_name="team_redrob.csv",
                    mime="text/csv"
                )
                
            except Exception as e:
                st.error(f"Error during ranking execution: {e}")
                import traceback
                st.text(traceback.format_exc())
    else:
        st.info("Upload a candidates file or click 'Load Hackathon Sample' in the sidebar to visualize results.")
