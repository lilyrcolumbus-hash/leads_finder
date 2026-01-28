"""
Lead Manager - Deduplication, Persistence, Export, Email Finding
"""

import json
import csv
import hashlib
import requests
from pathlib import Path
from typing import List, Optional, Dict, Set
from datetime import datetime
import io

from src.utils.models import Lead
from src.config import settings


class LeadManager:
    """Manages leads with deduplication, persistence, and enrichment."""

    def __init__(self, storage_path: str = "data/leads.json"):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._seen_hashes: Set[str] = set()
        self._load_seen_hashes()

    def _generate_hash(self, lead: Lead) -> str:
        """Generate unique hash for a lead based on URL, title, and author."""
        unique_string = f"{lead.url}|{lead.title.lower().strip()}|{lead.author.lower().strip()}"
        return hashlib.md5(unique_string.encode()).hexdigest()

    def _load_seen_hashes(self):
        """Load previously seen lead hashes from storage."""
        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    for lead_data in data.get('leads', []):
                        hash_str = lead_data.get('hash', '')
                        if hash_str:
                            self._seen_hashes.add(hash_str)
            except Exception:
                pass

    def deduplicate(self, leads: List[Lead]) -> List[Lead]:
        """Remove duplicate leads based on URL, title, and author."""
        unique_leads = []
        session_hashes = set()

        for lead in leads:
            lead_hash = self._generate_hash(lead)

            # Skip if already seen in storage or this session
            if lead_hash in self._seen_hashes or lead_hash in session_hashes:
                continue

            session_hashes.add(lead_hash)
            unique_leads.append(lead)

        return unique_leads

    def save_leads(self, leads: List[Lead]) -> int:
        """Save leads to JSON storage. Returns number of new leads saved."""
        existing_data = {'leads': [], 'last_updated': None}

        if self.storage_path.exists():
            try:
                with open(self.storage_path, 'r') as f:
                    existing_data = json.load(f)
            except Exception:
                pass

        new_count = 0
        for lead in leads:
            lead_hash = self._generate_hash(lead)

            if lead_hash not in self._seen_hashes:
                lead_dict = lead.model_dump()
                lead_dict['hash'] = lead_hash
                lead_dict['saved_at'] = datetime.now().isoformat()
                # Convert datetime objects to strings
                if lead_dict.get('found_at'):
                    lead_dict['found_at'] = str(lead_dict['found_at'])
                if lead_dict.get('posted_at'):
                    lead_dict['posted_at'] = str(lead_dict['posted_at'])
                # Convert enum to string
                if lead_dict.get('source'):
                    lead_dict['source'] = str(lead_dict['source'].value) if hasattr(lead_dict['source'], 'value') else str(lead_dict['source'])
                if lead_dict.get('urgency'):
                    lead_dict['urgency'] = str(lead_dict['urgency'].value) if hasattr(lead_dict['urgency'], 'value') else str(lead_dict['urgency'])

                existing_data['leads'].append(lead_dict)
                self._seen_hashes.add(lead_hash)
                new_count += 1

        existing_data['last_updated'] = datetime.now().isoformat()
        existing_data['total_count'] = len(existing_data['leads'])

        with open(self.storage_path, 'w') as f:
            json.dump(existing_data, f, indent=2, default=str)

        return new_count

    def load_leads(self) -> List[Dict]:
        """Load all saved leads from storage."""
        if not self.storage_path.exists():
            return []

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)
                return data.get('leads', [])
        except Exception:
            return []

    def import_from_csv(self, csv_content: str) -> Dict:
        """Import leads from CSV content. Returns stats about import."""
        imported = 0
        duplicates = 0
        errors = 0

        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            existing_data = {'leads': [], 'last_updated': None}
            if self.storage_path.exists():
                try:
                    with open(self.storage_path, 'r') as f:
                        existing_data = json.load(f)
                except Exception:
                    pass

            for row in reader:
                try:
                    # Create a hash for deduplication
                    title = row.get('title', row.get('Title', ''))
                    url = row.get('url', row.get('URL', row.get('Url', '')))
                    author = row.get('author', row.get('Author', row.get('name', row.get('Name', ''))))
                    email = row.get('email', row.get('Email', ''))

                    if not title and not url:
                        errors += 1
                        continue

                    unique_string = f"{url}|{title.lower().strip()}|{author.lower().strip()}"
                    lead_hash = hashlib.md5(unique_string.encode()).hexdigest()

                    if lead_hash in self._seen_hashes:
                        duplicates += 1
                        continue

                    # Create lead dict
                    lead_dict = {
                        'title': title,
                        'author': author,
                        'email': email,
                        'url': url,
                        'content': row.get('content', row.get('Content', row.get('description', row.get('Description', '')))),
                        'source': row.get('source', row.get('Source', 'imported')),
                        'industry': row.get('industry', row.get('Industry', '')),
                        'pain_score': int(row.get('pain_score', row.get('Pain', row.get('pain', 0))) or 0),
                        'hash': lead_hash,
                        'saved_at': datetime.now().isoformat(),
                        'imported': True
                    }

                    existing_data['leads'].append(lead_dict)
                    self._seen_hashes.add(lead_hash)
                    imported += 1

                except Exception as e:
                    errors += 1
                    continue

            existing_data['last_updated'] = datetime.now().isoformat()
            existing_data['total_count'] = len(existing_data['leads'])

            with open(self.storage_path, 'w') as f:
                json.dump(existing_data, f, indent=2, default=str)

        except Exception as e:
            return {
                'imported': 0,
                'duplicates': 0,
                'errors': 1,
                'error_message': str(e)
            }

        return {
            'imported': imported,
            'duplicates': duplicates,
            'errors': errors
        }

    def get_stats(self) -> Dict:
        """Get statistics about saved leads."""
        leads = self.load_leads()

        if not leads:
            return {
                'total': 0,
                'by_source': {},
                'by_industry': {},
                'avg_pain_score': 0,
                'hot_leads': 0
            }

        by_source = {}
        by_industry = {}
        total_pain_score = 0
        hot_leads = 0

        for lead in leads:
            # Count by source
            source = lead.get('source', 'unknown')
            by_source[source] = by_source.get(source, 0) + 1

            # Count by industry
            industry = lead.get('industry', 'Unknown')
            if industry:
                by_industry[industry] = by_industry.get(industry, 0) + 1

            # Pain score
            pain_score = lead.get('pain_score', 0)
            total_pain_score += pain_score
            if pain_score >= 70:
                hot_leads += 1

        return {
            'total': len(leads),
            'by_source': by_source,
            'by_industry': by_industry,
            'avg_pain_score': total_pain_score / len(leads) if leads else 0,
            'hot_leads': hot_leads
        }

    def clear_storage(self):
        """Clear all saved leads."""
        self._seen_hashes.clear()
        if self.storage_path.exists():
            self.storage_path.unlink()

    def get_duplicate_count(self, leads: List[Lead]) -> int:
        """Count how many leads are duplicates."""
        duplicates = 0
        session_hashes = set()

        for lead in leads:
            lead_hash = self._generate_hash(lead)
            if lead_hash in self._seen_hashes or lead_hash in session_hashes:
                duplicates += 1
            else:
                session_hashes.add(lead_hash)

        return duplicates


class CSVExporter:
    """Export leads to CSV format."""

    @staticmethod
    def export_leads(leads: List[Lead]) -> str:
        """Export leads to CSV string."""
        output = io.StringIO()

        fieldnames = [
            'title', 'author', 'email', 'url', 'source', 'industry',
            'pain_score', 'urgency', 'keywords_matched', 'content_preview',
            'found_at'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            writer.writerow({
                'title': lead.title[:100] if lead.title else '',
                'author': lead.author or '',
                'email': lead.email or '',
                'url': lead.url or '',
                'source': lead.source.value if hasattr(lead.source, 'value') else str(lead.source),
                'industry': lead.industry or '',
                'pain_score': lead.pain_score,
                'urgency': lead.urgency.value if hasattr(lead.urgency, 'value') else str(lead.urgency),
                'keywords_matched': ', '.join(lead.keywords_matched[:5]) if lead.keywords_matched else '',
                'content_preview': lead.content[:200] if lead.content else '',
                'found_at': str(lead.found_at) if lead.found_at else ''
            })

        return output.getvalue()

    @staticmethod
    def export_leads_from_dict(leads: List[Dict]) -> str:
        """Export leads from dictionary format to CSV string."""
        output = io.StringIO()

        fieldnames = [
            'title', 'author', 'email', 'url', 'source', 'industry',
            'pain_score', 'urgency', 'keywords_matched', 'content_preview',
            'saved_at'
        ]

        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()

        for lead in leads:
            keywords = lead.get('keywords_matched', [])
            if isinstance(keywords, list):
                keywords_str = ', '.join(keywords[:5])
            else:
                keywords_str = str(keywords)

            writer.writerow({
                'title': str(lead.get('title', ''))[:100],
                'author': lead.get('author', ''),
                'email': lead.get('email', ''),
                'url': lead.get('url', ''),
                'source': lead.get('source', ''),
                'industry': lead.get('industry', ''),
                'pain_score': lead.get('pain_score', 0),
                'urgency': lead.get('urgency', ''),
                'keywords_matched': keywords_str,
                'content_preview': str(lead.get('content', ''))[:200],
                'saved_at': lead.get('saved_at', '')
            })

        return output.getvalue()


class EmailFinder:
    """Find email addresses for leads using Hunter.io API."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, 'hunter_api_key', None)
        self.base_url = "https://api.hunter.io/v2"

    def is_configured(self) -> bool:
        """Check if Hunter.io API is configured."""
        return bool(self.api_key)

    def find_email(self, domain: str, first_name: str = None, last_name: str = None) -> Optional[Dict]:
        """Find email for a person at a domain."""
        if not self.is_configured():
            return None

        try:
            params = {
                'domain': domain,
                'api_key': self.api_key
            }

            if first_name:
                params['first_name'] = first_name
            if last_name:
                params['last_name'] = last_name

            response = requests.get(
                f"{self.base_url}/email-finder",
                params=params,
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                if data.get('data', {}).get('email'):
                    return {
                        'email': data['data']['email'],
                        'confidence': data['data'].get('score', 0),
                        'sources': data['data'].get('sources', [])
                    }
        except Exception:
            pass

        return None

    def verify_email(self, email: str) -> Optional[Dict]:
        """Verify if an email address is valid."""
        if not self.is_configured():
            return None

        try:
            response = requests.get(
                f"{self.base_url}/email-verifier",
                params={
                    'email': email,
                    'api_key': self.api_key
                },
                timeout=10
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    'status': data.get('data', {}).get('status'),
                    'score': data.get('data', {}).get('score', 0),
                    'disposable': data.get('data', {}).get('disposable', False)
                }
        except Exception:
            pass

        return None

    def domain_search(self, domain: str, limit: int = 10) -> List[Dict]:
        """Search for all emails at a domain."""
        if not self.is_configured():
            return []

        try:
            response = requests.get(
                f"{self.base_url}/domain-search",
                params={
                    'domain': domain,
                    'api_key': self.api_key,
                    'limit': limit
                },
                timeout=15
            )

            if response.status_code == 200:
                data = response.json()
                emails = data.get('data', {}).get('emails', [])
                return [
                    {
                        'email': e.get('value'),
                        'first_name': e.get('first_name'),
                        'last_name': e.get('last_name'),
                        'position': e.get('position'),
                        'confidence': e.get('confidence', 0)
                    }
                    for e in emails
                ]
        except Exception:
            pass

        return []


# Singleton instances
lead_manager = LeadManager()
csv_exporter = CSVExporter()
email_finder = EmailFinder()
