"""Configuration settings for the lead generation app."""

from typing import List, Dict
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    hubspot_api_key: str = Field(default="", alias="HUBSPOT_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_search_engine_id: str = Field(default="", alias="GOOGLE_SEARCH_ENGINE_ID")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Reddit subreddits to search (organized by industry)
    subreddits: List[str] = [
        # General Business
        "smallbusiness",
        "sweatystartup",
        "entrepreneur",
        "startups",
        "sidehustle",
        # HVAC / Air Conditioning
        "HVAC",
        "hvacadvice",
        "refrigeration",
        # Plumbing
        "Plumbing",
        "Plumbers",
        # Electrical
        "electricians",
        "electrical",
        # Roofing
        "Roofing",
        "roofers",
        # Landscaping / Lawn Care
        "landscaping",
        "lawncare",
        "arborists",
        "irrigation",
        # General Contractors / Construction
        "Construction",
        "contractors",
        "homebuilding",
        # Cleaning Services
        "cleaningservice",
        "pressurewashing",
        "windowcleaning",
        # Pest Control
        "pestcontrol",
        # Painting
        "painters",
        "paint",
        # Flooring
        "Flooring",
        "Hardwood",
        "Tile",
        # Garage Doors / Gates
        "garagedoorservice",
        # Locksmith
        "Locksmith",
        # Appliance Repair
        "appliancerepair",
        # Pool Services
        "pools",
        "swimmingpools",
        # Moving Services
        "moving",
        "movingcompanies",
        # Medical/Health
        "dentistry",
        "medicalpractice",
        "veterinary",
        "pharmacy",
        "chiropractors",
        "physicaltherapy",
        "optometry",
        "audiology",
        "mentalhealth",
        "therapists",
        # Legal
        "lawyers",
        "lawfirm",
        "paralegal",
        # Beauty/Wellness
        "salonprofessionals",
        "estheticians",
        "nails",
        "hairstylist",
        "barbershop",
        "massage",
        "tattoo",
        # Food/Restaurant
        "restaurantowners",
        "kitchenconfidential",
        "foodtrucks",
        "catering",
        "bakery",
        # Automotive
        "automotivemechanics",
        "autodetailing",
        "autobody",
        "tires",
        "Diesel",
        # Professional Services
        "insurance",
        "realestate",
        "realtors",
        "accounting",
        "bookkeeping",
        "financialplanning",
        # Fitness / Gyms
        "gymowners",
        "personaltraining",
        "yoga",
        "crossfit",
        # Pet Services
        "doggrooming",
        "petcare",
        "petsitting",
        "dogtraining",
        # Photography / Events
        "WeddingPhotography",
        "photography",
        "weddingplanning",
        "eventplanning"
    ]

    # Industry categories for filtering
    industries: Dict[str, List[str]] = {
        # Home Services - Specific Categories
        "HVAC / Air Conditioning": ["HVAC", "hvacadvice", "refrigeration"],
        "Plumbing": ["Plumbing", "Plumbers"],
        "Electrical": ["electricians", "electrical"],
        "Roofing": ["Roofing", "roofers"],
        "Landscaping / Lawn": ["landscaping", "lawncare", "arborists", "irrigation"],
        "General Contractors": ["Construction", "contractors", "homebuilding"],
        "Cleaning Services": ["cleaningservice", "pressurewashing", "windowcleaning"],
        "Pest Control": ["pestcontrol"],
        "Painting": ["painters", "paint"],
        "Flooring": ["Flooring", "Hardwood", "Tile"],
        "Pool Services": ["pools", "swimmingpools"],
        "Moving Services": ["moving", "movingcompanies"],
        "Locksmith": ["Locksmith"],
        "Appliance Repair": ["appliancerepair"],
        # Professional Services
        "Medical/Dental": ["dentistry", "medicalpractice", "veterinary", "pharmacy", "chiropractors", "physicaltherapy", "optometry", "audiology"],
        "Mental Health": ["mentalhealth", "therapists"],
        "Legal": ["lawyers", "lawfirm", "paralegal"],
        "Beauty/Spa": ["salonprofessionals", "estheticians", "nails", "hairstylist", "barbershop", "massage", "tattoo"],
        "Automotive": ["automotivemechanics", "autodetailing", "autobody", "tires", "Diesel"],
        "Restaurants": ["restaurantowners", "kitchenconfidential", "foodtrucks", "catering", "bakery"],
        "Real Estate": ["realestate", "realtors"],
        "Financial": ["insurance", "accounting", "bookkeeping", "financialplanning"],
        "Fitness / Gyms": ["gymowners", "personaltraining", "yoga", "crossfit"],
        "Pet Services": ["doggrooming", "petcare", "petsitting", "dogtraining"],
        "Photography / Events": ["WeddingPhotography", "photography", "weddingplanning", "eventplanning"],
        "General Business": ["smallbusiness", "sweatystartup", "entrepreneur", "startups", "sidehustle"]
    }

    # Pain point keywords (expanded for better detection)
    pain_keywords: List[str] = [
        # Original keywords
        "missed calls",
        "losing customers",
        "need receptionist",
        "can't answer phone",
        "cant answer phone",
        "overwhelmed",
        "scheduling nightmare",
        "no one answers",
        "bad reviews",
        "customer complaints",
        "phone keeps ringing",
        "voicemail full",
        "answering service",
        "receptionist needed",
        "need answering service",
        "never answers phone",
        "front desk",
        "call handling",
        "missed appointment",
        "booking system",
        # Appointment/Scheduling Problems
        "appointment no-shows",
        "double booked",
        "overbooking",
        "scheduling chaos",
        "calendar nightmare",
        "booking confusion",
        "no-show patients",
        "missed appointments",
        # Phone/Communication Issues
        "customer calling frustrated",
        "hold times too long",
        "put on hold",
        "after hours calls",
        "weekend phone coverage",
        "24/7 coverage",
        "phone going to voicemail",
        "customers cant reach",
        "too many calls",
        # Solution Seeking
        "virtual receptionist",
        "phone answering AI",
        "automated receptionist",
        "AI receptionist",
        "call answering service",
        "phone automation",
        # Business Impact
        "losing leads",
        "missed opportunities",
        "leads going cold",
        "potential clients",
        "lost revenue",
        "missing business",
        # Capacity Issues
        "too busy to answer",
        "juggling phone and work",
        "can't do both",
        "one person office",
        "solo practitioner",
        "one man show",
        "small team overwhelmed",
        # Staffing Problems
        "hiring receptionist expensive",
        "receptionist quit",
        "front desk turnover",
        "can't afford receptionist",
        "receptionist costs",
        "staff shortage",
        # Customer Feedback
        "customers complaining",
        "bad google reviews",
        "yelp reviews phone",
        "negative reviews",
        "complaints about phone",
        "never call back"
    ]

    # Urgency keywords (for scoring)
    urgency_keywords: List[str] = [
        "urgent",
        "desperate",
        "need help now",
        "losing money",
        "emergency",
        "asap",
        "immediately",
        "can't wait",
        "critical",
        "serious problem",
        "last straw",
        "fed up",
        "at breaking point"
    ]

    # Google search queries (expanded)
    google_search_queries: List[str] = [
        '"receptionist needed" small business',
        '"need answering service"',
        '"never answers phone" review',
        '"missed my call" business',
        '"can\'t get through" business phone',
        '"no one answers the phone" local business',
        '"scheduling nightmare" business owner',
        '"virtual receptionist" looking for',
        '"missed calls" small business',
        '"phone goes to voicemail" business',
        '"need someone to answer phones"',
        '"after hours phone coverage"',
        '"appointment scheduling software" frustrated',
        '"losing customers" phone calls'
    ]

    # Data source configuration
    data_sources: Dict[str, Dict] = {
        "reddit": {"enabled": True, "icon": "🔴", "name": "Reddit"},
        "hackernews": {"enabled": True, "icon": "🟠", "name": "Hacker News"},
        "google": {"enabled": True, "icon": "🔵", "name": "Google Search"},
        "producthunt": {"enabled": True, "icon": "🟤", "name": "Product Hunt"},
        "linkedin": {"enabled": False, "icon": "🔷", "name": "LinkedIn", "coming_soon": True},
        "twitter": {"enabled": False, "icon": "🐦", "name": "Twitter/X", "coming_soon": True},
        "yelp": {"enabled": False, "icon": "⭐", "name": "Yelp Reviews", "coming_soon": True},
        "gmb": {"enabled": False, "icon": "📍", "name": "Google My Business", "coming_soon": True},
        "facebook": {"enabled": False, "icon": "📘", "name": "Facebook Groups", "coming_soon": True},
        "g2": {"enabled": False, "icon": "🏆", "name": "G2/Clutch", "coming_soon": True}
    }

    # Lead scoring weights
    scoring_weights: Dict[str, float] = {
        "keyword_match": 15.0,        # Points per keyword matched
        "urgency_keyword": 25.0,      # Points per urgency keyword
        "multiple_pain_points": 10.0, # Bonus for 3+ pain points
        "recent_post": 15.0,          # Posted in last 24 hours
        "public_complaint": 20.0,     # Public review/complaint
        "solution_seeking": 20.0,     # Actively looking for solution
        "business_size_small": 10.0,  # Small business indicator
    }

    # Business size categories
    business_sizes: List[str] = [
        "1-5 employees",
        "6-20 employees",
        "21-50 employees",
        "50+ employees"
    ]

    # Batch sizes
    max_leads_per_source: int = 50
    ai_filter_batch_size: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
