"""
AttentionScoringService
=======================
Calculates explainable Attention Scores (0–100) from change signals.

Weights (UNCHANGED from Phase 1)
---------------------------------
  35% Price Movement
  20% Volume Anomaly
  20% News/Sentiment   ← now uses real VADER scores; redistributed if unavailable
  15% Volatility Change
  10% Technical Signal ← now uses real RSI-14 + SMA-20 deviation

Unavailable sentiment handling
-------------------------------
When sentiment_unavailable=True, the 20% sentiment weight is redistributed
proportionally across the other four components:
  Price:      35/80 × 20% = +8.75%  → effective weight 43.75%
  Volume:     20/80 × 20% = +5.0%   → effective weight 25.0%
  Volatility: 15/80 × 20% = +3.75%  → effective weight 18.75%
  Technical:  10/80 × 20% = +2.5%   → effective weight 12.5%

Technical signal formulas
--------------------------
RSI-14:
  gains   = mean of positive daily % returns over 14 periods
  losses  = mean of absolute negative daily % returns over 14 periods
  RS      = gains / losses   (if losses = 0, RS = inf → RSI = 100)
  RSI     = 100 - (100 / (1 + RS))
  Scoring:  extremes (≥70 overbought, ≤30 oversold) score higher.
            Neutral zone (40–60) scores low.

SMA-20 deviation:
  sma20       = mean(last 20 closing prices)
  deviation%  = abs((current_price - sma20) / sma20 × 100)
  score_sma   = min(100, deviation% × 5)

Combined:
  technical_score = 0.6 × score_rsi + 0.4 × score_sma

Fallback (when history unavailable):
  old formula retained: abs(price_change_pct)/10 × min(volume/2, 1) × 100
"""
from typing import Any, Dict, List, Optional


CLASSIFICATION_THRESHOLDS = {
    "CRITICAL": 81,
    "IMPORTANT": 61,
    "WORTH_WATCHING": 31,
    "NORMAL": 0,
}

# Base weights (must sum to 1.0)
_W_PRICE     = 0.35
_W_VOLUME    = 0.20
_W_SENTIMENT = 0.20
_W_VOLATILITY = 0.15
_W_TECHNICAL  = 0.10


def classify_score(score: float) -> str:
    if score >= CLASSIFICATION_THRESHOLDS["CRITICAL"]:
        return "CRITICAL"
    elif score >= CLASSIFICATION_THRESHOLDS["IMPORTANT"]:
        return "IMPORTANT"
    elif score >= CLASSIFICATION_THRESHOLDS["WORTH_WATCHING"]:
        return "WORTH_WATCHING"
    else:
        return "NORMAL"


# ---------------------------------------------------------------------------
# Component scorers (0–100 each)
# ---------------------------------------------------------------------------

def _score_price(price_change_pct: float) -> float:
    """Normalise price movement to 0–100. Unchanged from Phase 1."""
    abs_change = abs(price_change_pct)
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
    """Normalise volume anomaly to 0–100. Unchanged from Phase 1."""
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
        return max(0, 5 * volume_multiplier)


def _score_sentiment(sentiment_score: float, sentiment_change: str) -> float:
    """
    Score based on sentiment magnitude and direction change.
    sentiment_score is the VADER compound value in [-1.0, 1.0].
    Unchanged from Phase 1.
    """
    base = abs(sentiment_score) * 80
    if "→" in sentiment_change:
        base += 20
    return min(100.0, base)


def _score_volatility(volatility_change_pct: float) -> float:
    """Score volatility change. Unchanged from Phase 1."""
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


# ---------------------------------------------------------------------------
# Technical signal: RSI-14 + SMA-20 deviation (Phase 2 replacement)
# ---------------------------------------------------------------------------

def _compute_rsi14(closes: List[float]) -> Optional[float]:
    """
    Compute RSI-14 from a list of closing prices (oldest first).

    Formula:
      gains = mean of positive daily returns over 14 periods
      losses = mean of absolute negative daily returns over 14 periods
      RS = gains / losses
      RSI = 100 - (100 / (1 + RS))

    Returns None if there are fewer than 15 prices (need 14 diffs).
    """
    if len(closes) < 15:
        return None

    # Use last 15 closes → 14 daily returns
    recent = closes[-15:]
    diffs = [recent[i + 1] - recent[i] for i in range(14)]

    gains = [d for d in diffs if d > 0]
    losses = [abs(d) for d in diffs if d < 0]

    avg_gain = (sum(gains) / 14) if gains else 0.0
    avg_loss = (sum(losses) / 14) if losses else 0.0

    if avg_loss == 0:
        return 100.0 if avg_gain > 0 else 50.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)


def _score_rsi(rsi: Optional[float]) -> float:
    """
    Map RSI value to 0–100 attention component.

    Logic: extremes (overbought ≥70 or oversold ≤30) indicate
    a meaningful technical event → score higher.
    Neutral zone (40–60) → low score.

    Mapping:
      RSI ≥ 80  → 100
      RSI 70–80 → 75–100  (linear)
      RSI 60–70 → 25–75   (linear)
      RSI 40–60 → 0–25    (linear, centre at 50 = 12.5)
      RSI 30–40 → 25–75   (mirror of 60–70)
      RSI 20–30 → 75–100  (mirror of 70–80)
      RSI ≤ 20  → 100
    """
    if rsi is None:
        return 0.0
    if rsi >= 80:
        return 100.0
    elif rsi >= 70:
        return 75 + (rsi - 70) * 2.5
    elif rsi >= 60:
        return 25 + (rsi - 60) * 5
    elif rsi >= 40:
        # neutral zone: map 50→12.5 (lowest), 40→25, 60→25
        return 25 - abs(rsi - 50) * 0.625
    elif rsi >= 30:
        return 25 + (40 - rsi) * 5
    elif rsi >= 20:
        return 75 + (30 - rsi) * 2.5
    else:
        return 100.0


def _compute_sma20(closes: List[float]) -> Optional[float]:
    """20-day simple moving average. Returns None if fewer than 20 prices."""
    if len(closes) < 20:
        return None
    return sum(closes[-20:]) / 20


def _score_sma_deviation(current_price: float, sma20: Optional[float]) -> float:
    """
    Score how far current_price deviates from SMA-20.
    deviation% = abs((current - sma) / sma × 100)
    score = min(100, deviation% × 5)
      → 5% away from SMA = score 25
      → 20% away from SMA = score 100
    """
    if sma20 is None or sma20 <= 0:
        return 0.0
    deviation_pct = abs((current_price - sma20) / sma20 * 100)
    return min(100.0, deviation_pct * 5)


def _score_technical_real(
    closes: List[float],
    current_price: float,
) -> float:
    """
    Real technical signal using RSI-14 + SMA-20.
    combined = 0.6 × score_rsi + 0.4 × score_sma
    """
    rsi = _compute_rsi14(closes)
    sma = _compute_sma20(closes)

    score_rsi = _score_rsi(rsi)
    score_sma = _score_sma_deviation(current_price, sma)

    return round(0.6 * score_rsi + 0.4 * score_sma, 2)


def _score_technical_fallback(price_change_pct: float, volume_multiplier: float) -> float:
    """
    Phase 1 fallback formula used when historical prices are unavailable.
    strength × volume_confirmation × 100.
    """
    strength = abs(price_change_pct) / 10
    vol_confirm = min(volume_multiplier / 2.0, 1.0)
    return min(100.0, strength * vol_confirm * 100)


def score_technical(
    price_change_pct: float,
    volume_multiplier: float,
    closes: Optional[List[float]] = None,
    current_price: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Public technical scoring function.
    Uses real RSI+SMA when history is available; fallback otherwise.

    Returns dict with score and metadata.
    """
    if closes and len(closes) >= 15 and current_price and current_price > 0:
        score = _score_technical_real(closes, current_price)
        method = "RSI14_SMA20"
        rsi = _compute_rsi14(closes)
        sma = _compute_sma20(closes)
    else:
        score = _score_technical_fallback(price_change_pct, volume_multiplier)
        method = "price_volume_fallback"
        rsi = None
        sma = None

    return {
        "score": score,
        "method": method,
        "rsi14": round(rsi, 2) if rsi is not None else None,
        "sma20": round(sma, 4) if sma is not None else None,
    }


# ---------------------------------------------------------------------------
# Main scoring service
# ---------------------------------------------------------------------------

class AttentionScoringService:
    def calculate(self, change_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate Attention Score from change signals.

        change_data keys consumed:
          price_change_pct       float    required
          volume_multiplier      float    required
          current_sentiment      float|None  None = unavailable
          sentiment_change       str
          sentiment_unavailable  bool     True = redistribute weight
          volatility_change_pct  float
          closes                 list[float]  optional, for real technical
          current_price          float        optional, for real technical

        Returns dict with:
          attention_score, classification, components, key_reasons,
          sentiment_used (bool), technical_method (str)
        """
        price_change_pct      = change_data.get("price_change_pct", 0.0)
        volume_multiplier     = change_data.get("volume_multiplier", 1.0)
        sentiment_score_raw   = change_data.get("current_sentiment")   # may be None
        sentiment_change      = change_data.get("sentiment_change", "Neutral")
        volatility_change_pct = change_data.get("volatility_change_pct", 0.0)
        sentiment_unavailable = change_data.get("sentiment_unavailable", False)
        closes                = change_data.get("closes")   # list[float] or None
        current_price         = change_data.get("current_price")

        # Treat explicit None the same as unavailable flag
        if sentiment_score_raw is None:
            sentiment_unavailable = True

        # ── Component scores (0–100 each) ───────────────────────────────
        price_component     = _score_price(price_change_pct)
        volume_component    = _score_volume(volume_multiplier)
        volatility_component = _score_volatility(volatility_change_pct)

        tech_result = score_technical(
            price_change_pct=price_change_pct,
            volume_multiplier=volume_multiplier,
            closes=closes,
            current_price=current_price,
        )
        technical_component = tech_result["score"]

        # ── Sentiment: use real score or redistribute weight ─────────────
        if sentiment_unavailable:
            # Redistribute the 20% sentiment weight across other 4 components
            # proportional to their base weights (35+20+15+10 = 80 total)
            # Each gets: (base_weight / 80) * 20 extra
            w_price_eff     = _W_PRICE     + (_W_PRICE     / 0.80) * _W_SENTIMENT
            w_volume_eff    = _W_VOLUME    + (_W_VOLUME    / 0.80) * _W_SENTIMENT
            w_volatility_eff = _W_VOLATILITY + (_W_VOLATILITY / 0.80) * _W_SENTIMENT
            w_technical_eff  = _W_TECHNICAL  + (_W_TECHNICAL  / 0.80) * _W_SENTIMENT
            w_sentiment_eff  = 0.0

            sentiment_component = 0.0
            sentiment_used = False
        else:
            sentiment_score_val = float(sentiment_score_raw)
            sentiment_component = _score_sentiment(sentiment_score_val, sentiment_change)
            w_price_eff      = _W_PRICE
            w_volume_eff     = _W_VOLUME
            w_volatility_eff = _W_VOLATILITY
            w_technical_eff  = _W_TECHNICAL
            w_sentiment_eff  = _W_SENTIMENT
            sentiment_used   = True

        # ── Weighted attention score ──────────────────────────────────────
        attention_score = (
            w_price_eff     * price_component
            + w_volume_eff    * volume_component
            + w_sentiment_eff * sentiment_component
            + w_volatility_eff * volatility_component
            + w_technical_eff * technical_component
        )
        attention_score = round(min(100.0, attention_score), 1)
        classification = classify_score(attention_score)

        # ── Effective weights for display ────────────────────────────────
        eff_weights = {
            "price":      round(w_price_eff, 4),
            "volume":     round(w_volume_eff, 4),
            "sentiment":  round(w_sentiment_eff, 4),
            "volatility": round(w_volatility_eff, 4),
            "technical":  round(w_technical_eff, 4),
        }

        # ── Key reasons ──────────────────────────────────────────────────
        key_reasons = self._generate_key_reasons(
            price_change_pct=price_change_pct,
            volume_multiplier=volume_multiplier,
            sentiment_score=sentiment_score_raw if not sentiment_unavailable else 0.0,
            sentiment_change=sentiment_change,
            volatility_change_pct=volatility_change_pct,
            sentiment_unavailable=sentiment_unavailable,
            rsi14=tech_result.get("rsi14"),
        )

        return {
            "attention_score": attention_score,
            "classification": classification,
            "components": {
                "price":      round(price_component, 1),
                "volume":     round(volume_component, 1),
                "sentiment":  round(sentiment_component, 1),
                "volatility": round(volatility_component, 1),
                "technical":  round(technical_component, 1),
            },
            "effective_weights": eff_weights,
            "key_reasons": key_reasons,
            # Metadata for the response
            "sentiment_used": sentiment_used,
            "technical_method": tech_result["method"],
            "rsi14": tech_result.get("rsi14"),
            "sma20": tech_result.get("sma20"),
        }

    def _generate_key_reasons(
        self,
        price_change_pct: float,
        volume_multiplier: float,
        sentiment_score: float,
        sentiment_change: str,
        volatility_change_pct: float,
        sentiment_unavailable: bool = False,
        rsi14: Optional[float] = None,
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

        if sentiment_unavailable:
            reasons.append("News sentiment unavailable — sentiment weight redistributed")
        elif "→" in sentiment_change:
            reasons.append(f"Sentiment shifted: {sentiment_change}")
        elif abs(sentiment_score) > 0.4:
            direction = "Positive" if sentiment_score > 0 else "Negative"
            reasons.append(f"{direction} market sentiment (VADER lexicon score)")

        if abs(volatility_change_pct) >= 30:
            direction = "increased" if volatility_change_pct > 0 else "decreased"
            reasons.append(f"Volatility {direction} {abs(volatility_change_pct):.0f}%")

        if rsi14 is not None:
            if rsi14 >= 70:
                reasons.append(f"RSI-14 at {rsi14:.0f} — overbought territory")
            elif rsi14 <= 30:
                reasons.append(f"RSI-14 at {rsi14:.0f} — oversold territory")

        if not reasons:
            reasons.append("No significant changes detected")

        return reasons[:4]
