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
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    hunter_api_key: str = Field(default="", alias="HUNTER_API_KEY")
    apollo_api_key: str = Field(default="", alias="APOLLO_API_KEY")

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

    # Batch sizes
    max_leads_per_source: int = 50
    ai_filter_batch_size: int = 10

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
