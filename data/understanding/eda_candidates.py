import json
import os
from datetime import datetime

# Reference date from JD/architecture docs
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
    # Count skills marked "expert" with duration_months == 0
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
        # Check if the company name contains any IT service name
        is_it_service = False
        for svc in IT_SERVICE_COMPANIES:
            if svc in company:
                is_it_service = True
                break
        if not is_it_service:
            # Found at least one job in a non-IT service company
            return False
            
    return True

def analyze_candidates(filepath, is_jsonl=False, limit=None):
    total = 0
    honeypots_count = 0
    it_service_only_count = 0
    countries = {}
    locations = {}
    exp_brackets = {
        "<3 years": 0,
        "3-5 years": 0,
        "5-9 years (JD range)": 0,
        "9-12 years": 0,
        ">12 years": 0
    }
    honeypot_reasons_stats = {}
    
    print(f"Reading from: {filepath}...")
    
    if is_jsonl:
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                candidate = json.loads(line)
                total += 1
                
                # Check metrics
                profile = candidate.get("profile", {})
                exp = profile.get("years_of_experience", 0)
                if exp < 3:
                    exp_brackets["<3 years"] += 1
                elif exp < 5:
                    exp_brackets["3-5 years"] += 1
                elif exp <= 9:
                    exp_brackets["5-9 years (JD range)"] += 1
                elif exp <= 12:
                    exp_brackets["9-12 years"] += 1
                else:
                    exp_brackets[">12 years"] += 1
                    
                country = profile.get("country", "Unknown")
                countries[country] = countries.get(country, 0) + 1
                
                loc = profile.get("location", "Unknown")
                locations[loc] = locations.get(loc, 0) + 1
                
                is_hp, reasons = check_honeypot(candidate)
                if is_hp:
                    honeypots_count += 1
                    for r in reasons:
                        honeypot_reasons_stats[r] = honeypot_reasons_stats.get(r, 0) + 1
                        
                if check_it_service_only(candidate):
                    it_service_only_count += 1
                    
                if limit and total >= limit:
                    break
    else:
        with open(filepath, "r", encoding="utf-8") as f:
            candidates = json.load(f)
            for candidate in candidates:
                total += 1
                profile = candidate.get("profile", {})
                exp = profile.get("years_of_experience", 0)
                if exp < 3:
                    exp_brackets["<3 years"] += 1
                elif exp < 5:
                    exp_brackets["3-5 years"] += 1
                elif exp <= 9:
                    exp_brackets["5-9 years (JD range)"] += 1
                elif exp <= 12:
                    exp_brackets["9-12 years"] += 1
                else:
                    exp_brackets[">12 years"] += 1
                    
                country = profile.get("country", "Unknown")
                countries[country] = countries.get(country, 0) + 1
                
                loc = profile.get("location", "Unknown")
                locations[loc] = locations.get(loc, 0) + 1
                
                is_hp, reasons = check_honeypot(candidate)
                if is_hp:
                    honeypots_count += 1
                    for r in reasons:
                        honeypot_reasons_stats[r] = honeypot_reasons_stats.get(r, 0) + 1
                        
                if check_it_service_only(candidate):
                    it_service_only_count += 1
                    
                if limit and total >= limit:
                    break
                    
    print("\n--- EDA RESULTS ---")
    print(f"Total Profiles Processed: {total}")
    print(f"Honeypots Detected: {honeypots_count} ({honeypots_count/total*100:.2f}%)")
    print(f"Honeypot Breakdown:")
    for r, c in honeypot_reasons_stats.items():
        print(f"  - {r}: {c}")
    print(f"IT-Service Only Profiles (Excluded): {it_service_only_count} ({it_service_only_count/total*100:.2f}%)")
    print(f"Years of Experience Distribution:")
    for bracket, c in exp_brackets.items():
        print(f"  - {bracket}: {c} ({c/total*100:.2f}%)")
    print(f"Top 5 Countries:")
    sorted_countries = sorted(countries.items(), key=lambda x: x[1], reverse=True)[:5]
    for c, count in sorted_countries:
        print(f"  - {c}: {count} ({count/total*100:.2f}%)")
        
    print("-------------------\n")
    return {
        "total": total,
        "honeypots": honeypots_count,
        "it_service_only": it_service_only_count,
        "exp_brackets": exp_brackets,
        "countries": sorted_countries
    }

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--file", type=str, default=None)
    parser.add_argument("--jsonl", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    
    if args.file:
        analyze_candidates(args.file, args.jsonl, args.limit)
    else:
        # Default to sample file first
        sample_path = r"d:\redrob\[PUB] India_runs_data_and_ai_challenge\India_runs_data_and_ai_challenge\sample_candidates.json"
        if os.path.exists(sample_path):
            analyze_candidates(sample_path, is_jsonl=False)
        else:
            print("Please specify --file")
