"""Data models for the lead generation app.

Updated: Added extra fields for business data (website, location, rating, etc.)
"""

from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class LeadSource(str, Enum):
    """Sources where leads can be found."""
    REDDIT = "reddit"
    HACKER_NEWS = "hacker_news"
    GOOGLE_SEARCH = "google_search"
    PRODUCT_HUNT = "product_hunt"
    GOOGLE_MAPS = "google_maps"
    INDEED = "indeed"
    YELP = "yelp"
    LINKEDIN = "linkedin"
    FACEBOOK = "facebook"
    YELLOW_PAGES = "yellow_pages"
    BBB = "bbb"
    CRAIGSLIST = "craigslist"


class LeadUrgency(str, Enum):
    """Urgency level of a lead."""
    CRITICAL = "critical"
    HIGH = "high"
    HOT = "hot"
    MEDIUM = "medium"
    WARM = "warm"
    LOW = "low"
    COLD = "cold"


class LeadCategory(str, Enum):
    """Category of lead based on pain detection."""
    PAIN = "pain"           # Explicit pain/problem detected
    OPPORTUNITY = "opportunity"  # No explicit pain but potential customer
    COLD = "cold"           # Low potential


class Lead(BaseModel):
    """Represents a potential lead."""

    # Identification
    id: str = Field(description="Unique identifier for the lead")
    source: LeadSource = Field(description="Where the lead was found")

    # Contact info (may be partial)
    username: Optional[str] = Field(default=None, description="Username on the platform")
    email: Optional[str] = Field(default=None, description="Email if available")
    phone: Optional[str] = Field(default=None, description="Phone number if available")
    name: Optional[str] = Field(default=None, description="Real name if available")
    company: Optional[str] = Field(default=None, description="Company name if mentioned")

    # Professional & Social info
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    twitter: Optional[str] = Field(default=None, description="Twitter/X handle")
    position: Optional[str] = Field(default=None, description="Job title/position")
    author: Optional[str] = Field(default=None, description="Author name if from post")

    # Company info
    employees: Optional[str] = Field(default=None, description="Number of employees (e.g., '10-50')")
    revenue: Optional[str] = Field(default=None, description="Company revenue range")
    country: Optional[str] = Field(default=None, description="Country")

    # Content
    title: str = Field(description="Title of post or search result")
    content: str = Field(description="Full text content")
    url: str = Field(description="URL to the original content")

    # Metadata
    keywords_matched: List[str] = Field(default_factory=list, description="Pain keywords found")
    subreddit: Optional[str] = Field(default=None, description="Subreddit if from Reddit")
    industry: Optional[str] = Field(default=None, description="Detected industry")

    # Scoring
    pain_score: Optional[float] = Field(default=None, description="Pain score 0-100")
    intent_score: Optional[float] = Field(default=None, description="Intent score 0-100")
    fit_score: Optional[float] = Field(default=None, description="Fit score 0-100")
    total_score: Optional[float] = Field(default=None, description="Total combined score 0-100")
    urgency: Optional[LeadUrgency] = Field(default=None, description="Lead urgency level")
    urgency_keywords_matched: List[str] = Field(default_factory=list, description="Urgency keywords found")
    score_breakdown: Optional[dict] = Field(default=None, description="Detailed score breakdown")

    # Google Maps specific fields
    address: Optional[str] = Field(default=None, description="Business address")
    review_count: Optional[int] = Field(default=None, description="Total number of reviews")
    business_type: Optional[str] = Field(default=None, description="Type of business")
    place_id: Optional[str] = Field(default=None, description="Google Place ID")

    # Pain detection fields (for Google Maps reviews)
    has_pain: bool = Field(default=False, description="Whether pain points were detected in reviews")
    pain_reviews: List[str] = Field(default_factory=list, description="Reviews containing pain keywords")
    pain_summary: Optional[str] = Field(default=None, description="Summary of pain points found")

    # AI Analysis
    ai_score: Optional[float] = Field(default=None, description="AI relevance score 0-1")
    ai_reasoning: Optional[str] = Field(default=None, description="AI explanation")
    is_qualified: bool = Field(default=False, description="Whether AI qualified this lead")
    lead_category: Optional[LeadCategory] = Field(default=None, description="Category: pain, opportunity, or cold")
    has_explicit_pain: bool = Field(default=False, description="Whether lead has explicit pain/problem")

    # Gemini Business Analysis - Software needs detection
    software_needs: Optional[str] = Field(default=None, description="Software needs detected by Gemini (e.g., 'Needs chatbot, no social media')")
    has_website: Optional[bool] = Field(default=None, description="Whether business has a website")
    has_social_media: Optional[bool] = Field(default=None, description="Whether business has social media presence")
    gemini_analysis: Optional[str] = Field(default=None, description="Full Gemini analysis of business needs")

    # Tracking
    found_at: datetime = Field(default_factory=datetime.utcnow)
    sent_to_crm: bool = Field(default=False)
    hubspot_id: Optional[str] = Field(default=None)

    # Extra data (for enrichment services like Apollo, Google Maps, etc.)
    extra_data: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional data from enrichment services")
    posted_at: Optional[datetime] = Field(default=None, description="When the original content was posted")
    location: Optional[str] = Field(default=None, description="Geographic location")
    website: Optional[str] = Field(default=None, description="Business website")
    rating: Optional[float] = Field(default=None, description="Business rating 1-5")

    # CRM fields
    status: Optional[str] = Field(default="new", description="Lead status in CRM pipeline")
    notes: Optional[str] = Field(default=None, description="Notes about the lead")
    tags: List[str] = Field(default_factory=list, description="Tags for categorization")

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
