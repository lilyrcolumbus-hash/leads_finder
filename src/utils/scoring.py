"""
Lead scoring utilities - Triple Score System
Pain Score + Intent Score + Fit Score = Total Lead Score
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
from src.config import settings
from src.utils.models import Lead, LeadUrgency


# =============================================================================
# INTENT SIGNALS - Indicates they're actively looking for a solution
# =============================================================================

INTENT_SIGNALS = {
    # Hiring signals (strong intent - they're spending money to solve this)
    "hiring_receptionist": {
        "keywords": ["hiring receptionist", "looking for receptionist", "need receptionist",
                     "receptionist position", "front desk job", "seeking receptionist",
                     "receptionist wanted", "hiring front desk", "need front desk"],
        "score": 25
    },

    # Active solution seeking
    "solution_seeking": {
        "keywords": ["looking for solution", "need a solution", "searching for",
                     "any recommendations", "what do you use", "how do you handle",
                     "best way to", "anyone know", "suggestions for", "advice on",
                     "trying to find", "help me find", "recommend a"],
        "score": 20
    },

    # Comparison shopping (very high intent)
    "comparing_options": {
        "keywords": ["comparing", "vs", "versus", "alternative to", "better than",
                     "switch from", "replace", "looking at options", "evaluating",
                     "which is better", "pros and cons"],
        "score": 25
    },

    # Budget/pricing discussions (ready to buy)
    "budget_ready": {
        "keywords": ["budget for", "willing to pay", "cost of", "pricing",
                     "how much does", "affordable", "roi", "investment",
                     "worth the money", "pay for"],
        "score": 20
    },

    # Timeline urgency
    "urgent_timeline": {
        "keywords": ["asap", "urgent", "immediately", "right now", "this week",
                     "as soon as possible", "need it now", "can't wait", "emergency",
                     "deadline", "quickly"],
        "score": 15
    },

    # Negative reviews about phones (pain + intent combined)
    "phone_complaints": {
        "keywords": ["never answers", "can't get through", "no one picks up",
                     "always voicemail", "didn't return call", "hard to reach",
                     "poor communication", "missed my call", "couldn't reach",
                     "no response", "waiting for callback"],
        "score": 30
    },

    # Technology upgrade signals
    "tech_upgrade": {
        "keywords": ["upgrade", "modernize", "automate", "streamline",
                     "more efficient", "save time", "reduce workload",
                     "too manual", "outdated system", "old software"],
        "score": 15
    }
}


# =============================================================================
# FIT CRITERIA - How well they match your ideal customer profile
# =============================================================================

# Target industries for AI Receptionist (your ICP)
TARGET_INDUSTRIES = {
    "tier_1": {  # Perfect fit - 30 points
        "industries": ["HVAC / Air Conditioning", "Plumbing", "Electrical",
                      "Medical/Dental", "Legal", "Automotive"],
        "score": 30
    },
    "tier_2": {  # Great fit - 25 points
        "industries": ["Roofing", "General Contractors", "Beauty/Spa",
                      "Real Estate", "Pest Control", "Cleaning Services"],
        "score": 25
    },
    "tier_3": {  # Good fit - 20 points
        "industries": ["Landscaping / Lawn", "Pool Services", "Locksmith",
                      "Financial", "Fitness / Gyms", "Pet Services",
                      "Restaurants", "Photography / Events"],
        "score": 20
    },
    "tier_4": {  # Acceptable - 10 points
        "industries": ["Moving Services", "Appliance Repair", "Painting",
                      "Flooring", "Mental Health", "General Business"],
        "score": 10
    }
}

# Company size fit (employees)
COMPANY_SIZE_FIT = {
    "1-10": 25,      # Sweet spot - small team overwhelmed
    "11-50": 30,     # Perfect - can afford, needs solution
    "51-200": 20,    # Good - has budget
    "201-500": 10,   # Okay - might have internal solution
    "500+": 5        # Enterprise - different sales cycle
}

# Business indicators
BUSINESS_INDICATORS = {
    "has_website": 10,
    "has_phone": 10,
    "has_email": 10,
    "has_linkedin": 5,
    "has_reviews": 10,      # Active business
    "local_business": 15,   # Local SMB = perfect fit
}

# Email quality indicators (from email verification)
EMAIL_QUALITY_SCORES = {
    "verified_valid": 15,       # Verified deliverable email
    "catch_all": 5,             # Catch-all domain (uncertain)
    "role_based": 0,            # info@, support@ - reduce priority
    "free_email": -5,           # gmail, yahoo - less professional
    "disposable": -15,          # Temp email - bad signal
    "invalid": -20,             # Invalid email - remove from scoring
}


# =============================================================================
# SCORING FUNCTIONS
# =============================================================================

def calculate_pain_score(lead: Lead) -> int:
    """
    Calculate a Pain Score (0-100) for a lead based on multiple factors.

    Scoring factors:
    - Number of pain keywords matched
    - Presence of urgency keywords
    - Multiple pain points bonus
    - Recency of post
    - Solution-seeking language
    """
    score = 0
    breakdown = {"factors": []}
    weights = settings.scoring_weights

    # Base score from keyword matches (up to 45 points)
    keyword_count = len(lead.keywords_matched)
    keyword_score = min(keyword_count * weights["keyword_match"], 45)
    score += keyword_score
    if keyword_score > 0:
        breakdown["factors"].append(f"Pain keywords ({keyword_count}): +{keyword_score}")

    # Urgency keywords (up to 25 points)
    content_lower = lead.content.lower()
    urgency_matches = []
    for keyword in settings.urgency_keywords:
        if keyword.lower() in content_lower:
            urgency_matches.append(keyword)
    lead.urgency_keywords_matched = urgency_matches
    urgency_score = min(len(urgency_matches) * weights["urgency_keyword"], 25)
    score += urgency_score
    if urgency_score > 0:
        breakdown["factors"].append(f"Urgency keywords ({len(urgency_matches)}): +{urgency_score}")

    # Multiple pain points bonus (10 points)
    if keyword_count >= 3:
        score += weights["multiple_pain_points"]
        breakdown["factors"].append(f"Multiple pain points: +{weights['multiple_pain_points']}")

    # Recency bonus (15 points if posted in last 24 hours)
    if lead.found_at:
        age = datetime.utcnow() - lead.found_at
        if age < timedelta(hours=24):
            score += weights["recent_post"]
            breakdown["factors"].append(f"Recent post (<24h): +{weights['recent_post']}")
        elif age < timedelta(days=7):
            bonus = int(weights["recent_post"] * 0.5)
            score += bonus
            breakdown["factors"].append(f"Recent post (<7d): +{bonus}")

    # Solution-seeking language (5 points)
    solution_phrases = [
        "looking for", "need help", "any recommendations",
        "what do you use", "how do you handle", "suggestions",
        "advice", "trying to find", "searching for"
    ]
    for phrase in solution_phrases:
        if phrase in content_lower:
            score += 5
            breakdown["factors"].append("Solution-seeking language: +5")
            break

    # Cap at 100
    final_score = min(int(score), 100)
    lead.pain_score = final_score

    return final_score


def calculate_intent_score(lead: Lead) -> int:
    """
    Calculate Intent Score (0-100) based on buying signals.

    Higher score = more likely to buy soon
    """
    score = 0
    breakdown = {"signals": []}

    # Combine all text for analysis
    text_to_analyze = f"{lead.title} {lead.content}".lower()
    if lead.extra_data:
        # Include review text if available (from Yelp, Google Maps)
        reviews = lead.extra_data.get("reviews", "")
        if reviews:
            text_to_analyze += f" {reviews}".lower()

    # Check each intent signal category
    for signal_name, signal_data in INTENT_SIGNALS.items():
        for keyword in signal_data["keywords"]:
            if keyword in text_to_analyze:
                score += signal_data["score"]
                breakdown["signals"].append({
                    "signal": signal_name,
                    "keyword": keyword,
                    "score": signal_data["score"]
                })
                break  # Only count each signal category once

    # Bonus: From Indeed (hiring = high intent)
    if lead.source.value == "indeed":
        score += 20
        breakdown["signals"].append({
            "signal": "indeed_source",
            "keyword": "Hiring for receptionist role",
            "score": 20
        })

    # Bonus: Yelp with phone complaints
    if lead.source.value == "yelp" and lead.keywords_matched:
        phone_keywords = ["never answers", "can't reach", "no response", "voicemail"]
        if any(kw in " ".join(lead.keywords_matched).lower() for kw in phone_keywords):
            score += 15
            breakdown["signals"].append({
                "signal": "yelp_phone_complaint",
                "keyword": "Phone complaint in reviews",
                "score": 15
            })

    # Cap at 100
    final_score = min(int(score), 100)
    lead.intent_score = final_score

    return final_score


def calculate_fit_score(lead: Lead) -> int:
    """
    Calculate Fit Score (0-100) based on ideal customer profile match.

    Higher score = better match for AI Receptionist product
    """
    score = 0
    breakdown = {"criteria": []}

    # Industry fit (up to 30 points)
    industry = lead.industry or "General Business"
    industry_score = 0
    for tier_name, tier_data in TARGET_INDUSTRIES.items():
        if industry in tier_data["industries"]:
            industry_score = tier_data["score"]
            breakdown["criteria"].append({
                "factor": f"Industry: {industry} ({tier_name})",
                "score": industry_score
            })
            break
    score += industry_score

    # If no industry match, give base score
    if industry_score == 0:
        score += 5
        breakdown["criteria"].append({
            "factor": f"Industry: {industry} (unknown tier)",
            "score": 5
        })

    # Business data completeness (indicates established business)
    if lead.website:
        score += BUSINESS_INDICATORS["has_website"]
        breakdown["criteria"].append({"factor": "Has website", "score": 10})

    if lead.phone:
        score += BUSINESS_INDICATORS["has_phone"]
        breakdown["criteria"].append({"factor": "Has phone", "score": 10})

    if lead.email:
        score += BUSINESS_INDICATORS["has_email"]
        breakdown["criteria"].append({"factor": "Has email", "score": 10})

        # Email quality scoring (if verified)
        if lead.extra_data and lead.extra_data.get("email_verified"):
            email_data = lead.extra_data.get("email_verification", {})
            email_status = email_data.get("status", "")
            email_flags = email_data.get("flags", [])

            # Apply email quality adjustments
            if email_status == "valid" and "undeliverable" not in email_flags:
                email_bonus = EMAIL_QUALITY_SCORES["verified_valid"]
                score += email_bonus
                breakdown["criteria"].append({"factor": "Verified valid email", "score": email_bonus})
            elif "catch_all" in email_flags:
                email_bonus = EMAIL_QUALITY_SCORES["catch_all"]
                score += email_bonus
                breakdown["criteria"].append({"factor": "Catch-all domain", "score": email_bonus})

            # Penalties for low-quality emails
            if "free_email" in email_flags:
                penalty = EMAIL_QUALITY_SCORES["free_email"]
                score += penalty
                breakdown["criteria"].append({"factor": "Free email provider", "score": penalty})
            if "role_based" in email_flags:
                breakdown["criteria"].append({"factor": "Role-based email (info@, etc.)", "score": 0})
            if "disposable" in email_flags:
                penalty = EMAIL_QUALITY_SCORES["disposable"]
                score += penalty
                breakdown["criteria"].append({"factor": "Disposable email", "score": penalty})
            if email_status == "invalid":
                penalty = EMAIL_QUALITY_SCORES["invalid"]
                score += penalty
                breakdown["criteria"].append({"factor": "Invalid email", "score": penalty})

    if lead.linkedin:
        score += BUSINESS_INDICATORS["has_linkedin"]
        breakdown["criteria"].append({"factor": "Has LinkedIn", "score": 5})

    # Local business indicator (from Google Maps or has location)
    if lead.source.value == "google_my_business" or lead.location:
        score += BUSINESS_INDICATORS["local_business"]
        breakdown["criteria"].append({"factor": "Local business", "score": 15})

    # Company size fit (if available)
    if lead.employees:
        try:
            emp_str = lead.employees.lower().replace(",", "").replace("+", "")
            if "1-10" in emp_str or int(emp_str) <= 10:
                score += COMPANY_SIZE_FIT["1-10"]
                breakdown["criteria"].append({"factor": "Company size: 1-10", "score": 25})
            elif "11-50" in emp_str or (11 <= int(emp_str) <= 50):
                score += COMPANY_SIZE_FIT["11-50"]
                breakdown["criteria"].append({"factor": "Company size: 11-50", "score": 30})
            elif "51-200" in emp_str or (51 <= int(emp_str) <= 200):
                score += COMPANY_SIZE_FIT["51-200"]
                breakdown["criteria"].append({"factor": "Company size: 51-200", "score": 20})
        except (ValueError, TypeError):
            pass  # Can't parse employee count

    # Reviews indicator (active, established business)
    if lead.extra_data and lead.extra_data.get("rating"):
        score += BUSINESS_INDICATORS["has_reviews"]
        breakdown["criteria"].append({"factor": "Has reviews/rating", "score": 10})

    # Cap at 100
    final_score = min(int(score), 100)
    lead.fit_score = final_score

    return final_score


def calculate_total_score(lead: Lead) -> int:
    """
    Calculate Total Lead Score as average of Pain + Intent + Fit.

    Total Score = (Pain + Intent + Fit) / 3

    Interpretation:
    - 80-100: 🔥 HOT - Contact immediately
    - 60-79:  🌡️ WARM - Add to warming queue
    - 40-59:  ❄️ COOL - Nurture
    - 0-39:   🧊 COLD - Low priority
    """
    pain = lead.pain_score or 0
    intent = lead.intent_score or 0
    fit = lead.fit_score or 0

    total = int((pain + intent + fit) / 3)
    lead.total_score = total

    # Update urgency based on total score
    if total >= 80:
        lead.urgency = LeadUrgency.CRITICAL
    elif total >= 60:
        lead.urgency = LeadUrgency.HIGH
    elif total >= 40:
        lead.urgency = LeadUrgency.MEDIUM
    else:
        lead.urgency = LeadUrgency.LOW

    return total


def detect_industry(lead: Lead) -> str:
    """Detect the industry of a lead based on subreddit or content."""
    # First check subreddit
    if lead.subreddit:
        subreddit_lower = lead.subreddit.lower()
        for industry, subreddits in settings.industries.items():
            if subreddit_lower in [s.lower() for s in subreddits]:
                lead.industry = industry
                return industry

    # Content-based detection
    content_lower = lead.content.lower() + " " + lead.title.lower()

    industry_keywords = {
        # Home Services - Specific
        "HVAC / Air Conditioning": ["hvac", "air conditioning", "ac unit", "furnace", "heating", "cooling", "refrigeration", "ductwork"],
        "Plumbing": ["plumber", "plumbing", "pipe", "drain", "water heater", "leak", "sewer", "faucet"],
        "Electrical": ["electrician", "electrical", "wiring", "outlet", "circuit", "panel", "lighting"],
        "Roofing": ["roofing", "roofer", "roof", "shingles", "gutter", "leak repair"],
        "Landscaping / Lawn": ["landscaping", "lawn care", "mowing", "irrigation", "tree service", "garden"],
        "General Contractors": ["contractor", "construction", "remodel", "renovation", "building", "home improvement"],
        "Cleaning Services": ["cleaning service", "pressure washing", "window cleaning", "janitorial", "maid service"],
        "Pest Control": ["pest control", "exterminator", "termite", "rodent", "insect"],
        "Painting": ["painter", "painting", "interior paint", "exterior paint"],
        "Flooring": ["flooring", "hardwood", "tile", "carpet", "laminate"],
        "Pool Services": ["pool service", "pool cleaning", "swimming pool", "pool maintenance"],
        "Moving Services": ["moving company", "movers", "relocation", "packing"],
        "Locksmith": ["locksmith", "lock", "key", "security"],
        "Appliance Repair": ["appliance repair", "refrigerator repair", "washer", "dryer", "dishwasher"],
        # Professional Services
        "Medical/Dental": ["patient", "clinic", "doctor", "dentist", "medical", "healthcare", "appointment", "practice", "veterinary", "vet", "pharmacy", "chiropractor", "physical therapy", "optometrist"],
        "Mental Health": ["therapist", "counselor", "psychologist", "mental health", "therapy session"],
        "Legal": ["lawyer", "attorney", "law firm", "legal", "client consultation", "case", "paralegal"],
        "Beauty/Spa": ["salon", "spa", "hair", "nails", "beauty", "stylist", "esthetician", "barbershop", "massage", "tattoo"],
        "Automotive": ["mechanic", "auto shop", "car repair", "dealership", "automotive", "auto body", "tire", "oil change"],
        "Restaurants": ["restaurant", "cafe", "reservation", "dining", "kitchen", "food service", "catering", "food truck", "bakery"],
        "Real Estate": ["realtor", "real estate", "property", "showing", "listing", "buyer", "seller", "open house"],
        "Financial": ["insurance", "accounting", "bookkeeping", "tax", "financial planning", "cpa"],
        "Fitness / Gyms": ["gym", "fitness", "personal trainer", "yoga", "crossfit", "workout"],
        "Pet Services": ["dog grooming", "pet sitting", "dog training", "pet care", "boarding"],
        "Photography / Events": ["photographer", "wedding", "event planning", "videographer"]
    }

    best_match = "General Business"
    best_count = 0

    for industry, keywords in industry_keywords.items():
        count = sum(1 for kw in keywords if kw in content_lower)
        if count > best_count:
            best_count = count
            best_match = industry

    lead.industry = best_match
    return best_match


def enrich_lead(lead: Lead) -> Lead:
    """
    Enrich a lead with all three scores and industry detection.

    Calculates:
    - Pain Score (0-100)
    - Intent Score (0-100)
    - Fit Score (0-100)
    - Total Score (average)
    - Industry detection
    """
    # First detect industry (needed for fit score)
    detect_industry(lead)

    # Calculate all three scores
    pain = calculate_pain_score(lead)
    intent = calculate_intent_score(lead)
    fit = calculate_fit_score(lead)
    total = calculate_total_score(lead)

    # Store breakdown for UI display
    lead.score_breakdown = {
        "pain_score": pain,
        "intent_score": intent,
        "fit_score": fit,
        "total_score": total,
        "industry": lead.industry,
        "urgency": lead.urgency.value
    }

    return lead


def enrich_leads(leads: List[Lead]) -> List[Lead]:
    """Enrich multiple leads and sort by total score."""
    enriched = [enrich_lead(lead) for lead in leads]
    return sorted(enriched, key=lambda x: x.total_score, reverse=True)


def get_lead_grade(total_score: int) -> Dict[str, Any]:
    """
    Get the grade/classification for a lead based on total score.

    Returns dict with emoji, label, color, and action.
    """
    if total_score >= 80:
        return {
            "emoji": "🔥",
            "label": "HOT",
            "color": "#EF4444",
            "bg_color": "#FEE2E2",
            "action": "Contact immediately"
        }
    elif total_score >= 60:
        return {
            "emoji": "🌡️",
            "label": "WARM",
            "color": "#F59E0B",
            "bg_color": "#FEF3C7",
            "action": "Add to warming queue"
        }
    elif total_score >= 40:
        return {
            "emoji": "❄️",
            "label": "COOL",
            "color": "#3B82F6",
            "bg_color": "#DBEAFE",
            "action": "Nurture over time"
        }
    else:
        return {
            "emoji": "🧊",
            "label": "COLD",
            "color": "#6B7280",
            "bg_color": "#F3F4F6",
            "action": "Low priority"
        }
