"""Data models for the lead generation app."""

from datetime import datetime
from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class LeadSource(str, Enum):
    """Sources where leads can be found."""
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    GOOGLE_SEARCH = "google_search"
    PRODUCT_HUNT = "product_hunt"
    INDEED = "indeed"


class Lead(BaseModel):
    """Represents a potential lead."""

    # Identification
    id: str = Field(description="Unique identifier for the lead")
    source: LeadSource = Field(description="Where the lead was found")

    # Contact info (may be partial)
    username: Optional[str] = Field(default=None, description="Username on the platform")
    email: Optional[str] = Field(default=None, description="Email if available")
    name: Optional[str] = Field(default=None, description="Real name if available")
    company: Optional[str] = Field(default=None, description="Company name if mentioned")

    # Content
    title: str = Field(description="Title of post or search result")
    content: str = Field(description="Full text content")
    url: str = Field(description="URL to the original content")

    # Metadata
    keywords_matched: List[str] = Field(default_factory=list, description="Pain keywords found")
    subreddit: Optional[str] = Field(default=None, description="Subreddit if from Reddit")

    # AI Analysis
    ai_score: Optional[float] = Field(default=None, description="AI relevance score 0-1")
    ai_reasoning: Optional[str] = Field(default=None, description="AI explanation")
    is_qualified: bool = Field(default=False, description="Whether AI qualified this lead")

    # Tracking
    found_at: datetime = Field(default_factory=datetime.utcnow)
    sent_to_crm: bool = Field(default=False)
    hubspot_id: Optional[str] = Field(default=None)

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        if isinstance(other, Lead):
            return self.id == other.id
        return False


class LeadBatch(BaseModel):
    """A collection of leads from a scraping run."""

    source: LeadSource
    leads: List[Lead] = Field(default_factory=list)
    total_found: int = 0
    qualified_count: int = 0
    errors: List[str] = Field(default_factory=list)
    scraped_at: datetime = Field(default_factory=datetime.utcnow)
