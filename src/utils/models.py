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
    LINKEDIN = "linkedin"
    TWITTER = "twitter"
    YELP = "yelp"
    GOOGLE_MY_BUSINESS = "google_my_business"
    FACEBOOK = "facebook"
    G2_CLUTCH = "g2_clutch"


class LeadUrgency(str, Enum):
    """Urgency level of a lead."""
    CRITICAL = "critical"    # Public complaints, actively losing business
    HIGH = "high"            # Multiple pain points, seeking solution
    MEDIUM = "medium"        # Some pain points mentioned
    LOW = "low"              # General interest


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
    phone: Optional[str] = Field(default=None, description="Phone number if available")
    website: Optional[str] = Field(default=None, description="Business website if found")

    # Professional info
    position: Optional[str] = Field(default=None, description="Job title/position")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    twitter: Optional[str] = Field(default=None, description="Twitter/X profile URL")

    # Location
    location: Optional[str] = Field(default=None, description="City, State, Country")
    country: Optional[str] = Field(default=None, description="Country")
    timezone: Optional[str] = Field(default=None, description="Timezone")

    # Content
    title: str = Field(description="Title of post or search result")
    content: str = Field(description="Full text content")
    url: str = Field(description="URL to the original content")
    notes: Optional[str] = Field(default=None, description="Additional notes")

    # Classification
    industry: Optional[str] = Field(default=None, description="Detected industry category")
    business_size: Optional[str] = Field(default=None, description="Estimated business size")
    revenue: Optional[str] = Field(default=None, description="Estimated revenue range")
    employees: Optional[str] = Field(default=None, description="Number of employees")

    # Metadata
    keywords_matched: List[str] = Field(default_factory=list, description="Pain keywords found")
    urgency_keywords_matched: List[str] = Field(default_factory=list, description="Urgency keywords found")
    subreddit: Optional[str] = Field(default=None, description="Subreddit if from Reddit")
    tags: List[str] = Field(default_factory=list, description="Custom tags")

    # Scoring
    pain_score: int = Field(default=0, description="Pain score 0-100")
    urgency: LeadUrgency = Field(default=LeadUrgency.LOW, description="Urgency level")

    # AI Analysis
    ai_score: Optional[float] = Field(default=None, description="AI relevance score 0-1")
    ai_reasoning: Optional[str] = Field(default=None, description="AI explanation")
    is_qualified: bool = Field(default=False, description="Whether AI qualified this lead")

    # Tracking
    found_at: datetime = Field(default_factory=datetime.utcnow)
    sent_to_crm: bool = Field(default=False)
    hubspot_id: Optional[str] = Field(default=None)
    status: Optional[str] = Field(default="new", description="Lead status: new, contacted, qualified, converted, lost")
    last_contact: Optional[datetime] = Field(default=None, description="Last contact date")

    # Custom fields
    author: Optional[str] = Field(default=None, description="Author alias for compatibility")
    posted_at: Optional[datetime] = Field(default=None, description="When content was posted")

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
