"""HubSpot CRM integration with full lead management capabilities."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead


class LeadStage(str, Enum):
    """Pipeline stages for leads."""
    NEW = "new"
    CONTACTED = "contacted"
    DEMO = "demo"
    PROPOSAL = "proposal"
    CLOSED_WON = "closed_won"
    CLOSED_LOST = "closed_lost"


@dataclass
class HubSpotContact:
    """Represents a HubSpot contact."""
    id: str
    email: Optional[str]
    firstname: Optional[str]
    lastname: Optional[str]
    company: Optional[str]
    phone: Optional[str]
    lead_stage: LeadStage
    source: Optional[str]
    notes: List[str]
    created_at: datetime
    properties: Dict[str, Any]

    @classmethod
    def from_hubspot(cls, data: dict) -> "HubSpotContact":
        """Create HubSpotContact from API response."""
        props = data.get("properties", {})
        return cls(
            id=data.get("id", ""),
            email=props.get("email"),
            firstname=props.get("firstname"),
            lastname=props.get("lastname"),
            company=props.get("company"),
            phone=props.get("phone"),
            lead_stage=LeadStage(props.get("lead_stage", "new")),
            source=props.get("lead_source"),
            notes=[],
            created_at=datetime.fromisoformat(props.get("createdate", "").replace("Z", "+00:00")) if props.get("createdate") else datetime.now(),
            properties=props
        )


class HubSpotCRM:
    """HubSpot CRM client with full lead management."""

    BASE_URL = "https://api.hubapi.com"

    def __init__(self):
        self.logger = get_logger("HubSpot")
        self.api_key = settings.hubspot_api_key
        self.client = httpx.Client(
            timeout=30.0,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
        )
        self._pipeline_id = None
        self._stage_ids = {}

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.client.close()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def is_configured(self) -> bool:
        """Check if HubSpot is properly configured."""
        return bool(self.api_key)

    def test_connection(self) -> dict:
        """
        Test the HubSpot API connection.

        Returns:
            dict with 'success', 'message', and optionally 'account_info'
        """
        if not self.is_configured():
            return {
                'success': False,
                'message': 'HubSpot API key not configured'
            }

        try:
            # Try to get account info
            url = f"{self.BASE_URL}/account-info/v3/details"
            response = self.client.get(url)

            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'message': 'Connected successfully',
                    'account_info': {
                        'portal_id': data.get('portalId'),
                        'account_type': data.get('accountType'),
                        'time_zone': data.get('timeZone')
                    }
                }
            elif response.status_code == 401:
                return {
                    'success': False,
                    'message': 'Invalid API key or token expired'
                }
            elif response.status_code == 403:
                return {
                    'success': False,
                    'message': 'Access denied - check API key permissions'
                }
            else:
                return {
                    'success': False,
                    'message': f'API returned status {response.status_code}'
                }

        except httpx.ConnectError:
            return {
                'success': False,
                'message': 'Network error - cannot reach HubSpot API'
            }
        except httpx.TimeoutException:
            return {
                'success': False,
                'message': 'Connection timeout - HubSpot API not responding'
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Connection error: {str(e)[:100]}'
            }

    def get_contacts_count(self) -> int:
        """Get total number of contacts in HubSpot."""
        if not self.is_configured():
            return 0

        try:
            url = f"{self.BASE_URL}/crm/v3/objects/contacts?limit=1"
            response = self.client.get(url)
            if response.status_code == 200:
                data = response.json()
                return data.get('total', 0)
        except Exception:
            pass
        return 0

    # ==================== CREATE OPERATIONS ====================

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def create_contact(self, lead: Lead) -> Optional[str]:
        """
        Create a new contact in HubSpot from a Lead.

        Args:
            lead: Lead object to create as contact

        Returns:
            HubSpot contact ID or None on failure
        """
        from src.utils.models import LeadCategory

        if not self.is_configured():
            self.logger.warning("HubSpot not configured")
            return None

        # Determine HubSpot Lead Status based on category
        hs_lead_status = "OPEN"  # Default
        lead_category_label = "Opportunity"

        if lead.lead_category == LeadCategory.PAIN:
            hs_lead_status = "OPEN"  # Hot leads marked as OPEN (priority)
            lead_category_label = "🔴 PAIN - Has explicit problem"
        elif lead.lead_category == LeadCategory.OPPORTUNITY:
            hs_lead_status = "OPEN"
            lead_category_label = "🟡 OPPORTUNITY - Potential customer"
        elif lead.lead_category == LeadCategory.COLD:
            hs_lead_status = "UNQUALIFIED"
            lead_category_label = "⚪ COLD - Low priority"
        elif lead.has_explicit_pain:
            hs_lead_status = "OPEN"
            lead_category_label = "🔴 PAIN - Has explicit problem"
        elif lead.ai_score and lead.ai_score >= 0.6:
            hs_lead_status = "OPEN"
            lead_category_label = "🔴 HIGH SCORE"
        elif lead.ai_score and lead.ai_score >= 0.3:
            hs_lead_status = "OPEN"
            lead_category_label = "🟡 OPPORTUNITY"
        else:
            hs_lead_status = "UNQUALIFIED"
            lead_category_label = "⚪ COLD"

        # Prepare properties
        properties = {
            "lead_source": lead.source.value,
            "lead_stage": LeadStage.NEW.value,
            "hs_lead_status": hs_lead_status,
            "lead_score": str(int((lead.ai_score or 0.5) * 100)),
            "message": lead.content[:1000],
            "website": lead.url,
            "keywords_matched": ", ".join(lead.keywords_matched[:10])
        }

        # Add email if available
        if lead.email:
            properties["email"] = lead.email
        else:
            # Create a placeholder email for tracking
            properties["email"] = f"{lead.id}@leadgen.placeholder"

        # Add name if available
        if lead.name:
            parts = lead.name.split(" ", 1)
            properties["firstname"] = parts[0]
            if len(parts) > 1:
                properties["lastname"] = parts[1]
        elif lead.username:
            properties["firstname"] = lead.username

        # Add company if available
        if lead.company:
            properties["company"] = lead.company

        # Build detailed AI analysis note with category info
        ai_notes = []
        ai_notes.append(f"Category: {lead_category_label}")
        ai_notes.append(f"AI Score: {(lead.ai_score or 0) * 100:.0f}%")
        if lead.pain_score:
            ai_notes.append(f"Pain Score: {lead.pain_score}")
        if lead.ai_reasoning:
            ai_notes.append(f"AI Analysis: {lead.ai_reasoning}")
        if lead.keywords_matched:
            ai_notes.append(f"Keywords: {', '.join(lead.keywords_matched[:5])}")
        if lead.industry:
            ai_notes.append(f"Industry: {lead.industry}")

        properties["ai_analysis"] = " | ".join(ai_notes)

        url = f"{self.BASE_URL}/crm/v3/objects/contacts"

        try:
            response = self.client.post(url, json={"properties": properties})

            if response.status_code == 409:
                # Contact already exists
                self.logger.info(f"Contact already exists for lead {lead.id}")
                return self._get_existing_contact_id(lead.email or properties["email"])

            response.raise_for_status()
            data = response.json()
            contact_id = data.get("id")
            self.logger.info(f"Created HubSpot contact {contact_id} for lead {lead.id}")
            return contact_id

        except Exception as e:
            self.logger.error(f"Failed to create contact: {e}")
            return None

    def contact_exists(self, email: str = None, url: str = None) -> Optional[str]:
        """
        Check if a contact already exists in HubSpot.

        Args:
            email: Email to search for
            url: Website URL to search for

        Returns:
            Contact ID if exists, None otherwise
        """
        if not self.is_configured():
            return None

        # Try email search first
        if email and not email.endswith("@leadgen.placeholder"):
            contact_id = self._get_existing_contact_id(email)
            if contact_id:
                return contact_id

        # Try website URL search
        if url:
            search_url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
            body = {
                "filterGroups": [{
                    "filters": [{
                        "propertyName": "website",
                        "operator": "EQ",
                        "value": url
                    }]
                }],
                "limit": 1
            }
            try:
                response = self.client.post(search_url, json=body)
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]["id"]
            except Exception:
                pass

        return None

    def send_leads_to_crm(self, leads: List[Lead]) -> Dict[str, int]:
        """
        Send multiple leads to HubSpot with deduplication.

        Args:
            leads: List of leads to send

        Returns:
            Dict with counts of created, existing, and failed
        """
        results = {"created": 0, "existing": 0, "failed": 0}

        self.logger.info(f"Sending {len(leads)} leads to HubSpot (with deduplication)")

        for lead in leads:
            try:
                # Check for existing contact first (deduplication)
                existing_id = self.contact_exists(email=lead.email, url=lead.url)

                if existing_id:
                    self.logger.info(f"Lead {lead.id[:8]} already exists in HubSpot (ID: {existing_id})")
                    lead.hubspot_id = existing_id
                    lead.sent_to_crm = True
                    results["existing"] += 1
                    continue

                # Create new contact
                result = self.create_contact(lead)
                if result:
                    lead.hubspot_id = result
                    lead.sent_to_crm = True
                    results["created"] += 1
                else:
                    results["failed"] += 1

            except Exception as e:
                self.logger.error(f"Error sending lead {lead.id}: {e}")
                results["failed"] += 1

        self.logger.info(
            f"HubSpot sync complete: {results['created']} created, "
            f"{results['existing']} existing, {results['failed']} failed"
        )
        return results

    # ==================== READ OPERATIONS ====================

    def get_all_contacts(self, limit: int = 100) -> List[HubSpotContact]:
        """
        Get all contacts from HubSpot.

        Args:
            limit: Maximum number of contacts to retrieve

        Returns:
            List of HubSpotContact objects
        """
        if not self.is_configured():
            return []

        contacts = []
        url = f"{self.BASE_URL}/crm/v3/objects/contacts"
        params = {
            "limit": min(limit, 100),
            "properties": "email,firstname,lastname,company,phone,lead_stage,lead_source,createdate,hs_lead_status"
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            for result in data.get("results", []):
                contacts.append(HubSpotContact.from_hubspot(result))

            self.logger.info(f"Retrieved {len(contacts)} contacts from HubSpot")

        except Exception as e:
            self.logger.error(f"Failed to get contacts: {e}")

        return contacts

    def get_contacts_by_stage(self, stage: LeadStage) -> List[HubSpotContact]:
        """
        Get contacts filtered by pipeline stage.

        Args:
            stage: LeadStage to filter by

        Returns:
            List of contacts in that stage
        """
        if not self.is_configured():
            return []

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
        body = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "lead_stage",
                    "operator": "EQ",
                    "value": stage.value
                }]
            }],
            "properties": ["email", "firstname", "lastname", "company", "phone", "lead_stage", "lead_source", "createdate"],
            "limit": 100
        }

        try:
            response = self.client.post(url, json=body)
            response.raise_for_status()
            data = response.json()

            contacts = [HubSpotContact.from_hubspot(r) for r in data.get("results", [])]
            self.logger.info(f"Found {len(contacts)} contacts in stage '{stage.value}'")
            return contacts

        except Exception as e:
            self.logger.error(f"Failed to get contacts by stage: {e}")
            return []

    def search_contacts(self, query: str) -> List[HubSpotContact]:
        """
        Search contacts by name or email.

        Args:
            query: Search query (name or email)

        Returns:
            List of matching contacts
        """
        if not self.is_configured():
            return []

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
        body = {
            "filterGroups": [
                {
                    "filters": [{
                        "propertyName": "email",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                },
                {
                    "filters": [{
                        "propertyName": "firstname",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                },
                {
                    "filters": [{
                        "propertyName": "lastname",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                },
                {
                    "filters": [{
                        "propertyName": "company",
                        "operator": "CONTAINS_TOKEN",
                        "value": query
                    }]
                }
            ],
            "properties": ["email", "firstname", "lastname", "company", "phone", "lead_stage", "lead_source", "createdate"],
            "limit": 50
        }

        try:
            response = self.client.post(url, json=body)
            response.raise_for_status()
            data = response.json()

            contacts = [HubSpotContact.from_hubspot(r) for r in data.get("results", [])]
            self.logger.info(f"Search '{query}' found {len(contacts)} contacts")
            return contacts

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            return []

    def get_contact(self, contact_id: str) -> Optional[HubSpotContact]:
        """Get a single contact by ID."""
        if not self.is_configured():
            return None

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
        params = {
            "properties": "email,firstname,lastname,company,phone,lead_stage,lead_source,createdate,message,ai_analysis"
        }

        try:
            response = self.client.get(url, params=params)
            response.raise_for_status()
            return HubSpotContact.from_hubspot(response.json())
        except Exception as e:
            self.logger.error(f"Failed to get contact {contact_id}: {e}")
            return None

    # ==================== UPDATE OPERATIONS ====================

    def update_lead_stage(self, contact_id: str, new_stage: LeadStage) -> bool:
        """
        Move a lead to a different pipeline stage.

        Args:
            contact_id: HubSpot contact ID
            new_stage: New LeadStage to set

        Returns:
            True if successful
        """
        if not self.is_configured():
            return False

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"
        body = {
            "properties": {
                "lead_stage": new_stage.value,
                "hs_lead_status": new_stage.value.upper().replace("_", " ")
            }
        }

        try:
            response = self.client.patch(url, json=body)
            response.raise_for_status()
            self.logger.info(f"Updated contact {contact_id} to stage '{new_stage.value}'")
            return True
        except Exception as e:
            self.logger.error(f"Failed to update stage: {e}")
            return False

    def add_note(self, contact_id: str, note: str) -> bool:
        """
        Add a note to a contact.

        Args:
            contact_id: HubSpot contact ID
            note: Note text to add

        Returns:
            True if successful
        """
        if not self.is_configured():
            return False

        # Create a note engagement
        url = f"{self.BASE_URL}/crm/v3/objects/notes"
        body = {
            "properties": {
                "hs_note_body": note,
                "hs_timestamp": datetime.now().isoformat()
            },
            "associations": [{
                "to": {"id": contact_id},
                "types": [{
                    "associationCategory": "HUBSPOT_DEFINED",
                    "associationTypeId": 202  # Note to Contact
                }]
            }]
        }

        try:
            response = self.client.post(url, json=body)
            response.raise_for_status()
            self.logger.info(f"Added note to contact {contact_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add note: {e}")
            return False

    def mark_as_won(self, contact_id: str) -> bool:
        """Mark a lead as closed/won."""
        return self.update_lead_stage(contact_id, LeadStage.CLOSED_WON)

    def mark_as_lost(self, contact_id: str, reason: str = "") -> bool:
        """Mark a lead as closed/lost with optional reason."""
        success = self.update_lead_stage(contact_id, LeadStage.CLOSED_LOST)
        if success and reason:
            self.add_note(contact_id, f"Lost reason: {reason}")
        return success

    # ==================== DELETE OPERATIONS ====================

    def delete_contact(self, contact_id: str) -> bool:
        """
        Delete a contact from HubSpot.

        Args:
            contact_id: HubSpot contact ID

        Returns:
            True if successful
        """
        if not self.is_configured():
            return False

        url = f"{self.BASE_URL}/crm/v3/objects/contacts/{contact_id}"

        try:
            response = self.client.delete(url)
            response.raise_for_status()
            self.logger.info(f"Deleted contact {contact_id}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete contact: {e}")
            return False

    # ==================== STATISTICS ====================

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get lead statistics and conversion metrics.

        Returns:
            Dictionary with various statistics
        """
        if not self.is_configured():
            return {"error": "HubSpot not configured"}

        stats = {
            "total_leads": 0,
            "by_stage": {},
            "by_source": {},
            "conversion_rate": 0.0,
            "win_rate": 0.0
        }

        # Count by stage
        for stage in LeadStage:
            contacts = self.get_contacts_by_stage(stage)
            count = len(contacts)
            stats["by_stage"][stage.value] = count
            stats["total_leads"] += count

            # Also count by source
            for contact in contacts:
                source = contact.source or "unknown"
                stats["by_source"][source] = stats["by_source"].get(source, 0) + 1

        # Calculate conversion rates
        if stats["total_leads"] > 0:
            won = stats["by_stage"].get(LeadStage.CLOSED_WON.value, 0)
            lost = stats["by_stage"].get(LeadStage.CLOSED_LOST.value, 0)
            closed_total = won + lost

            # Conversion rate = leads that reached demo or beyond / total
            advanced = (
                stats["by_stage"].get(LeadStage.DEMO.value, 0) +
                stats["by_stage"].get(LeadStage.PROPOSAL.value, 0) +
                closed_total
            )
            stats["conversion_rate"] = round(advanced / stats["total_leads"] * 100, 1)

            # Win rate = won / (won + lost)
            if closed_total > 0:
                stats["win_rate"] = round(won / closed_total * 100, 1)

        return stats

    # ==================== HELPER METHODS ====================

    def _get_existing_contact_id(self, email: str) -> Optional[str]:
        """Get contact ID by email."""
        url = f"{self.BASE_URL}/crm/v3/objects/contacts/search"
        body = {
            "filterGroups": [{
                "filters": [{
                    "propertyName": "email",
                    "operator": "EQ",
                    "value": email
                }]
            }],
            "limit": 1
        }

        try:
            response = self.client.post(url, json=body)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            return results[0]["id"] if results else None
        except Exception:
            return None
