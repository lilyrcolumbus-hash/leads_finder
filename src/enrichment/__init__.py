"""Enrichment modules for lead data enhancement."""

from .hunter import HunterClient

try:
    from .apollo_enricher import ApolloEnricher, enrich_leads_with_apollo
except ImportError:
    ApolloEnricher = None
    enrich_leads_with_apollo = None

__all__ = ["ApolloEnricher", "enrich_leads_with_apollo", "HunterClient"]
