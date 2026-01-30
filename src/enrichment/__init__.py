"""Enrichment modules for lead data enhancement."""

from .apollo_enricher import ApolloEnricher, enrich_leads_with_apollo
from .email_verifier import (
    EmailVerifier,
    EmailVerificationResult,
    EmailStatus,
    EmailRisk,
    ZeroBounceVerifier,
    HunterVerifier,
    verify_lead_email,
    get_email_quality_for_scoring
)

__all__ = [
    # Apollo enrichment
    "ApolloEnricher",
    "enrich_leads_with_apollo",
    # Email verification
    "EmailVerifier",
    "EmailVerificationResult",
    "EmailStatus",
    "EmailRisk",
    "ZeroBounceVerifier",
    "HunterVerifier",
    "verify_lead_email",
    "get_email_quality_for_scoring"
]
