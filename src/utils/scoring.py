"""Lead scoring utilities for calculating Pain Score."""

from typing import List
from datetime import datetime, timedelta
from src.config import settings
from src.utils.models import Lead, LeadUrgency


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
    weights = settings.scoring_weights

    # Base score from keyword matches (up to 45 points)
    keyword_count = len(lead.keywords_matched)
    score += min(keyword_count * weights["keyword_match"], 45)

    # Urgency keywords (up to 25 points)
    content_lower = lead.content.lower()
    urgency_matches = []
    for keyword in settings.urgency_keywords:
        if keyword.lower() in content_lower:
            urgency_matches.append(keyword)
    lead.urgency_keywords_matched = urgency_matches
    score += min(len(urgency_matches) * weights["urgency_keyword"], 25)

    # Multiple pain points bonus (10 points)
    if keyword_count >= 3:
        score += weights["multiple_pain_points"]

    # Recency bonus (15 points if posted in last 24 hours)
    if lead.found_at:
        age = datetime.utcnow() - lead.found_at
        if age < timedelta(hours=24):
            score += weights["recent_post"]
        elif age < timedelta(days=7):
            score += weights["recent_post"] * 0.5

    # Solution-seeking language (5 points)
    solution_phrases = [
        "looking for", "need help", "any recommendations",
        "what do you use", "how do you handle", "suggestions",
        "advice", "trying to find", "searching for"
    ]
    for phrase in solution_phrases:
        if phrase in content_lower:
            score += 5
            break

    # Cap at 100
    final_score = min(int(score), 100)
    lead.pain_score = final_score

    # Set urgency level based on score
    if final_score >= 75:
        lead.urgency = LeadUrgency.CRITICAL
    elif final_score >= 50:
        lead.urgency = LeadUrgency.HIGH
    elif final_score >= 25:
        lead.urgency = LeadUrgency.MEDIUM
    else:
        lead.urgency = LeadUrgency.LOW

    return final_score


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
    """Enrich a lead with pain score, urgency, and industry detection."""
    calculate_pain_score(lead)
    detect_industry(lead)
    return lead


def enrich_leads(leads: List[Lead]) -> List[Lead]:
    """Enrich multiple leads and sort by pain score."""
    enriched = [enrich_lead(lead) for lead in leads]
    return sorted(enriched, key=lambda x: x.pain_score, reverse=True)
