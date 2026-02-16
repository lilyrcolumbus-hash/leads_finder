"""AI-powered lead filtering using OpenAI, Anthropic, or Google Gemini."""

import json
from typing import List, Optional, Tuple

import httpx

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead


class AILeadFilter:
    """Filter leads using AI to identify qualified business owners."""

    SYSTEM_PROMPT = """You are an expert lead qualification assistant. Your job is to analyze social media posts, forum discussions, and search results to identify business owners who have problems with:

1. Missed phone calls or messages
2. Difficulty answering customer calls
3. Scheduling and appointment problems
4. Customer complaints about communication
5. Need for receptionist or answering service

For each lead, determine:
- Is this person likely a business owner or decision maker? (not an employee complaining)
- Do they have a real pain point we can solve?
- How urgent does their problem seem?

Respond ONLY with valid JSON. No markdown, no explanation outside JSON."""

    USER_PROMPT_TEMPLATE = """Analyze these potential leads and score each one from 0 to 1 based on qualification criteria.

Leads to analyze:
{leads_json}

For each lead, return a JSON object with:
- "id": the lead ID
- "score": float from 0 to 1 (1 = highly qualified)
- "is_qualified": boolean (true if score >= 0.3, meaning it's worth reaching out)
- "has_explicit_pain": boolean (true ONLY if they explicitly mention a problem like missed calls, complaints, need help)
- "category": one of "pain", "opportunity", or "cold"
  - "pain": score >= 0.6 AND has explicit problem/complaint mentioned
  - "opportunity": score 0.3-0.6 OR score >= 0.6 but no explicit pain (potential customer)
  - "cold": score < 0.3 (low priority but keep for reference)
- "reasoning": brief explanation (max 100 chars)

Return a JSON array of these objects. Example:
[{{"id": "abc123", "score": 0.8, "is_qualified": true, "has_explicit_pain": true, "category": "pain", "reasoning": "Business owner mentions missed calls costing customers"}}]"""

    def __init__(self):
        self.logger = get_logger("AIFilter")
        self.openai_client = None
        self.anthropic_client = None
        self.gemini_model = None
        self.gemini_api_key = None
        self._init_clients()

    def _init_clients(self):
        """Initialize AI clients based on available API keys."""
        # Try Gemini first (user's preferred) - uses REST API directly
        if settings.gemini_api_key:
            self.gemini_api_key = settings.gemini_api_key
            self.gemini_model = "gemini-2.0-flash"
            self.logger.info("Initialized Google Gemini client (REST API)")

        if settings.openai_api_key:
            try:
                from openai import OpenAI
                self.openai_client = OpenAI(api_key=settings.openai_api_key)
                self.logger.info("Initialized OpenAI client")
            except Exception as e:
                self.logger.warning(f"Failed to initialize OpenAI: {e}")

        if settings.anthropic_api_key:
            try:
                import anthropic
                self.anthropic_client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
                self.logger.info("Initialized Anthropic client")
            except Exception as e:
                self.logger.warning(f"Failed to initialize Anthropic: {e}")

    def filter_leads(self, leads: List[Lead]) -> List[Lead]:
        """
        Analyze and categorize leads using AI.

        Args:
            leads: List of leads to analyze

        Returns:
            List of ALL leads with AI scores and categories (pain/opportunity/cold)
        """
        from src.utils.models import LeadCategory

        if not leads:
            return []

        if not self.openai_client and not self.anthropic_client and not self.gemini_model:
            self.logger.warning("No AI client available. Returning leads with keyword-based categories.")
            # Assign categories based on keyword count only (no ai_score set)
            for lead in leads:
                if len(lead.keywords_matched) >= 3:
                    lead.lead_category = LeadCategory.PAIN
                    lead.is_qualified = True
                elif len(lead.keywords_matched) >= 1:
                    lead.lead_category = LeadCategory.OPPORTUNITY
                    lead.is_qualified = True
                else:
                    lead.lead_category = LeadCategory.COLD
                    lead.is_qualified = False
                # ai_score stays None to indicate no real AI was used
            return leads

        self.logger.info(f"Analyzing {len(leads)} leads with AI")

        all_leads = []
        batch_size = settings.ai_filter_batch_size

        # Process in batches
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i + batch_size]
            try:
                scored_leads = self._score_batch(batch)
                all_leads.extend(scored_leads)
            except Exception as e:
                self.logger.error(f"Error scoring batch: {e}")
                # On error, categorize based on keywords
                for lead in batch:
                    if len(lead.keywords_matched) >= 3:
                        lead.lead_category = LeadCategory.PAIN
                        lead.is_qualified = True
                        lead.ai_score = 0.7
                        lead.ai_reasoning = "Fallback: Multiple pain keywords matched"
                        lead.has_explicit_pain = True
                    elif len(lead.keywords_matched) >= 1:
                        lead.lead_category = LeadCategory.OPPORTUNITY
                        lead.is_qualified = True
                        lead.ai_score = 0.4
                        lead.ai_reasoning = "Fallback: Keywords matched, potential opportunity"
                    else:
                        lead.lead_category = LeadCategory.COLD
                        lead.is_qualified = False
                        lead.ai_score = 0.2
                        lead.ai_reasoning = "Fallback: No clear indicators"
                    all_leads.append(lead)

        # Count by category
        pain_count = len([l for l in all_leads if l.lead_category == LeadCategory.PAIN])
        opportunity_count = len([l for l in all_leads if l.lead_category == LeadCategory.OPPORTUNITY])
        cold_count = len([l for l in all_leads if l.lead_category == LeadCategory.COLD])

        self.logger.info(
            f"AI analysis complete: {pain_count} pain, {opportunity_count} opportunity, {cold_count} cold"
        )

        return all_leads

    def _score_batch(self, leads: List[Lead]) -> List[Lead]:
        """Score a batch of leads using AI."""
        # Prepare leads for AI
        leads_data = []
        for lead in leads:
            leads_data.append({
                "id": lead.id,
                "source": lead.source.value,
                "title": lead.title[:200],
                "content": lead.content[:500],
                "keywords": lead.keywords_matched,
                "username": lead.username,
                "company": lead.company
            })

        prompt = self.USER_PROMPT_TEMPLATE.format(leads_json=json.dumps(leads_data, indent=2))

        # Try Gemini first, then OpenAI, then Anthropic
        response_text = None
        if self.gemini_model:
            response_text = self._call_gemini(prompt)
        elif self.openai_client:
            response_text = self._call_openai(prompt)
        elif self.anthropic_client:
            response_text = self._call_anthropic(prompt)

        if not response_text:
            raise Exception("No AI response received")

        # Parse response and update leads
        return self._parse_ai_response(response_text, leads)

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Google Gemini API via REST (avoids gRPC SSL issues)."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.gemini_model}:generateContent"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": f"{self.SYSTEM_PROMPT}\n\n{prompt}"}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.3,
                    "maxOutputTokens": 4000
                }
            }
            response = httpx.post(
                url,
                params={"key": self.gemini_api_key},
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            self.logger.error(f"Gemini API error: {e}")
            return None

    def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API."""
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"OpenAI API error: {e}")
            return None

    def _call_anthropic(self, prompt: str) -> Optional[str]:
        """Call Anthropic API."""
        try:
            response = self.anthropic_client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=2000,
                system=self.SYSTEM_PROMPT,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )
            return response.content[0].text
        except Exception as e:
            self.logger.error(f"Anthropic API error: {e}")
            return None

    def _parse_ai_response(self, response_text: str, leads: List[Lead]) -> List[Lead]:
        """Parse AI response and update lead scores."""
        # Clean response - remove markdown code blocks if present
        response_text = response_text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1] if lines[-1] == "```" else lines[1:])

        try:
            scores = json.loads(response_text)
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse AI response as JSON: {e}")
            self.logger.debug(f"Response was: {response_text[:500]}")
            raise

        # Create mapping of scores by ID
        score_map = {s["id"]: s for s in scores}

        # Update leads with scores and categories
        from src.utils.models import LeadCategory

        for lead in leads:
            if lead.id in score_map:
                score_data = score_map[lead.id]
                lead.ai_score = float(score_data.get("score", 0))
                lead.is_qualified = bool(score_data.get("is_qualified", False))
                lead.ai_reasoning = score_data.get("reasoning", "")
                lead.has_explicit_pain = bool(score_data.get("has_explicit_pain", False))

                # Set lead category from AI response or calculate from score
                category_str = score_data.get("category", "").lower()
                if category_str == "pain":
                    lead.lead_category = LeadCategory.PAIN
                elif category_str == "opportunity":
                    lead.lead_category = LeadCategory.OPPORTUNITY
                elif category_str == "cold":
                    lead.lead_category = LeadCategory.COLD
                else:
                    # Fallback: calculate category from score
                    if lead.ai_score >= 0.6 and lead.has_explicit_pain:
                        lead.lead_category = LeadCategory.PAIN
                    elif lead.ai_score >= 0.3:
                        lead.lead_category = LeadCategory.OPPORTUNITY
                    else:
                        lead.lead_category = LeadCategory.COLD

        return leads
