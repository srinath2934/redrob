import os
import json
import numpy as np
from tqdm import tqdm
from sentence_transformers import SentenceTransformer
import offline_utils

CANDIDATES_PATH = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
ARTIFACTS_DIR = "artifacts"
BGE_MODEL_DIR = os.path.join(ARTIFACTS_DIR, "bge_model")

def get_candidate_summary_text(candidate):
    profile = candidate.get("profile", {})
    title = profile.get("current_title", "")
    headline = profile.get("headline", "")
    summary = profile.get("summary", "")
    
    # Career history titles only (excluding descriptions to maximize speed and density)
    jobs_summary = []
    for job in candidate.get("career_history", []):
        j_title = job.get("title", "")
        if j_title:
            jobs_summary.append(j_title)
    
    jobs_str = ", ".join(jobs_summary)
    return f"Title: {title}. Headline: {headline}. Summary: {summary}. Past Roles: {jobs_str}"



logger = offline_utils.setup_logging("build_cache")

def main():
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)
    
    # 1. Download and Save BGE Model Locally
    logger.info("Initializing BGE model (BAAI/bge-small-en-v1.5)...")
    if not os.path.exists(BGE_MODEL_DIR):
        logger.info("Downloading BGE small model and saving to local cache...")
        model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        model.save(BGE_MODEL_DIR)
        logger.info(f"Model saved locally at {BGE_MODEL_DIR}")
    else:
        logger.info(f"Local BGE model found at {BGE_MODEL_DIR}. Loading...")
        model = SentenceTransformer(BGE_MODEL_DIR)
        
    logger.info("BGE model loaded successfully.")
    
    # 2. Extract Features and Build Embeddings
    logger.info("Processing candidates pool...")
    features_cache = {}
    candidate_ids = {}
    summaries = []
    
    # Check total lines in candidates file for progress bar
    logger.info("Counting total candidates...")
    total_lines = 100000  # Default expected size
    try:
        with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
            total_lines = sum(1 for _ in f)
        logger.info(f"Total candidates to process: {total_lines}")
    except Exception as e:
        logger.warning(f"Could not count lines: {e}. Defaulting progress tracking.")
        
    # Read candidates line-by-line
    idx = 0
    with open(CANDIDATES_PATH, "r", encoding="utf-8") as f:
        for line in tqdm(f, total=total_lines, desc="Extracting features & preparing summaries"):
            if not line.strip():
                continue
            candidate = json.loads(line)
            cid = candidate.get("candidate_id")
            
            # Extract features
            feats = offline_utils.extract_all_features(candidate)
            features_cache[cid] = feats
            candidate_ids[cid] = idx
            
            # Prepare summary for embedding
            summary_txt = get_candidate_summary_text(candidate)
            summaries.append(summary_txt)
            idx += 1
            
    # Save features cache and ID-to-index mapping
    features_path = os.path.join(ARTIFACTS_DIR, "features.json")
    logger.info(f"Saving features cache to {features_path}...")
    with open(features_path, "w", encoding="utf-8") as fh:
        json.dump(features_cache, fh)
        
    ids_path = os.path.join(ARTIFACTS_DIR, "candidate_ids.json")
    logger.info(f"Saving candidate ID map to {ids_path}...")
    with open(ids_path, "w", encoding="utf-8") as ih:
        json.dump(candidate_ids, ih)
        
    # 3. Generate BGE embeddings in batches
    logger.info("Generating embeddings for all candidates (Batch encoding)...")
    batch_size = 1000
    embeddings_list = []
    
    # SentenceTransformers has built-in batching, but manually splitting enables garbage collection 
    # and progress updates to prevent any memory spikes.
    for i in tqdm(range(0, len(summaries), batch_size), desc="Encoding batches"):
        batch_texts = summaries[i : i + batch_size]
        batch_embeddings = model.encode(batch_texts, batch_size=256, show_progress_bar=False, convert_to_numpy=True)
        embeddings_list.append(batch_embeddings)

        
    all_embeddings = np.vstack(embeddings_list)
    
    # Save embeddings to NumPy disk matrix
    embeddings_path = os.path.join(ARTIFACTS_DIR, "embeddings.npy")
    logger.info(f"Saving embeddings matrix of shape {all_embeddings.shape} to {embeddings_path}...")
    np.save(embeddings_path, all_embeddings)
    
    logger.info("🎉 Pre-computation caching complete! All artifacts generated. 🎉")

if __name__ == "__main__":
    main()
