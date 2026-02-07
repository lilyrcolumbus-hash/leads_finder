"""AI-powered lead filtering using Ollama (free, local) or Gemini (free tier)."""

import json
from typing import List, Optional

import httpx

from src.config import settings
from src.utils.logger import get_logger
from src.utils.models import Lead


class OllamaGeminiFilter:
    """Filter and qualify leads using Ollama (local) or Gemini (free API)."""

    SYSTEM_PROMPT = """You are an expert lead qualification assistant. Analyze business leads and score them.

For each lead, determine:
- Is this a real business that could be a customer? (score higher)
- Do they have contact information? (score higher)
- How relevant is the business to the niche? (score higher)

Respond ONLY with valid JSON. No markdown, no explanation outside JSON."""

    QUALIFY_TEMPLATE = """Score these leads from 0 to 1 based on quality.

Leads:
{leads_json}

Return JSON array:
[{{"id": "xxx", "score": 0.8, "is_qualified": true, "reasoning": "Real business with contact info"}}]"""

    MESSAGE_TEMPLATE = """Write a short, personalized sales outreach message (3-4 sentences max) for this business:

Business: {company}
Niche: {niche}
Location: {location}
Details: {content}

The message should:
- Be friendly and professional
- Reference their specific business/niche
- Mention a common pain point for their industry
- End with a soft call to action

Return ONLY the message text, no JSON, no quotes."""

    def __init__(self):
        self.logger = get_logger("OllamaGeminiFilter")
        self.ollama_available = False
        self.gemini_available = False
        self._check_availability()

    def _check_availability(self):
        """Check which AI backends are available."""
        # Check Ollama
        try:
            response = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=3.0)
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m.get("name", "") for m in models]
                if any(settings.ollama_model in name for name in model_names):
                    self.ollama_available = True
                    self.logger.info(f"Ollama available with model: {settings.ollama_model}")
                else:
                    self.logger.warning(f"Ollama running but model '{settings.ollama_model}' not found. Available: {model_names}")
        except Exception:
            self.logger.info("Ollama not available (not running or not installed)")

        # Check Gemini
        if settings.gemini_api_key:
            self.gemini_available = True
            self.logger.info("Gemini API key configured")

    def is_available(self) -> bool:
        """Check if any AI backend is available."""
        return self.ollama_available or self.gemini_available

    def get_backend_name(self) -> str:
        """Return the name of the active backend."""
        if self.ollama_available:
            return f"Ollama ({settings.ollama_model})"
        elif self.gemini_available:
            return "Gemini (free)"
        return "None"

    def filter_leads(self, leads: List[Lead]) -> List[Lead]:
        """Filter and qualify leads using local/free AI."""
        if not leads:
            return []

        if not self.is_available():
            self.logger.warning("No AI backend available. Returning leads with keyword-based scoring.")
            return self._keyword_fallback(leads)

        self.logger.info(f"Filtering {len(leads)} leads with {self.get_backend_name()}")

        batch_size = settings.ai_filter_batch_size
        for i in range(0, len(leads), batch_size):
            batch = leads[i:i + batch_size]
            try:
                self._score_batch(batch)
            except Exception as e:
                self.logger.error(f"Error scoring batch: {e}")
                self._keyword_fallback(batch)

        qualified = [l for l in leads if l.is_qualified]
        self.logger.info(f"Filtering complete: {len(qualified)}/{len(leads)} qualified")
        return leads

    def generate_message(self, lead: Lead) -> Optional[str]:
        """Generate a personalized outreach message for a lead."""
        if not self.is_available():
            return None

        prompt = self.MESSAGE_TEMPLATE.format(
            company=lead.company or lead.title,
            niche=lead.niche or "business",
            location=lead.location or "local area",
            content=lead.content[:300],
        )

        response = self._call_ai(prompt)
        if response:
            # Clean up the response
            message = response.strip().strip('"').strip("'")
            lead.personalized_message = message
            return message

        return None

    def _score_batch(self, leads: List[Lead]):
        """Score a batch of leads."""
        leads_data = []
        for lead in leads:
            leads_data.append({
                "id": lead.id,
                "title": lead.title[:200],
                "content": lead.content[:300],
                "company": lead.company,
                "phone": lead.phone,
                "email": lead.email,
                "website": lead.website,
                "niche": lead.niche,
                "location": lead.location,
            })

        prompt = self.QUALIFY_TEMPLATE.format(leads_json=json.dumps(leads_data, indent=2))
        response = self._call_ai(prompt)

        if not response:
            self._keyword_fallback(leads)
            return

        # Parse response
        try:
            # Clean response
            response = response.strip()
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

            scores = json.loads(response)
            score_map = {s["id"]: s for s in scores}

            for lead in leads:
                if lead.id in score_map:
                    data = score_map[lead.id]
                    lead.ai_score = float(data.get("score", 0))
                    lead.is_qualified = bool(data.get("is_qualified", False))
                    lead.ai_reasoning = data.get("reasoning", "")
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            self.logger.error(f"Failed to parse AI response: {e}")
            self._keyword_fallback(leads)

    def _call_ai(self, prompt: str) -> Optional[str]:
        """Call the available AI backend."""
        if self.ollama_available:
            return self._call_ollama(prompt)
        elif self.gemini_available:
            return self._call_gemini(prompt)
        return None

    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call Ollama local API."""
        try:
            response = httpx.post(
                f"{settings.ollama_base_url}/api/generate",
                json={
                    "model": settings.ollama_model,
                    "prompt": f"{self.SYSTEM_PROMPT}\n\n{prompt}",
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "num_predict": 2000,
                    }
                },
                timeout=120.0,  # Ollama can be slow
            )
            if response.status_code == 200:
                return response.json().get("response", "")
        except Exception as e:
            self.logger.error(f"Ollama error: {e}")

        return None

    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Google Gemini API (free tier)."""
        try:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={settings.gemini_api_key}"
            response = httpx.post(
                url,
                json={
                    "contents": [{
                        "parts": [{"text": f"{self.SYSTEM_PROMPT}\n\n{prompt}"}]
                    }],
                    "generationConfig": {
                        "temperature": 0.3,
                        "maxOutputTokens": 2000,
                    }
                },
                timeout=30.0,
            )
            if response.status_code == 200:
                data = response.json()
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "")
        except Exception as e:
            self.logger.error(f"Gemini error: {e}")

        return None

    def _keyword_fallback(self, leads: List[Lead]) -> List[Lead]:
        """Score leads based on available data when AI is not available."""
        for lead in leads:
            score = 0.3  # Base score

            # Has contact info
            if lead.email:
                score += 0.2
            if lead.phone:
                score += 0.15
            if lead.website:
                score += 0.1

            # Has business info
            if lead.company:
                score += 0.1
            if lead.address:
                score += 0.05

            # Keyword matches
            if len(lead.keywords_matched) >= 2:
                score += 0.1

            lead.ai_score = min(score, 1.0)
            lead.is_qualified = score >= 0.5
            lead.ai_reasoning = "Keyword/data-based scoring (no AI)"

        return leads
