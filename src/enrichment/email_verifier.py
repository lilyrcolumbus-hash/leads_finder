"""
Email Verification Module

Provides email verification through multiple providers:
- ZeroBounce: Industry leader in email validation (99%+ accuracy)
- Hunter.io: Email verification with deliverability scoring

ZEROBOUNCE API DOCS: https://www.zerobounce.net/docs/
HUNTER.IO API DOCS: https://hunter.io/api-documentation/v2#email-verifier

PRICING (as of 2024):
ZeroBounce:
- Free: 100 verifications/month
- Pay as you go: $0.008 per verification
- Bulk: Starting at $15 for 2,000 verifications

Hunter.io:
- Free: 25 verifications/month
- Starter: $49/month - 1,000 verifications
- Growth: $149/month - 5,000 verifications

VERIFICATION STATUSES:
- valid: Email exists and can receive mail
- invalid: Email does not exist or cannot receive mail
- catch_all: Domain accepts all emails (can't verify specific address)
- disposable: Temporary/throwaway email address
- spam_trap: Known spam trap address (high risk)
- unknown: Could not determine status
"""

import os
import time
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class EmailStatus(str, Enum):
    """Email verification status."""
    VALID = "valid"
    INVALID = "invalid"
    CATCH_ALL = "catch_all"
    DISPOSABLE = "disposable"
    SPAM_TRAP = "spam_trap"
    UNKNOWN = "unknown"
    ROLE_BASED = "role_based"  # info@, support@, etc.
    ABUSE = "abuse"  # Known complainer


class EmailRisk(str, Enum):
    """Email risk level for outreach."""
    LOW = "low"        # Safe to send
    MEDIUM = "medium"  # Use caution
    HIGH = "high"      # Avoid sending
    CRITICAL = "critical"  # Do not send


@dataclass
class EmailVerificationResult:
    """Result of email verification."""
    email: str
    status: EmailStatus
    risk: EmailRisk
    deliverable: bool

    # Confidence and scoring
    confidence_score: float  # 0-100
    quality_score: float     # 0-100 (for lead scoring)

    # Provider-specific data
    provider: str  # zerobounce, hunter, combined

    # Detailed info
    is_free_email: bool = False       # gmail, yahoo, etc.
    is_disposable: bool = False       # temp mail services
    is_role_based: bool = False       # info@, support@, etc.
    is_catch_all: bool = False        # Domain accepts all
    is_spam_trap: bool = False        # Known spam trap

    # SMTP check results
    smtp_valid: Optional[bool] = None
    mx_found: bool = True

    # Additional data
    domain: Optional[str] = None
    suggested_correction: Optional[str] = None  # For typos
    reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None


class ZeroBounceVerifier:
    """
    ZeroBounce email verification client.

    Industry leader with 99%+ accuracy.
    Provides detailed deliverability analysis.
    """

    BASE_URL = "https://api.zerobounce.net/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ZEROBOUNCE_API_KEY")
        self.session = requests.Session()

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def verify(self, email: str, ip_address: Optional[str] = None) -> Optional[EmailVerificationResult]:
        """
        Verify a single email address.

        Args:
            email: Email address to verify
            ip_address: Optional IP for additional context

        Returns:
            EmailVerificationResult or None if error
        """
        if not self.is_configured():
            logger.warning("ZeroBounce API key not configured")
            return None

        params = {
            "api_key": self.api_key,
            "email": email
        }
        if ip_address:
            params["ip_address"] = ip_address

        try:
            response = self.session.get(
                f"{self.BASE_URL}/validate",
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_response(email, data)
            else:
                logger.error(f"ZeroBounce API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"ZeroBounce request failed: {e}")
            return None

    def verify_batch(self, emails: List[str]) -> Dict[str, EmailVerificationResult]:
        """
        Verify multiple emails (uses batch API for efficiency).

        Note: Batch API requires file upload, so we use sequential for simplicity.
        For large batches, consider using the file upload API.
        """
        results = {}
        for email in emails:
            result = self.verify(email)
            if result:
                results[email] = result
            time.sleep(0.1)  # Small delay between requests
        return results

    def get_credits(self) -> Optional[int]:
        """Get remaining API credits."""
        if not self.is_configured():
            return None

        try:
            response = self.session.get(
                f"{self.BASE_URL}/getcredits",
                params={"api_key": self.api_key},
                timeout=10
            )
            if response.status_code == 200:
                data = response.json()
                return int(data.get("Credits", 0))
        except Exception as e:
            logger.error(f"Failed to get ZeroBounce credits: {e}")
        return None

    def _parse_response(self, email: str, data: Dict) -> EmailVerificationResult:
        """Parse ZeroBounce API response."""
        status_map = {
            "valid": EmailStatus.VALID,
            "invalid": EmailStatus.INVALID,
            "catch-all": EmailStatus.CATCH_ALL,
            "spamtrap": EmailStatus.SPAM_TRAP,
            "abuse": EmailStatus.ABUSE,
            "do_not_mail": EmailStatus.INVALID,
            "unknown": EmailStatus.UNKNOWN
        }

        sub_status = data.get("sub_status", "").lower()
        zb_status = data.get("status", "unknown").lower()

        # Determine email status
        if sub_status == "disposable":
            status = EmailStatus.DISPOSABLE
        elif sub_status == "role_based":
            status = EmailStatus.ROLE_BASED
        else:
            status = status_map.get(zb_status, EmailStatus.UNKNOWN)

        # Determine risk level
        risk = self._calculate_risk(status, data)

        # Calculate quality score for lead scoring
        quality_score = self._calculate_quality_score(status, data)

        # Determine deliverability
        deliverable = status == EmailStatus.VALID

        return EmailVerificationResult(
            email=email,
            status=status,
            risk=risk,
            deliverable=deliverable,
            confidence_score=data.get("confidence", 0) or 0,
            quality_score=quality_score,
            provider="zerobounce",
            is_free_email=data.get("free_email", False),
            is_disposable=sub_status == "disposable",
            is_role_based=sub_status == "role_based",
            is_catch_all=zb_status == "catch-all",
            is_spam_trap=zb_status == "spamtrap",
            smtp_valid=data.get("smtp_provider") is not None,
            mx_found=data.get("mx_found") == "true",
            domain=data.get("domain"),
            suggested_correction=data.get("did_you_mean"),
            reason=data.get("sub_status"),
            raw_response=data
        )

    def _calculate_risk(self, status: EmailStatus, data: Dict) -> EmailRisk:
        """Calculate risk level based on verification result."""
        if status == EmailStatus.SPAM_TRAP:
            return EmailRisk.CRITICAL
        elif status == EmailStatus.INVALID:
            return EmailRisk.HIGH
        elif status in [EmailStatus.DISPOSABLE, EmailStatus.ABUSE]:
            return EmailRisk.HIGH
        elif status == EmailStatus.CATCH_ALL:
            return EmailRisk.MEDIUM
        elif status == EmailStatus.ROLE_BASED:
            return EmailRisk.MEDIUM
        elif status == EmailStatus.VALID:
            return EmailRisk.LOW
        else:
            return EmailRisk.MEDIUM

    def _calculate_quality_score(self, status: EmailStatus, data: Dict) -> float:
        """Calculate quality score for lead scoring."""
        base_scores = {
            EmailStatus.VALID: 100,
            EmailStatus.CATCH_ALL: 60,
            EmailStatus.ROLE_BASED: 50,
            EmailStatus.UNKNOWN: 30,
            EmailStatus.DISPOSABLE: 10,
            EmailStatus.INVALID: 0,
            EmailStatus.SPAM_TRAP: 0,
            EmailStatus.ABUSE: 0
        }

        score = base_scores.get(status, 30)

        # Reduce score for free email providers (less professional)
        if data.get("free_email"):
            score *= 0.8

        # Boost for MX records found
        if data.get("mx_found") == "true":
            score = min(100, score * 1.05)

        return round(score, 1)


class HunterVerifier:
    """
    Hunter.io email verification client.

    Known for strong domain intelligence and accuracy.
    Good for B2B email verification.
    """

    BASE_URL = "https://api.hunter.io/v2"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("HUNTER_API_KEY")
        self.session = requests.Session()

    def is_configured(self) -> bool:
        """Check if API key is configured."""
        return bool(self.api_key)

    def verify(self, email: str) -> Optional[EmailVerificationResult]:
        """
        Verify a single email address.

        Args:
            email: Email address to verify

        Returns:
            EmailVerificationResult or None if error
        """
        if not self.is_configured():
            logger.warning("Hunter.io API key not configured")
            return None

        params = {
            "api_key": self.api_key,
            "email": email
        }

        try:
            response = self.session.get(
                f"{self.BASE_URL}/email-verifier",
                params=params,
                timeout=30
            )

            if response.status_code == 200:
                data = response.json()
                return self._parse_response(email, data.get("data", {}))
            elif response.status_code == 202:
                # Verification in progress, retry after delay
                logger.info(f"Hunter.io verification in progress for {email}")
                time.sleep(2)
                return self.verify(email)  # Retry once
            else:
                logger.error(f"Hunter.io API error: {response.status_code} - {response.text}")
                return None

        except requests.exceptions.RequestException as e:
            logger.error(f"Hunter.io request failed: {e}")
            return None

    def _parse_response(self, email: str, data: Dict) -> EmailVerificationResult:
        """Parse Hunter.io API response."""
        result = data.get("result", "unknown")
        score = data.get("score", 0) or 0

        # Map Hunter status to our status
        status_map = {
            "deliverable": EmailStatus.VALID,
            "undeliverable": EmailStatus.INVALID,
            "risky": EmailStatus.CATCH_ALL,
            "unknown": EmailStatus.UNKNOWN
        }

        status = status_map.get(result, EmailStatus.UNKNOWN)

        # Check for disposable
        if data.get("disposable"):
            status = EmailStatus.DISPOSABLE

        # Determine risk
        if status == EmailStatus.VALID:
            risk = EmailRisk.LOW
        elif status == EmailStatus.CATCH_ALL:
            risk = EmailRisk.MEDIUM
        elif status in [EmailStatus.DISPOSABLE, EmailStatus.INVALID]:
            risk = EmailRisk.HIGH
        else:
            risk = EmailRisk.MEDIUM

        # Calculate quality score
        quality_score = self._calculate_quality_score(score, data)

        return EmailVerificationResult(
            email=email,
            status=status,
            risk=risk,
            deliverable=(result == "deliverable"),
            confidence_score=score,
            quality_score=quality_score,
            provider="hunter",
            is_free_email=data.get("webmail", False),
            is_disposable=data.get("disposable", False),
            is_role_based=data.get("role", False),
            is_catch_all=data.get("accept_all", False),
            mx_found=data.get("mx_records", False),
            smtp_valid=data.get("smtp_check", False),
            domain=email.split("@")[1] if "@" in email else None,
            reason=data.get("status"),
            raw_response=data
        )

    def _calculate_quality_score(self, hunter_score: int, data: Dict) -> float:
        """Calculate quality score from Hunter data."""
        score = float(hunter_score)

        # Penalties
        if data.get("disposable"):
            score *= 0.1
        if data.get("webmail"):  # Free email
            score *= 0.8
        if data.get("role"):  # Role-based
            score *= 0.7
        if not data.get("mx_records"):
            score *= 0.5

        return round(score, 1)


class EmailVerifier:
    """
    Unified email verification interface.

    Uses multiple providers for best results:
    1. ZeroBounce (primary) - Most accurate
    2. Hunter.io (fallback) - Good B2B coverage

    Usage:
        verifier = EmailVerifier()

        # Verify single email
        result = verifier.verify("john@company.com")

        # Verify multiple emails
        results = verifier.verify_batch(["john@a.com", "jane@b.com"])

        # Check if email is safe to send
        if result.deliverable and result.risk == EmailRisk.LOW:
            send_email(result.email)
    """

    def __init__(
        self,
        zerobounce_key: Optional[str] = None,
        hunter_key: Optional[str] = None,
        prefer_provider: str = "zerobounce"
    ):
        """
        Initialize email verifier.

        Args:
            zerobounce_key: ZeroBounce API key
            hunter_key: Hunter.io API key
            prefer_provider: Preferred provider ("zerobounce" or "hunter")
        """
        self.zerobounce = ZeroBounceVerifier(zerobounce_key)
        self.hunter = HunterVerifier(hunter_key)
        self.prefer_provider = prefer_provider

    def is_configured(self) -> bool:
        """Check if at least one provider is configured."""
        return self.zerobounce.is_configured() or self.hunter.is_configured()

    def get_available_providers(self) -> List[str]:
        """Get list of configured providers."""
        providers = []
        if self.zerobounce.is_configured():
            providers.append("zerobounce")
        if self.hunter.is_configured():
            providers.append("hunter")
        return providers

    def verify(
        self,
        email: str,
        use_fallback: bool = True,
        combine_results: bool = False
    ) -> Optional[EmailVerificationResult]:
        """
        Verify an email address.

        Args:
            email: Email address to verify
            use_fallback: If primary fails, try secondary provider
            combine_results: Use both providers and combine results

        Returns:
            EmailVerificationResult or None
        """
        if not self.is_configured():
            logger.warning("No email verification providers configured")
            return None

        # Validate email format first
        if not self._is_valid_email_format(email):
            return EmailVerificationResult(
                email=email,
                status=EmailStatus.INVALID,
                risk=EmailRisk.HIGH,
                deliverable=False,
                confidence_score=100,
                quality_score=0,
                provider="format_check",
                reason="Invalid email format"
            )

        result = None

        # Try preferred provider first
        if self.prefer_provider == "zerobounce" and self.zerobounce.is_configured():
            result = self.zerobounce.verify(email)
        elif self.prefer_provider == "hunter" and self.hunter.is_configured():
            result = self.hunter.verify(email)

        # Fallback to other provider if needed
        if not result and use_fallback:
            if self.prefer_provider == "zerobounce" and self.hunter.is_configured():
                result = self.hunter.verify(email)
            elif self.prefer_provider == "hunter" and self.zerobounce.is_configured():
                result = self.zerobounce.verify(email)

        # Combine results from both providers
        if combine_results and result:
            result = self._combine_results(email, result)

        return result

    def verify_batch(
        self,
        emails: List[str],
        delay_seconds: float = 0.3,
        max_verifications: int = 100
    ) -> Dict[str, EmailVerificationResult]:
        """
        Verify multiple email addresses.

        Args:
            emails: List of email addresses
            delay_seconds: Delay between API calls
            max_verifications: Maximum emails to verify

        Returns:
            Dict mapping email to verification result
        """
        results = {}
        verified_count = 0

        for email in emails:
            if verified_count >= max_verifications:
                logger.info(f"Reached max verifications ({max_verifications})")
                break

            result = self.verify(email)
            if result:
                results[email] = result
                verified_count += 1

            if delay_seconds > 0:
                time.sleep(delay_seconds)

        return results

    def get_quality_score(self, email: str) -> Tuple[float, str]:
        """
        Get email quality score for lead scoring.

        Returns:
            Tuple of (score 0-100, reason)
        """
        result = self.verify(email)
        if not result:
            return (30.0, "Could not verify email")

        reasons = []
        if result.is_disposable:
            reasons.append("disposable email")
        if result.is_free_email:
            reasons.append("free email provider")
        if result.is_role_based:
            reasons.append("role-based address")
        if not result.deliverable:
            reasons.append("not deliverable")
        if result.is_catch_all:
            reasons.append("catch-all domain")

        reason = ", ".join(reasons) if reasons else "valid professional email"
        return (result.quality_score, reason)

    def _is_valid_email_format(self, email: str) -> bool:
        """Basic email format validation."""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))

    def _combine_results(
        self,
        email: str,
        primary_result: EmailVerificationResult
    ) -> EmailVerificationResult:
        """
        Combine results from multiple providers for higher accuracy.
        """
        # Get result from secondary provider
        if primary_result.provider == "zerobounce" and self.hunter.is_configured():
            secondary_result = self.hunter.verify(email)
        elif primary_result.provider == "hunter" and self.zerobounce.is_configured():
            secondary_result = self.zerobounce.verify(email)
        else:
            return primary_result

        if not secondary_result:
            return primary_result

        # Combine scores
        combined_confidence = (
            primary_result.confidence_score * 0.6 +
            secondary_result.confidence_score * 0.4
        )
        combined_quality = (
            primary_result.quality_score * 0.6 +
            secondary_result.quality_score * 0.4
        )

        # Use stricter validation (if either says invalid, it's invalid)
        if (primary_result.status == EmailStatus.INVALID or
            secondary_result.status == EmailStatus.INVALID):
            combined_status = EmailStatus.INVALID
            combined_deliverable = False
        elif (primary_result.status == EmailStatus.SPAM_TRAP or
              secondary_result.status == EmailStatus.SPAM_TRAP):
            combined_status = EmailStatus.SPAM_TRAP
            combined_deliverable = False
        else:
            combined_status = primary_result.status
            combined_deliverable = primary_result.deliverable

        # Use higher risk level
        risk_order = [EmailRisk.LOW, EmailRisk.MEDIUM, EmailRisk.HIGH, EmailRisk.CRITICAL]
        combined_risk = max(
            primary_result.risk,
            secondary_result.risk,
            key=lambda r: risk_order.index(r)
        )

        return EmailVerificationResult(
            email=email,
            status=combined_status,
            risk=combined_risk,
            deliverable=combined_deliverable,
            confidence_score=round(combined_confidence, 1),
            quality_score=round(combined_quality, 1),
            provider="combined",
            is_free_email=primary_result.is_free_email or secondary_result.is_free_email,
            is_disposable=primary_result.is_disposable or secondary_result.is_disposable,
            is_role_based=primary_result.is_role_based or secondary_result.is_role_based,
            is_catch_all=primary_result.is_catch_all or secondary_result.is_catch_all,
            is_spam_trap=primary_result.is_spam_trap or secondary_result.is_spam_trap,
            mx_found=primary_result.mx_found and secondary_result.mx_found,
            domain=primary_result.domain,
            suggested_correction=primary_result.suggested_correction,
            reason=f"ZB: {primary_result.reason}, Hunter: {secondary_result.reason}",
            raw_response={
                "zerobounce": primary_result.raw_response if primary_result.provider == "zerobounce" else secondary_result.raw_response,
                "hunter": secondary_result.raw_response if secondary_result.provider == "hunter" else primary_result.raw_response
            }
        )


# Convenience functions for integration with lead enrichment

def verify_lead_email(email: str, verifier: Optional[EmailVerifier] = None) -> Optional[EmailVerificationResult]:
    """
    Verify a single lead's email address.

    Args:
        email: Email to verify
        verifier: EmailVerifier instance (creates new if not provided)

    Returns:
        EmailVerificationResult or None
    """
    if not verifier:
        verifier = EmailVerifier()

    if not verifier.is_configured():
        logger.warning("Email verification not configured. Set ZEROBOUNCE_API_KEY or HUNTER_API_KEY.")
        return None

    return verifier.verify(email)


def get_email_quality_for_scoring(email: str, verifier: Optional[EmailVerifier] = None) -> Dict[str, Any]:
    """
    Get email quality data for lead scoring.

    Returns dict with:
    - quality_score: 0-100 score for lead scoring
    - deliverable: boolean
    - risk: low/medium/high/critical
    - flags: list of flags (disposable, free_email, etc.)
    """
    if not verifier:
        verifier = EmailVerifier()

    if not verifier.is_configured():
        return {
            "quality_score": 50,  # Neutral score
            "deliverable": None,
            "risk": "unknown",
            "flags": ["not_verified"]
        }

    result = verifier.verify(email)

    if not result:
        return {
            "quality_score": 30,
            "deliverable": None,
            "risk": "unknown",
            "flags": ["verification_failed"]
        }

    flags = []
    if result.is_disposable:
        flags.append("disposable")
    if result.is_free_email:
        flags.append("free_email")
    if result.is_role_based:
        flags.append("role_based")
    if result.is_catch_all:
        flags.append("catch_all")
    if result.is_spam_trap:
        flags.append("spam_trap")
    if not result.deliverable:
        flags.append("undeliverable")

    return {
        "quality_score": result.quality_score,
        "deliverable": result.deliverable,
        "risk": result.risk.value,
        "flags": flags,
        "status": result.status.value,
        "confidence": result.confidence_score
    }
