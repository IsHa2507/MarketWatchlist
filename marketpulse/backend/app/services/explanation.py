"""
ExplanationService
Generates human-readable explanations for stock changes.

Supports LLM-based explanations (when API key is present)
and deterministic template fallbacks.
"""
from typing import Dict, Any, Optional
from app.core.config import settings


class ExplanationService:
    def generate(self, change_data: Dict[str, Any], score_data: Dict[str, Any]) -> str:
        """Generate explanation. Falls back to template if LLM unavailable."""
        if settings.LLM_API_KEY:
            try:
                return self._llm_explanation(change_data, score_data)
            except Exception:
                pass
        return self._template_explanation(change_data, score_data)

    def _template_explanation(
        self, change_data: Dict[str, Any], score_data: Dict[str, Any]
    ) -> str:
        ticker = change_data.get("ticker", "")
        company = change_data.get("company_name", ticker)
        price_pct = change_data.get("price_change_pct", 0.0)
        volume_multiplier = change_data.get("volume_multiplier", 1.0)
        sentiment_change = change_data.get("sentiment_change", "Neutral")
        classification = score_data.get("classification", "NORMAL")
        sentiment_label = change_data.get("sentiment_label", "Neutral")
        abs_price = abs(price_pct)
        direction = "rose" if price_pct > 0 else "declined"
        sign = "+" if price_pct > 0 else ""

        if classification == "CRITICAL":
            return self._critical_explanation(
                company, price_pct, volume_multiplier, sentiment_change, sentiment_label
            )
        elif classification == "IMPORTANT":
            return self._important_explanation(
                company, price_pct, volume_multiplier, sentiment_change, sentiment_label
            )
        elif classification == "WORTH_WATCHING":
            return self._watching_explanation(
                company, price_pct, volume_multiplier, sentiment_label
            )
        else:
            return f"{company} has remained largely stable since your last check, with no significant price, volume, or sentiment changes."

    def _critical_explanation(
        self, company: str, price_pct: float, volume_multiplier: float,
        sentiment_change: str, sentiment_label: str
    ) -> str:
        direction = "surged" if price_pct > 0 else "experienced a sharp decline"
        abs_price = abs(price_pct)
        vol_part = ""
        if volume_multiplier >= 2.0:
            vol_part = f" Trading volume reached {volume_multiplier:.1f}x the normal level, indicating substantial market participation."
        sent_part = ""
        if "→" in sentiment_change or sentiment_label in ("Positive", "Negative"):
            sent_part = f" Market sentiment is currently {sentiment_label.lower()}, which adds to the significance of this move."
        return (
            f"{company} {direction} {abs(price_pct):.1f}% since your last check.{vol_part}{sent_part} "
            f"This is a high-impact change that warrants close attention."
        )

    def _important_explanation(
        self, company: str, price_pct: float, volume_multiplier: float,
        sentiment_change: str, sentiment_label: str
    ) -> str:
        direction = "rose" if price_pct > 0 else "declined"
        abs_price = abs(price_pct)
        parts = [f"{company} {direction} {abs_price:.1f}% since your last check."]
        if volume_multiplier >= 1.5:
            parts.append(
                f"Unusually high trading volume ({volume_multiplier:.1f}x average) accompanied this move."
            )
        if "→" in sentiment_change:
            parts.append(f"Sentiment shifted to {sentiment_label.lower()}, suggesting a change in market perception.")
        elif sentiment_label in ("Positive", "Negative"):
            parts.append(f"{sentiment_label} sentiment also increased, making this a notable change.")
        return " ".join(parts)

    def _watching_explanation(
        self, company: str, price_pct: float, volume_multiplier: float, sentiment_label: str
    ) -> str:
        direction = "moved up" if price_pct > 0 else "moved down"
        abs_price = abs(price_pct)
        parts = [f"{company} {direction} {abs_price:.1f}% since your last check."]
        if volume_multiplier >= 1.4:
            parts.append(f"Volume was slightly elevated at {volume_multiplier:.1f}x normal levels.")
        if sentiment_label in ("Positive", "Negative"):
            parts.append(f"Sentiment leans {sentiment_label.lower()}.")
        parts.append("The change is moderate but worth monitoring.")
        return " ".join(parts)

    def _llm_explanation(self, change_data: Dict[str, Any], score_data: Dict[str, Any]) -> str:
        """LLM-based explanation using OpenAI or compatible API."""
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.LLM_API_KEY)
            ticker = change_data.get("ticker", "")
            company = change_data.get("company_name", ticker)
            price_pct = change_data.get("price_change_pct", 0.0)
            volume_multiplier = change_data.get("volume_multiplier", 1.0)
            sentiment_change = change_data.get("sentiment_change", "Neutral")
            score = score_data.get("attention_score", 0.0)
            classification = score_data.get("classification", "NORMAL")

            prompt = f"""
You are a concise market analysis assistant. Write a 2-3 sentence explanation for why a stock changed.

Stock: {company} ({ticker})
Price change: {price_pct:+.1f}% since the user's last check
Volume: {volume_multiplier:.1f}x average trading volume
Sentiment: {sentiment_change}
Attention Score: {score:.0f}/100 ({classification})

Rules:
- Be factual and neutral
- Never give buy/sell recommendations
- Never predict future prices
- Use phrases like "Needs Attention", "Significant Change", "Worth Watching"
- Keep to 2-3 sentences maximum
"""
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            raise e
