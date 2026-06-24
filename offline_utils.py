import os
import sys
import json
import logging
from datetime import datetime

def setup_logging(name, log_filename="pipeline.log"):
    os.makedirs(os.path.join("artifacts", "logs"), exist_ok=True)
    log_path = os.path.join("artifacts", "logs", log_filename)
    
    logger = logging.getLogger(name)
    # Ensure we don't add duplicate handlers if this is called multiple times
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        
        # File Handler
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        
        # Console Handler (writes to stdout)
        try:
            if hasattr(sys.stdout, 'reconfigure'):
                sys.stdout.reconfigure(errors='backslashreplace')
        except Exception:
            pass
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(logging.INFO)
        
        # Format
        formatter = logging.Formatter("[%(asctime)s] %(name)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        
        logger.addHandler(fh)
        logger.addHandler(ch)
        
    return logger

# Reference date from JD and architecture documentation
REF_DATE = datetime(2026, 6, 17)


IT_SERVICE_COMPANIES = {
    "tcs", "infosys", "wipro", "accenture", "cognizant", "capgemini",
    "l&t", "larsen & toubro", "tech mahindra", "mindtree", "hcl"
}

def parse_date(date_str):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None

def calculate_duration_months(start_str, end_str, is_current):
    start_date = parse_date(start_str)
    if not start_date:
        return 0
    end_date = parse_date(end_str) if not is_current else REF_DATE
    if not end_date:
        end_date = REF_DATE
    
    # Calculate difference in months
    diff_years = end_date.year - start_date.year
    diff_months = end_date.month - start_date.month
    total_months = diff_years * 12 + diff_months
    return max(0, total_months)

# Non-software engineering and non-technical disciplines that should never rank for AI roles
NON_TECH_TRAP_TITLES = {
    "civil", "mechanical", "chemical", "electrical", "aerospace",
    "graphic", "designer", "illustrator", "creative director",
    "brand", "content writer", "copywriter",
    "finance", "accountant", "financial analyst",
    "legal", "lawyer", "attorney", "paralegal",
    "supply chain", "procurement", "logistics",
    "customer support", "customer service",
    "operations manager", "project manager",
}

def check_honeypot(candidate):
    reasons = []
    
    # 1. Expert Skill Inflation
    skills = candidate.get("skills", [])
    expert_zero_dur = 0
    for s in skills:
        prof = s.get("proficiency", "").lower()
        dur = s.get("duration_months", 0)
        if prof == "expert" and dur == 0:
            expert_zero_dur += 1
    if expert_zero_dur >= 10:
        reasons.append(f"expert_skill_inflation (count={expert_zero_dur})")
        
    # 2 & 3. Job Duration Anomaly & Future Dates
    career_history = candidate.get("career_history", [])
    total_career_months = 0
    has_future_date = False
    has_duration_anomaly = False
    
    for job in career_history:
        start_str = job.get("start_date")
        end_str = job.get("end_date")
        is_current = job.get("is_current", False)
        stated_dur = job.get("duration_months", 0)
        
        start_date = parse_date(start_str)
        end_date = parse_date(end_str) if not is_current else REF_DATE
        if not end_date:
            end_date = REF_DATE
            
        if start_date and start_date > REF_DATE:
            has_future_date = True
        if end_date and end_date > REF_DATE:
            has_future_date = True
            
        calc_dur = calculate_duration_months(start_str, end_str, is_current)
        total_career_months += calc_dur
        
        if abs(calc_dur - stated_dur) > 3:
            has_duration_anomaly = True
            
    if has_future_date:
        reasons.append("future_dates_detected")
    if has_duration_anomaly:
        reasons.append("job_duration_anomaly")
        
    # 4. Skill Duration Over-inflation
    has_skill_inflation = False
    for s in skills:
        dur = s.get("duration_months", 0)
        if dur > total_career_months + 12:
            has_skill_inflation = True
            break
    if has_skill_inflation:
        reasons.append("skill_duration_over_inflation")

    # 5. Title-Summary Mismatch (Keyword Stuffer Trap)
    # Catches candidates whose summary template references an unrelated role
    profile = candidate.get("profile", {})
    current_title = profile.get("current_title", "").lower()
    summary = profile.get("summary", "").lower()
    headline = profile.get("headline", "").lower()
    
    # Common injected mismatch patterns in honeypot summaries
    mismatch_patterns = [
        ("marketing manager", ["marketing", "sales", "brand"]),
        ("customer support", ["support", "customer", "service"]),
        ("graphic designer", ["graphic", "design", "visual", "illustrat"]),
        ("content writer", ["content", "writing", "copywrite"]),
        ("sales manager", ["sales", "revenue", "business development"]),
        ("hr manager", ["hr", "human resource", "recruitment", "talent acquisition"]),
    ]
    
    for inject_keyword, valid_title_terms in mismatch_patterns:
        if inject_keyword in summary:
            # Summary mentions an irrelevant role - check if title matches
            title_matches = any(term in current_title for term in valid_title_terms)
            if not title_matches:
                reasons.append(f"summary_title_mismatch (summary mentions '{inject_keyword}' but title is '{profile.get('current_title', '')}'")
                break
        
    return len(reasons) > 0, reasons

def check_it_service_only(candidate):
    career_history = candidate.get("career_history", [])
    if not career_history:
        return False
        
    for job in career_history:
        company = job.get("company", "").lower()
        is_it_service = False
        for svc in IT_SERVICE_COMPANIES:
            if svc in company:
                is_it_service = True
                break
        if not is_it_service:
            # Found at least one job at a non-IT service company
            return False
            
    return True

def calculate_title_score(title):
    # This is a placeholder default. The actual title score is computed
    # semantically using the BGE model in build_cache.py, rank.py, and app.py.
    return 30.0

def calculate_experience_score(profile, skills_count, is_it_service_only=False):
    years = profile.get("years_of_experience", 0)
    github_activity_score = profile.get("github_activity_score", 0)  # parsed from profile/signals later
    current_title = profile.get("current_title", "").lower()
    
    score = 100.0
    if years < 6.0:
        score = max(0.0, 100.0 - (6.0 - years) * 40.0)
    elif years > 8.0:
        # Hands-on Check: if active builder, exempt from decay
        is_management = any(kw in current_title for kw in ["vp", "director", "manager", "architect", "lead"])
        if github_activity_score >= 30 or skills_count >= 15 or not is_management:
            score = 100.0
        else:
            score = max(0.0, 100.0 - (years - 8.0) * 15.0)

    # 1. Senior No-Code Penalty (Rule 3: Senior title but no production code written in last 18 months)
    if years >= 5.0 and github_activity_score <= 10:
        score *= 0.70  # 30% penalty for no recent hands-on code activity
        
    # 2. IT Service Penalty (Rule 4: Only worked at IT consulting firms for ENTIRE career)
    if is_it_service_only:
        score *= 0.85  # 15% penalty for lack of product company experience
        
    return score

def calculate_skills_score(skills):
    if not skills:
        return 0.0
        
    core_retrieval = {
        "pinecone", "milvus", "faiss", "qdrant", "weaviate", "bge", "e5",
        "vector search", "dense retrieval", "sparse retrieval", "ann search",
        "embedding model", "sentence transformer", "vector db", "vector database"
    }
    core_ranking = {
        "learning-to-rank", "ndcg", "map", "mrr", "ranking", "hybrid search",
        "elasticsearch", "solr", "opensearch", "lexical search", "bm25",
        "information retrieval", "ir evaluation"
    }
    core_ml = {
        "nlp", "machine learning", "deep learning", "pytorch", "huggingface", "fine-tuning",
        "recommendation systems", "mlflow", "kubeflow", "spark", "distributed training",
        "transformer", "bert", "llm", "embeddings", "semantic search", "a/b testing",
        "tensorflow", "scikit-learn", "xgboost"
    }
    
    total_score = 0.0
    for s in skills:
        name_lower = s.get("name", "").lower()
        
        # 1. Get weight based on category
        weight = 0.0
        if any(term in name_lower for term in core_retrieval):
            weight = 1.0
        elif any(term in name_lower for term in core_ranking):
            weight = 0.8
        elif any(term in name_lower for term in core_ml):
            weight = 0.5
            
        if weight == 0.0:
            continue
            
        # 2. Get proficiency multiplier
        prof = s.get("proficiency", "").lower()
        prof_mult = 0.5  # default
        if prof == "expert":
            prof_mult = 1.0
        elif prof == "advanced":
            prof_mult = 0.8
        elif prof == "intermediate":
            prof_mult = 0.5
        elif prof == "beginner":
            prof_mult = 0.2
            
        # 3. Get duration multiplier
        dur = s.get("duration_months", 0)
        dur_mult = min(1.0, dur / 24.0)  # caps at 24 months (2 years)
        
        total_score += (weight * prof_mult * dur_mult)
        
    # Scale and cap at 100.0
    return min(100.0, total_score * 25.0)

def calculate_behavioral_score(signals):
    # 1. GitHub Score
    github = signals.get("github_activity_score", 0)
    s_github = float(github) if github != -1 else 0.0
    
    # 2. Responsiveness Score (uses recruiter_response_rate and avg_response_time_hours)
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    resp_time = signals.get("avg_response_time_hours", 0.0)
    s_resp_rate = resp_rate * 100.0
    s_resp_time = max(0.0, 100.0 - (resp_time * 2.0))
    s_responsiveness = (s_resp_rate * 0.6) + (s_resp_time * 0.4)
    
    # 3. Activity Recency Score (uses last_active_date)
    last_active_str = signals.get("last_active_date", "")
    last_active_dt = parse_date(last_active_str)
    if last_active_dt:
        days_inactive = (REF_DATE - last_active_dt).days
        if days_inactive <= 30:
            s_activity = 100.0
        elif days_inactive <= 90:
            s_activity = 70.0
        elif days_inactive <= 180:
            s_activity = 40.0
        else:
            s_activity = 0.0
    else:
        s_activity = 0.0
        
    # 4. Platform Reliability Score (uses interview_completion_rate and offer_acceptance_rate)
    completion_rate = signals.get("interview_completion_rate", 0.0) * 100.0
    acceptance = signals.get("offer_acceptance_rate", 0.0)
    acceptance_rate = (acceptance * 100.0) if acceptance != -1 else 70.0
    s_reliability = (completion_rate + acceptance_rate) / 2.0
    
    # 5. Recruiter Demand & Active Intent Score (uses views, saves, search appearance, applications)
    views = signals.get("profile_views_received_30d", 0)
    saves = signals.get("saved_by_recruiters_30d", 0)
    searches = signals.get("search_appearance_30d", 0)
    apps = signals.get("applications_submitted_30d", 0)
    s_views = min(100.0, views * 4.0)
    s_saves = min(100.0, saves * 10.0)
    s_searches = min(100.0, searches * 1.0)
    s_apps = min(100.0, apps * 10.0)
    s_demand = (s_views + s_saves + s_searches + s_apps) / 4.0
    
    # Weighted Sum of behavioral groups
    total = (0.25 * s_github) + (0.25 * s_responsiveness) + (0.20 * s_activity) + (0.15 * s_reliability) + (0.15 * s_demand)
    return total

def calculate_logistics_modifiers(signals, profile):
    # 1. Notice Period Modifier
    notice_days = signals.get("notice_period_days", 0)
    if notice_days <= 30:
        m_notice = 1.0
    elif notice_days <= 60:
        m_notice = 0.90
    elif notice_days <= 90:
        m_notice = 0.75
    else:
        m_notice = 0.40
        
    # 2. Location Fit Modifier
    country = profile.get("country", "").lower()
    location = profile.get("location", "").lower()
    willing_relocate = signals.get("willing_to_relocate", False)
    
    is_tier_1_city = any(city in location for city in ["bangalore", "mumbai", "delhi", "gurgaon", "hyderabad", "noida", "pune"])
    
    if country != "india":
        m_location = 0.40 if willing_relocate else 0.10
    else:
        if "pune" in location or "noida" in location:
            m_location = 1.0
        elif is_tier_1_city:
            m_location = 0.95 if willing_relocate else 0.60
        else:
            m_location = 0.50 if willing_relocate else 0.30
            
    # 3. Availability Modifier
    m_availability = 1.0 if signals.get("open_to_work_flag", True) else 0.90
    
    # 4. Preferred Work Mode Modifier (JD wants Hybrid Noida/Pune, remote-only gets slight penalty)
    work_mode = signals.get("preferred_work_mode", "").lower()
    m_work_mode = 0.85 if work_mode == "remote" else 1.0
    
    # 5. Salary Expectations Modifier (Soft friction if expectations are extremely high)
    salary_range = signals.get("expected_salary_range_inr_lpa", {})
    m_salary = 1.0
    if isinstance(salary_range, dict):
        salary_max = salary_range.get("max", 0)
        if salary_max > 80:
            m_salary = 0.90
        elif salary_max > 60:
            m_salary = 0.95
            
    return m_notice, m_location, m_availability, m_work_mode, m_salary

def calculate_trust_modifier(signals):
    profile_completeness = signals.get("profile_completeness_score", 0)
    signup_date_str = signals.get("signup_date", "")
    connection_count = signals.get("connection_count", 0)
    endorsements = signals.get("endorsements_received", 0)
    verified_email = signals.get("verified_email", False)
    verified_phone = signals.get("verified_phone", False)
    linkedin_connected = signals.get("linkedin_connected", False)
    
    s_completeness = (profile_completeness / 100.0) * 2.0
    
    s_tenure = 0.0
    signup_dt = parse_date(signup_date_str)
    if signup_dt:
        days_tenure = (REF_DATE - signup_dt).days
        s_tenure = min(2.0, (days_tenure / 365.0) * 1.0)
        
    s_connections = min(2.0, (connection_count / 100.0) * 0.4)
    s_endorsements = min(2.0, (endorsements / 20.0) * 1.0)
    
    s_email = 1.0 if verified_email else 0.0
    s_phone = 1.0 if verified_phone else 0.0
    s_linkedin = 1.0 if linkedin_connected else 0.0
    
    s_trust_total = s_completeness + s_tenure + s_connections + s_endorsements + s_email + s_phone + s_linkedin
    m_trust = 1.0 + (s_trust_total / 11.0) * 0.05
    return m_trust

def calculate_assessment_score(signals):
    scores = signals.get("skill_assessment_scores", {})
    if not isinstance(scores, dict) or not scores:
        return None
        
    relevant_scores = []
    for k, v in scores.items():
        k_lower = k.lower()
        if any(term in k_lower for term in ["python", "machine learning", "ml", "nlp", "natural language", "deep learning", "vector", "retrieval", "ranking", "sql"]):
            relevant_scores.append(v)
            
    if relevant_scores:
        return sum(relevant_scores) / len(relevant_scores)
    return None

def extract_all_features(candidate):
    profile = candidate.get("profile", {})
    skills = candidate.get("skills", [])
    signals = candidate.get("redrob_signals", {})
    
    # Check safety flags
    is_hp, hp_reasons = check_honeypot(candidate)
    is_it_service = check_it_service_only(candidate)
    
    # Calculate components
    title_score = calculate_title_score(profile.get("current_title", ""))
    
    # Mix github activity score into experience calculation
    profile_with_github = profile.copy()
    profile_with_github["github_activity_score"] = float(signals.get("github_activity_score", 0))
    if signals.get("github_activity_score") == -1:
        profile_with_github["github_activity_score"] = 0.0
        
    exp_score = calculate_experience_score(profile_with_github, len(skills), is_it_service)
    
    # 360-degree skills score (blends resume and Redrob assessment scores)
    skills_score = calculate_skills_score(skills)
    assessment_score = calculate_assessment_score(signals)
    if assessment_score is not None:
        skills_score = 0.6 * skills_score + 0.4 * assessment_score
        
    behavioral_score = calculate_behavioral_score(signals)
    m_notice, m_location, m_availability, m_work_mode, m_salary = calculate_logistics_modifiers(signals, profile)
    m_trust = calculate_trust_modifier(signals)
    
    return {
        "candidate_id": candidate.get("candidate_id"),
        "is_honeypot": is_hp,
        "honeypot_reasons": hp_reasons,
        "is_it_service_only": is_it_service,
        "title_score": title_score,
        "experience_score": exp_score,
        "skills_score": skills_score,
        "behavioral_score": behavioral_score,
        "notice_modifier": m_notice,
        "location_modifier": m_location,
        "availability_modifier": m_availability,
        "work_mode_modifier": m_work_mode,
        "salary_modifier": m_salary,
        "trust_modifier": m_trust,
        "raw_profile": {
            "years_of_experience": profile.get("years_of_experience", 0),
            "current_title": profile.get("current_title", ""),
            "location": profile.get("location", ""),
            "notice_period_days": signals.get("notice_period_days", 0),
            "top_skills": [s.get("name") for s in skills[:3]]
        }
    }
