"""Scraper modules for different lead sources."""

from .reddit_scraper import RedditScraper
from .hackernews_scraper import HackerNewsScraper
from .google_scraper import GoogleScraper
from .producthunt_scraper import ProductHuntScraper
from .google_maps_scraper import GoogleMapsScraper  # API version with pain detection
from .googlemaps_scraper import GoogleMapsWebScraper  # Web scraping version
from .indeed_scraper import IndeedScraper
from .yelp_scraper import YelpScraper
from .linkedin_scraper import LinkedInScraper
from .facebook_scraper import FacebookScraper
from .yellowpages_scraper import YellowPagesScraper
from .bbb_scraper import BBBScraper
from .craigslist_scraper import CraigslistScraper
from .base_scraper import BaseScraper

__all__ = [
    "BaseScraper",
    "RedditScraper",
    "HackerNewsScraper",
    "GoogleScraper",
    "ProductHuntScraper",
    "GoogleMapsScraper",
    "GoogleMapsWebScraper",
    "IndeedScraper",
    "YelpScraper",
    "LinkedInScraper",
    "FacebookScraper",
    "YellowPagesScraper",
    "BBBScraper",
    "CraigslistScraper"
]
