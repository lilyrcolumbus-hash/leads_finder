"""Product Hunt scraper for finding founders with communication pain points."""

import time
from typing import List
from xml.etree import ElementTree as ET

from bs4 import BeautifulSoup

from src.config import settings
from src.utils.models import Lead, LeadBatch, LeadSource
from .base_scraper import BaseScraper


class ProductHuntScraper(BaseScraper):
    """Scraper for Product Hunt using RSS feeds and public pages."""

    source = LeadSource.PRODUCT_HUNT
    RSS_URL = "https://www.producthunt.com/feed"
    TOPICS_URL = "https://www.producthunt.com/topics/{topic}"

    def __init__(self):
        super().__init__()
        # Topics relevant to our target audience
        self.topics = [
            "customer-communication",
            "scheduling",
            "customer-service",
            "small-business",
            "productivity",
            "phone",
            "appointments"
        ]
        # Product-specific keywords
        self.ph_keywords = [
            "receptionist",
            "answering",
            "call handling",
            "phone service",
            "appointment",
            "scheduling",
            "customer calls",
            "voicemail",
            "business phone",
            "call management"
        ]

    def scrape(self) -> LeadBatch:
        """
        Scrape Product Hunt for relevant founders and discussions.

        Returns:
            LeadBatch with found leads
        """
        batch = LeadBatch(source=self.source)
        all_leads: List[Lead] = []

        self.logger.info("Starting Product Hunt scrape")

        # Get from main RSS feed
        try:
            rss_leads = self._scrape_rss_feed()
            all_leads.extend(rss_leads)
            self.logger.info(f"Found {len(rss_leads)} leads from RSS feed")
        except Exception as e:
            error_msg = f"Error scraping PH RSS: {str(e)}"
            self.logger.error(error_msg)
            batch.errors.append(error_msg)

        # Scrape relevant topic pages
        for topic in self.topics:
            try:
                topic_leads = self._scrape_topic(topic)
                all_leads.extend(topic_leads)
                self.logger.debug(f"Found {len(topic_leads)} leads in topic: {topic}")
                time.sleep(1)
            except Exception as e:
                self.logger.warning(f"Error scraping topic {topic}: {e}")

        # Search discussions/comments for pain points
        try:
            discussion_leads = self._scrape_discussions()
            all_leads.extend(discussion_leads)
        except Exception as e:
            batch.errors.append(f"Error scraping discussions: {str(e)}")

        # Deduplicate
        unique_leads = list({lead.id: lead for lead in all_leads}.values())

        batch.leads = unique_leads[:settings.max_leads_per_source]
        batch.total_found = len(unique_leads)

        self.logger.info(f"Product Hunt scrape complete: {batch.total_found} leads found")
        return batch

    def _scrape_rss_feed(self) -> List[Lead]:
        """Scrape the main Product Hunt RSS feed."""
        leads = []

        try:
            response = self.fetch_url(self.RSS_URL)
            entries = self._parse_rss(response.text)

            for entry in entries:
                lead = self._entry_to_lead(entry)
                if lead:
                    leads.append(lead)

        except Exception as e:
            self.logger.debug(f"RSS feed scrape failed: {e}")
            raise

        return leads

    def _parse_rss(self, xml_content: str) -> List[dict]:
        """Parse RSS XML feed into list of entries."""
        entries = []
        try:
            root = ET.fromstring(xml_content)

            # RSS 2.0 format
            for item in root.findall('.//item'):
                entry_data = {
                    'title': item.findtext('title', ''),
                    'link': item.findtext('link', ''),
                    'summary': item.findtext('description', ''),
                    'author': item.findtext('author', '') or item.findtext('{http://purl.org/dc/elements/1.1/}creator', ''),
                }
                entries.append(entry_data)

            # Also try Atom format
            ns = {'atom': 'http://www.w3.org/2005/Atom'}
            for entry in root.findall('atom:entry', ns):
                title_el = entry.find('atom:title', ns)
                link_el = entry.find('atom:link', ns)
                summary_el = entry.find('atom:summary', ns) or entry.find('atom:content', ns)
                author_el = entry.find('atom:author/atom:name', ns)

                entry_data = {
                    'title': title_el.text if title_el is not None else '',
                    'link': link_el.get('href', '') if link_el is not None else '',
                    'summary': summary_el.text if summary_el is not None else '',
                    'author': author_el.text if author_el is not None else '',
                }
                entries.append(entry_data)

        except ET.ParseError as e:
            self.logger.debug(f"XML parse error: {e}")

        return entries

    def _scrape_topic(self, topic: str) -> List[Lead]:
        """
        Scrape a specific Product Hunt topic page.

        Args:
            topic: Topic slug to scrape

        Returns:
            List of leads found
        """
        leads = []
        url = self.TOPICS_URL.format(topic=topic)

        try:
            response = self.fetch_url(url)
            soup = BeautifulSoup(response.text, "lxml")

            # Find product cards or links
            product_links = soup.find_all("a", href=lambda x: x and "/posts/" in x)

            for link in product_links[:20]:  # Limit per topic
                try:
                    lead = self._parse_product_link(link, topic)
                    if lead:
                        leads.append(lead)
                except Exception:
                    continue

        except Exception as e:
            self.logger.debug(f"Topic scrape failed for {topic}: {e}")

        return leads

    def _scrape_discussions(self) -> List[Lead]:
        """Look for discussions where founders mention pain points."""
        leads = []

        # Product Hunt has discussion pages, try to find relevant ones
        discussion_urls = [
            "https://www.producthunt.com/discussions?category=founder-stories",
            "https://www.producthunt.com/discussions?category=advice"
        ]

        for url in discussion_urls:
            try:
                response = self.fetch_url(url)
                soup = BeautifulSoup(response.text, "lxml")

                # Find discussion cards
                discussions = soup.find_all(["article", "div"], class_=lambda x: x and "discussion" in str(x).lower())

                for disc in discussions[:15]:
                    text = disc.get_text(" ", strip=True)
                    keywords = self.find_keywords(text)

                    if keywords:
                        # Find link
                        link = disc.find("a", href=True)
                        href = link["href"] if link else url

                        if not href.startswith("http"):
                            href = f"https://www.producthunt.com{href}"

                        lead = Lead(
                            id=self.generate_id("ph_disc", href),
                            source=self.source,
                            title=text[:100],
                            content=text[:2000],
                            url=href,
                            keywords_matched=keywords
                        )
                        leads.append(lead)

                time.sleep(0.5)

            except Exception as e:
                self.logger.debug(f"Discussion scrape failed: {e}")

        return leads

    def _entry_to_lead(self, entry: dict) -> Lead | None:
        """Convert RSS entry to Lead if relevant."""
        try:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            link = entry.get("link", "")

            full_text = f"{title} {summary}"

            # Check for relevance
            keywords = self.find_keywords(full_text)

            # Also check PH-specific keywords
            text_lower = full_text.lower()
            for kw in self.ph_keywords:
                if kw.lower() in text_lower and kw not in keywords:
                    keywords.append(kw)

            if not keywords:
                return None

            # Try to extract maker info
            author = entry.get("author", "")

            lead = Lead(
                id=self.generate_id("ph", link or title),
                source=self.source,
                username=author,
                title=title,
                content=summary[:2000],
                url=link,
                keywords_matched=keywords,
                email=self.extract_email(full_text),
                phone=self.extract_phone(full_text),
                company=self.extract_company(full_text)
            )

            return lead

        except Exception as e:
            self.logger.debug(f"Error parsing PH entry: {e}")
            return None

    def _parse_product_link(self, link_elem, topic: str) -> Lead | None:
        """Parse a product link element into a Lead."""
        try:
            href = link_elem.get("href", "")
            if not href:
                return None

            if not href.startswith("http"):
                href = f"https://www.producthunt.com{href}"

            text = link_elem.get_text(" ", strip=True)

            # Only include if text seems relevant
            keywords = self.find_keywords(text)
            text_lower = text.lower()
            for kw in self.ph_keywords:
                if kw.lower() in text_lower and kw not in keywords:
                    keywords.append(kw)

            if not keywords:
                return None

            lead = Lead(
                id=self.generate_id("ph", href),
                source=self.source,
                title=text[:200],
                content=f"Found in topic: {topic}. {text}",
                url=href,
                keywords_matched=keywords
            )

            return lead

        except Exception:
            return None
