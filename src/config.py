"""Configuration settings for the lead generation app."""

from typing import List
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    hubspot_api_key: str = Field(default="", alias="HUBSPOT_API_KEY")
    google_api_key: str = Field(default="", alias="GOOGLE_API_KEY")
    google_search_engine_id: str = Field(default="", alias="GOOGLE_SEARCH_ENGINE_ID")
    google_places_api_key: str = Field(default="", alias="GOOGLE_PLACES_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")

    # Reddit subreddits to search
    subreddits: List[str] = [
        "smallbusiness",
        "sweatystartup",
        "HVAC",
        "Plumbing",
        "electricians",
        "Roofing",
        "landscaping",
        "dentistry",
        "realtors"
    ]

    # Pain point keywords
    pain_keywords: List[str] = [
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
        "booking system"
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

    # Batch sizes
    max_leads_per_source: int = 50
    ai_filter_batch_size: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
