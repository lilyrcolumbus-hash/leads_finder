"""Configuration settings for the lead generation app."""

import os
from pathlib import Path
from typing import List
from dotenv import load_dotenv
from pydantic_settings import BaseSettings
from pydantic import Field

# Load .env from project root
_project_root = Path(__file__).parent.parent
_env_file = _project_root / ".env"
if _env_file.exists():
    load_dotenv(_env_file, override=True)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    hubspot_api_key: str = Field(default="", alias="HUBSPOT_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_search_engine_id: str = Field(default="", alias="GOOGLE_SEARCH_ENGINE_ID")
    google_places_api_key: str = Field(default="", alias="GOOGLE_PLACES_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    hunter_api_key: str = Field(default="", alias="HUNTER_API_KEY")
    apollo_api_key: str = Field(default="", alias="APOLLO_API_KEY")
    facebook_access_token: str = Field(default="", alias="FACEBOOK_ACCESS_TOKEN")

    # Google Sheets sync (Apps Script Web App URL)
    google_sheets_webhook_url: str = Field(default="", alias="GOOGLE_SHEETS_WEBHOOK_URL")
    google_sheets_batch_size: int = Field(default=10, alias="GOOGLE_SHEETS_BATCH_SIZE")

    # Reddit subreddits to search - Active business communities
    subreddits: List[str] = [
        "smallbusiness",
        "Entrepreneur",
        "sweatystartup",
        "startups",
        "business",
        "HVAC",
        "Plumbing",
        "electricians",
        "Roofing",
        "landscaping",
        "dentistry",
        "realtors",
        "contractors",
        "HomeImprovement",
        "lawncare"
    ]

    # Pain point keywords - General terms people actually use
    pain_keywords: List[str] = [
        # Phone/Communication problems
        "phone",
        "calls",
        "customers",
        "clients",
        "busy",
        "overwhelmed",
        "stressed",
        "help needed",
        "struggling",
        "frustrated",
        # Business problems
        "losing money",
        "losing customers",
        "bad reviews",
        "complaints",
        "too many",
        "can't keep up",
        "need help",
        "hiring",
        "staff",
        "receptionist",
        "assistant",
        # Scheduling
        "appointments",
        "scheduling",
        "bookings",
        "no shows",
        "cancellations",
        # General pain
        "problem",
        "issue",
        "nightmare",
        "disaster",
        "advice needed",
        "what do you do"
    ]

    # Google search queries
    google_search_queries: List[str] = [
        '"receptionist needed" small business',
        '"need answering service"',
        '"never answers phone" review',
        '"missed my call" business',
        '"can\'t get through" business phone',
        '"no one answers the phone" local business',
        '"scheduling nightmare" business owner'
    ]

    # Google Maps settings
    google_maps_business_types: List[str] = [
        "plumber",
        "electrician",
        "hvac",
        "dentist",
        "lawyer",
        "accountant",
        "real_estate_agent",
        "contractor",
        "auto_repair",
        "veterinarian",
        "medical_clinic",
        "salon",
        "restaurant"
    ]

    google_maps_locations: List[str] = [
        "Miami, FL",
        "Houston, TX",
        "Phoenix, AZ",
        "Los Angeles, CA",
        "Chicago, IL"
    ]

    # Review pain keywords (specific for Google Maps reviews)
    review_pain_keywords: List[str] = [
        "never answers",
        "no one picks up",
        "can't get through",
        "went to voicemail",
        "left message never called back",
        "hard to reach",
        "impossible to contact",
        "no response",
        "waited forever",
        "rude receptionist",
        "couldn't schedule",
        "missed appointment",
        "no confirmation",
        "terrible communication",
        "never returned my call",
        "phone just rings",
        "always busy",
        "no call back",
        "poor customer service",
        "ignored my calls"
    ]

    # Google Maps scraper settings
    google_maps_max_results_per_search: int = 20
    google_maps_max_reviews_per_business: int = 10
    google_maps_min_reviews: int = 5  # Minimum reviews to consider

    # Industries with keywords
    industries: dict = {
        "HVAC": ["hvac", "heating", "cooling", "air conditioning", "furnace"],
        "Plumbing": ["plumbing", "plumber", "pipes", "drain", "water heater"],
        "Electrical": ["electrician", "electrical", "wiring", "outlet"],
        "Roofing": ["roofing", "roof", "shingles", "gutters"],
        "Landscaping": ["landscaping", "lawn", "garden", "yard"],
        "Dental": ["dental", "dentist", "orthodontist", "teeth"],
        "Real Estate": ["realtor", "real estate", "property", "homes"],
        "Legal": ["lawyer", "attorney", "legal", "law firm"],
        "Medical": ["medical", "doctor", "clinic", "healthcare"],
        "Auto Repair": ["mechanic", "auto repair", "car service", "automotive"]
    }

    # Urgency keywords for scoring
    urgency_keywords: List[str] = [
        "urgent", "asap", "immediately", "emergency", "critical",
        "desperate", "help needed", "right away", "as soon as possible",
        "can't wait", "time sensitive", "deadline", "losing money",
        "losing customers", "frustrated", "fed up", "at my wits end"
    ]

    # Scoring weights for lead qualification
    scoring_weights: dict = {
        "keyword_match": 9,           # Points per pain keyword matched (max 45)
        "urgency_keyword": 8,         # Points per urgency keyword (max 25)
        "multiple_pain_points": 10,   # Bonus for 3+ pain keywords
        "recent_post": 15,            # Bonus for posts < 24 hours old
        "solution_seeking": 5,        # Bonus for solution-seeking language
        "industry_match": 5,          # Bonus for matching target industry
    }

    # Batch sizes
    max_leads_per_source: int = 50
    ai_filter_batch_size: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
