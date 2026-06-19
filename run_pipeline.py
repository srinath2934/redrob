import os
import sys
import subprocess
import yaml  # If yaml isn't installed, we can fall back to custom parsing

def run_step(name, command):
    print(f"\n--- [STEP] Running: {name} ---")
    print(f"Command: {command}")
    try:
        # Run process and print output in real-time
        result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        print(result.stdout)
        print(f"--- [SUCCESS] {name} completed successfully. ---\n")
        return True
    except subprocess.CalledProcessError as e:
        print(e.stdout)
        print(f"--- [FAILURE] {name} failed with exit code {e.returncode}. ---\n")
        return False

def check_files():
    print("\n--- [STEP] Checking Bundle Files ---")
    required_files = [
        r"job_description.docx",
        r"submission_spec.docx",
        r"redrob_signals_doc.docx",
        r"candidates.jsonl",
        r"validate_submission.py"
    ]
    dir_path = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge"
    
    missing = []
    for f in required_files:
        path = os.path.join(dir_path, f)
        if not os.path.exists(path):
            missing.append(f)
            
    if missing:
        print(f"Missing files in challenge directory: {missing}")
        return False
    
    print("All required hackathon bundle files are present.")
    return True

def main():
    # 1. Check files
    if not check_files():
        sys.exit(1)
        
    # 2. Run the ranker
    # We will use rank.py to read the unzipped candidates.jsonl and output participant_id.csv
    # For now, let's output a mock file name to test the pipeline (e.g. team_redrob.csv)
    # The actual team name will be populated in rank.py
    csv_filename = "team_redrob.csv"
    ranker_cmd = f"python rank.py --candidates \"d:\\redrob\\[PUB] India_runs_data_and_ai_challenge\\India_runs_data_and_ai_challenge\\candidates.jsonl\" --out {csv_filename}"
    
    if not run_step("Candidate Ranker", ranker_cmd):
        print("Pipeline aborted at Ranking stage.")
        sys.exit(1)
        
    # 3. Validate Submission
    validator_cmd = f"python \"d:\\redrob\\[PUB] India_runs_data_and_ai_challenge\\India_runs_data_and_ai_challenge\\validate_submission.py\" {csv_filename}"
    if not run_step("Submission Validator", validator_cmd):
        print("Pipeline aborted at Validation stage. The CSV format is invalid.")
        sys.exit(1)
        
    # 4. Verify submission_metadata.yaml
    print("\n--- [STEP] Verifying submission_metadata.yaml ---")
    metadata_path = "submission_metadata.yaml"
    if not os.path.exists(metadata_path):
        print(f"[WARNING] submission_metadata.yaml not found at repo root. Copying from template...")
        template_path = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\submission_metadata_template.yaml"
        if os.path.exists(template_path):
            with open(template_path, 'r', encoding='utf-8') as src, open(metadata_path, 'w', encoding='utf-8') as dest:
                dest.write(src.read())
            print(f"Copied template to {metadata_path}. Please fill in your team details.")
        else:
            print("[ERROR] Metadata template not found.")
            sys.exit(1)
    else:
        print("submission_metadata.yaml is present.")
        
    print("\n==============================================")
    print("🎉 PIPELINE RUN COMPLETED SUCCESSFULLY! 🎉")
    print("Your submission CSV and metadata are ready.")
    print("==============================================")

if __name__ == "__main__":
    main()
