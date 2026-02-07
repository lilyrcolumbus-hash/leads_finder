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

    # Ollama (local AI - free)
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="qwen2.5-coder:7b", alias="OLLAMA_MODEL")

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

    # Google Maps search niches
    maps_niches: List[str] = [
        "dentist",
        "plumber",
        "hvac",
        "roofing",
        "electrician",
        "landscaping",
        "real estate agent",
        "auto repair",
        "veterinarian",
        "chiropractor"
    ]

    # Google Maps default locations
    maps_locations: List[str] = [
        "Texas",
        "Florida",
        "California",
        "New York",
        "Illinois"
    ]

    # Domains to skip when extracting emails
    junk_domains: List[str] = [
        "gstatic.com",
        "schema.org",
        "googleapis.com",
        "google.com",
        "facebook.com",
        "twitter.com",
        "instagram.com",
        "youtube.com",
        "linkedin.com",
        "yelp.com",
        "w3.org",
        "example.com",
        "sentry.io",
        "wixpress.com",
        "squarespace.com",
        "wordpress.com"
    ]

    # Batch sizes
    max_leads_per_source: int = 50
    ai_filter_batch_size: int = 10

    # CSV export path
    csv_export_dir: str = "exports"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()
