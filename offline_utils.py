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
    if not title:
        return 50.0
    title_lower = title.lower()
    
    # 1. Trap Titles (0 points / Disqualified)
    trap_keywords = {"marketing", "sales", "recruiter", "hr", "operations", "consultant", "business analyst", "accountant"}
    for kw in trap_keywords:
        if kw in title_lower:
            return 0.0
            
    # 2. Target ML/AI Engineering Title (100 points)
    ml_keywords = {"machine learning", "ml", "ai", "search", "ranking", "retrieval", "nlp", "computer vision"}
    for kw in ml_keywords:
        if kw in title_lower:
            return 100.0
            
    # 3. Technical Pipeline Title (70 points)
    tech_keywords = {"software", "backend", "data", "fullstack", "systems", "developer", "engineer"}
    for kw in tech_keywords:
        if kw in title_lower:
            return 70.0
            
    return 50.0

def calculate_experience_score(profile, skills_count):
    years = profile.get("years_of_experience", 0)
    github_activity_score = profile.get("github_activity_score", 0)  # parsed from profile/signals later
    current_title = profile.get("current_title", "").lower()
    
    if 6.0 <= years <= 8.0:
        return 100.0
    elif years < 6.0:
        return max(0.0, 100.0 - (6.0 - years) * 40.0)
    else:  # years > 8.0
        # Hands-on Check: if active builder, exempt from decay
        is_management = any(kw in current_title for kw in ["vp", "director", "manager", "architect", "lead"])
        if github_activity_score >= 30 or skills_count >= 15 or not is_management:
            return 100.0
        else:
            return max(0.0, 100.0 - (years - 8.0) * 15.0)

def calculate_skills_score(skills):
    if not skills:
        return 0.0
        
    core_retrieval = {"pinecone", "milvus", "faiss", "qdrant", "weaviate", "bge", "e5", "vector search", "dense retrieval"}
    core_ranking = {"learning-to-rank", "ndcg", "map", "mrr", "ranking", "hybrid search", "elasticsearch"}
    core_ml = {"nlp", "machine learning", "deep learning", "pytorch", "huggingface", "fine-tuning"}
    
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
    
    # 2. Responsiveness Score
    resp_rate = signals.get("recruiter_response_rate", 0.0)
    resp_time = signals.get("avg_response_time_hours", 0.0)
    s_responsiveness = max(0.0, (resp_rate * 100.0) - min(30.0, resp_time * 0.5))
    
    # 3. Activity Recency Score
    last_active_str = signals.get("last_active_date", "")
    last_active_dt = parse_date(last_active_str)
    if last_active_dt:
        days_inactive = (REF_DATE - last_active_dt).days
        s_activity = 100.0 if days_inactive <= 180 else 0.0
    else:
        s_activity = 0.0
        
    # 4. Platform Reliability Score
    completion_rate = signals.get("interview_completion_rate", 0.0) * 100.0
    acceptance = signals.get("offer_acceptance_rate", 0.0)
    acceptance_rate = (acceptance * 100.0) if acceptance != -1 else 0.0
    s_reliability = (completion_rate + acceptance_rate) / 2.0
    
    # 5. Recruiter Demand Score
    views = signals.get("profile_views_received_30d", 0)
    saves = signals.get("saved_by_recruiters_30d", 0)
    s_views = min(100.0, views * 2.0)
    s_saves = min(100.0, saves * 10.0)
    s_demand = (s_views + s_saves) / 2.0
    
    # Weighted Sum
    total = (0.30 * s_github) + (0.25 * s_responsiveness) + (0.20 * s_activity) + (0.15 * s_reliability) + (0.10 * s_demand)
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
            
    return m_notice, m_location

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
        
    exp_score = calculate_experience_score(profile_with_github, len(skills))
    skills_score = calculate_skills_score(skills)
    behavioral_score = calculate_behavioral_score(signals)
    m_notice, m_location = calculate_logistics_modifiers(signals, profile)
    
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
        "raw_profile": {
            "years_of_experience": profile.get("years_of_experience", 0),
            "current_title": profile.get("current_title", ""),
            "location": profile.get("location", ""),
            "notice_period_days": signals.get("notice_period_days", 0),
            "top_skills": [s.get("name") for s in skills[:3]]
        }
    }
