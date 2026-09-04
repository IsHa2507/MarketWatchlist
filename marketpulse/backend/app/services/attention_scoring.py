"""
AttentionScoringService
Calculates explainable Attention Scores from change signals.

Weights:
  35% Price Movement
  20% Volume Anomaly
  20% News/Sentiment
  15% Volatility Change
  10% Technical Signal
"""
from typing import Dict, Any, List
import math


CLASSIFICATION_THRESHOLDS = {
    "CRITICAL": 81,
    "IMPORTANT": 61,
    "WORTH_WATCHING": 31,
    "NORMAL": 0,
}


def classify_score(score: float) -> str:
    if score >= CLASSIFICATION_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif score >= CLASSIFICATION_THRESHOLDS["IMPORTANT"]:
        return "IMPORTANT"
    elif score >= CLASSIFICATION_THRESHOLDS["WORTH_WATCHING"]:
        return "WORTH_WATCHING"
    else:
        return "NORMAL"


def _score_price(price_change_pct: float) -> float:
    """Normalize price movement to 0-100. Larger absolute moves score higher."""
    abs_change = abs(price_change_pct)
    # >10% = 100, 5% = 75, 2% = 50, 1% = 30, <0.5% = 10
    if abs_change >= 10:
        return 100.0
    elif abs_change >= 5:
        return 75 + (abs_change - 5) * 5
    elif abs_change >= 2:
        return 50 + (abs_change - 2) * 8.33
    elif abs_change >= 1:
        return 30 + (abs_change - 1) * 20
    elif abs_change >= 0.5:
        return 10 + (abs_change - 0.5) * 40
    else:
        return abs_change * 20


def _score_volume(volume_multiplier: float) -> float:
    """Normalize volume anomaly to 0-100."""
    # 3x = 100, 2x = 75, 1.5x = 50, 1.2x = 25, 1x = 5
    if volume_multiplier >= 3.0:
        return 100.0
    elif volume_multiplier >= 2.0:
        return 75 + (volume_multiplier - 2.0) * 25
    elif volume_multiplier >= 1.5:
        return 50 + (volume_multiplier - 1.5) * 50
    elif volume_multiplier >= 1.2:
        return 25 + (volume_multiplier - 1.2) * 83.33
    elif volume_multiplier >= 1.0:
        return 5 + (volume_multiplier - 1.0) * 100
    else:
        # Below average volume
        return max(0, 5 * volume_multiplier)


def _score_sentiment(sentiment_score: float, sentiment_change: str) -> float:
    """Score based on sentiment magnitude and direction change."""
    base = abs(sentiment_score) * 80  # -1 to 1 → 0 to 80
    # Bonus if sentiment direction changed
    if "→" in sentiment_change:
        base += 20
    return min(100.0, base)


def _score_volatility(volatility_change_pct: float) -> float:
    """Score volatility change (percent change in volatility)."""
    abs_change = abs(volatility_change_pct)
    if abs_change >= 100:
        return 100.0
    elif abs_change >= 50:
        return 75 + (abs_change - 50) * 0.5
    elif abs_change >= 25:
        return 50 + (abs_change - 25) * 1
    elif abs_change >= 10:
        return 25 + (abs_change - 10) * 1.67
    else:
        return abs_change * 2.5


def _score_technical(price_change_pct: float, volume_multiplier: float) -> float:
    """
    Simple technical signal: combines direction + volume confirmation.
    High volume + strong directional move = high technical signal.
    """
    strength = abs(price_change_pct) / 10  # 0 to 1+ for moves up to 10%
    vol_confirm = min(volume_multiplier / 2.0, 1.0)  # 0 to 1 for volumes up to 2x
    return min(100.0, strength * vol_confirm * 100)


class AttentionScoringService:
    def calculate(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Attention Score from change signals.
        Returns score, classification, components, and explanation.
        """
        price_change_pct = change_data.get("price_change_pct", 0.0)
        volume_multiplier = change_data.get("volume_multiplier", 1.0)
        sentiment_score = change_data.get("current_sentiment", 0.0)
        sentiment_change = change_data.get("sentiment_change", "Neutral")
        volatility_change_pct = change_data.get("volatility_change_pct", 0.0)

        # Component scores
        price_component = _score_price(price_change_pct)
        volume_component = _score_volume(volume_multiplier)
        sentiment_component = _score_sentiment(sentiment_score, sentiment_change)
        volatility_component = _score_volatility(volatility_change_pct)
        technical_component = _score_technical(price_change_pct, volume_multiplier)

        # Weighted attention score
        attention_score = (
            0.35 * price_component
            + 0.20 * volume_component
            + 0.20 * sentiment_component
            + 0.15 * volatility_component
            + 0.10 * technical_component
        )
        attention_score = round(min(100.0, attention_score), 1)

        classification = classify_score(attention_score)

        # Generate key reasons
        key_reasons = self._generate_key_reasons(
            price_change_pct,
            volume_multiplier,
            sentiment_score,
            sentiment_change,
            volatility_change_pct,
        )

        return {
            "attention_score": attention_score,
            "classification": classification,
            "components": {
                "price": round(price_component, 1),
                "volume": round(volume_component, 1),
                "sentiment": round(sentiment_component, 1),
                "volatility": round(volatility_component, 1),
                "technical": round(technical_component, 1),
            },
            "key_reasons": key_reasons,
        }

    def _generate_key_reasons(
        self,
        price_change_pct: float,
        volume_multiplier: float,
        sentiment_score: float,
        sentiment_change: str,
        volatility_change_pct: float,
    ) -> List[str]:
        reasons = []

        abs_price = abs(price_change_pct)
        if abs_price >= 5:
            direction = "surge" if price_change_pct > 0 else "decline"
            reasons.append(f"Significant price {direction} of {abs_price:.1f}%")
        elif abs_price >= 2:
            direction = "up" if price_change_pct > 0 else "down"
            reasons.append(f"Notable price move {direction} {abs_price:.1f}%")
        elif abs_price >= 1:
            reasons.append(f"Price movement of {abs_price:.1f}%")

        if volume_multiplier >= 2.0:
            reasons.append(f"Volume {volume_multiplier:.1f}x normal — unusually high activity")
        elif volume_multiplier >= 1.5:
            reasons.append(f"Volume {volume_multiplier:.1f}x average — above normal activity")
        elif volume_multiplier <= 0.7:
            reasons.append("Unusually low trading volume")

        if "→" in sentiment_change:
            reasons.append(f"Sentiment shifted: {sentiment_change}")
        elif abs(sentiment_score) > 0.4:
            direction = "Positive" if sentiment_score > 0 else "Negative"
            reasons.append(f"{direction} market sentiment")

        if abs(volatility_change_pct) >= 30:
            direction = "increased" if volatility_change_pct > 0 else "decreased"
            reasons.append(f"Volatility {direction} {abs(volatility_change_pct):.0f}%")

        if not reasons:
            reasons.append("No significant changes detected")

        return reasons[:4]  # Cap at 4 reasons
