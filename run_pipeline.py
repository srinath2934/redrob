import os
import sys
import time
import subprocess
import offline_utils

logger = offline_utils.setup_logging("run_pipeline")

# Config
CANDIDATES_PATH = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\candidates.jsonl"
VALIDATOR_PATH = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\validate_submission.py"
OUTPUT_CSV = "team_srinath.csv"

def verify_challenge_bundle():
    logger.info("--- [STEP] Verifying Challenge Bundle Files ---")
    required = [
        CANDIDATES_PATH,
        VALIDATOR_PATH
    ]
    missing = []
    for p in required:
        if not os.path.exists(p):
            missing.append(p)
            
    if missing:
        logger.error(f"Missing critical challenge bundle files: {missing}")
        return False
    logger.info("All critical challenge bundle files are present.")
    return True

def ensure_cache_exists():
    logger.info("--- [STEP] Checking Offline Cache Status ---")
    cache_files = [
        "artifacts/embeddings.npy",
        "artifacts/features.json",
        "artifacts/candidate_ids.json",
        "artifacts/bge_model"
    ]
    
    missing_cache = [f for f in cache_files if not os.path.exists(f)]
    
    if missing_cache:
        logger.info(f"Cache is incomplete (missing: {missing_cache}). Launching pre-computation...")
        start_time = time.time()
        # Execute build_cache.py
        result = subprocess.run([sys.executable, "build_cache.py"], check=True)
        duration = time.time() - start_time
        logger.info(f"Pre-computation caching finished in {duration:.2f} seconds.")
    else:
        logger.info("Offline cache is complete and verified on disk.")

def execute_ranker():
    logger.info("--- [STEP] Executing Candidate Ranker (Timing 5-Min Limit) ---")
    start_time = time.time()
    
    # Run rank.py in Cached Mode (since cache is guaranteed to exist now)
    cmd = [
        sys.executable,
        "rank.py",
        "--candidates", CANDIDATES_PATH,
        "--out", OUTPUT_CSV
    ]
    
    logger.info(f"Command: {' '.join(cmd)}")
    result = subprocess.run(cmd, check=True)
    
    duration = time.time() - start_time
    logger.info("--- [SUCCESS] Ranking step finished. ---")
    logger.info(f"Ranking execution time: {duration:.2f} seconds (Limit: 300.0s)")
    if duration > 300.0:
        logger.warning("Pipeline exceeded the 5-minute wall-clock constraint!")
    else:
        logger.info("Pipeline is well within the 5-minute wall-clock constraint.")
    return True

def validate_submission():
    logger.info("--- [STEP] Running Format Validator ---")
    cmd = [
        sys.executable,
        VALIDATOR_PATH,
        OUTPUT_CSV
    ]
    logger.info(f"Command: {' '.join(cmd)}")
    try:
        subprocess.run(cmd, check=True)
        logger.info("--- [SUCCESS] Submission CSV passed all formatting constraints. ---")
        return True
    except subprocess.CalledProcessError as e:
        logger.error("--- [FAILURE] Submission CSV failed format validation. ---")
        return False

def verify_metadata():
    logger.info("--- [STEP] Verifying submission_metadata.yaml ---")
    metadata_path = "submission_metadata.yaml"
    template_path = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\submission_metadata_template.yaml"
    
    if not os.path.exists(metadata_path):
        logger.warning(f"{metadata_path} not found at repo root. Recreating from template...")
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as src, open(metadata_path, 'w', encoding='utf-8') as dest:
                dest.write(src.read())
            logger.info(f"Copied template to {metadata_path}. Please update with your metadata.")
        else:
            logger.error("Metadata template not found in bundle.")
            return False
    else:
        logger.info("submission_metadata.yaml is present.")
    return True

def main():
    logger.info("==============================================")
    logger.info("[START] REDROB RANKING PIPELINE ORCHESTRATOR")
    logger.info("==============================================")
    
    if not verify_challenge_bundle():
        sys.exit(1)
        
    # Build cache if it doesn't exist
    ensure_cache_exists()
    
    # Run ranking step
    if not execute_ranker():
        sys.exit(1)
        
    # Validate the CSV
    if not validate_submission():
        sys.exit(1)
        
    # Recreate metadata template if missing
    verify_metadata()
    
    logger.info("==============================================")
    logger.info("[SUCCESS] PIPELINE RUN COMPLETED SUCCESSFULLY!")
    logger.info("Your submission CSV and metadata are ready for upload.")
    logger.info("==============================================")

if __name__ == "__main__":
    main()
