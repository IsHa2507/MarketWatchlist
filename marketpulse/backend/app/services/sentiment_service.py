"""
SentimentService
================
Computes a sentiment score from news headlines.

IMPORTANT LABELLING NOTE
-------------------------
VADER (Valence Aware Dictionary and sEntiment Reasoner) is a
LEXICON-BASED and RULE-BASED method — NOT a machine-learning model.
It uses a manually-curated word list with intensity modifiers and
grammatical rules (negation, punctuation, capitalization, etc.).

It is NOT FinBERT, NOT a neural network, and NOT trained on financial data.
It works well enough for short news headlines as a Phase 2 baseline.

Upgrade path
------------
To replace VADER with FinBERT or another financial NLP model in Phase 3,
implement a new class that satisfies the _BaseSentimentModel interface and
register it in _get_model(). Nothing else in the system needs to change.

Score range
-----------
All scores are normalised to [-1.0, 1.0]:
  -1.0 = maximally negative
   0.0 = neutral
  +1.0 = maximally positive

Sample output
-------------
{
    "score": -0.42,
    "label": "Negative",
    "confidence": 0.71,
    "article_count": 5,
    "source": "VADER",              # always labelled as lexicon/rule-based
    "method": "lexicon_rule_based", # explicit method type
    "unavailable": False,
    "timestamp": "2024-04-17T10:30:00",
}
"""
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.news_service import NewsService

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sentiment result dataclass (plain dict — no pydantic dependency here)
# ---------------------------------------------------------------------------

def _unavailable_result() -> Dict[str, Any]:
    """Return a canonical 'no data' result. Never silently use 0.0 as neutral."""
    return {
        "score": None,           # None = genuinely unknown; NOT the same as 0.0
        "label": "Unavailable",
        "confidence": 0.0,
        "article_count": 0,
        "source": "Unavailable",
        "method": "none",
        "unavailable": True,
        "timestamp": datetime.utcnow().isoformat(),
    }


def _make_result(
    score: float,
    article_count: int,
    source: str,
    method: str,
    confidence: float,
) -> Dict[str, Any]:
    label = "Neutral"
    if score > 0.15:
        label = "Positive"
    elif score < -0.15:
        label = "Negative"

    return {
        "score": round(score, 4),
        "label": label,
        "confidence": round(confidence, 4),
        "article_count": article_count,
        "source": source,
        "method": method,
        "unavailable": False,
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Abstract model interface (upgrade path for Phase 3)
# ---------------------------------------------------------------------------

class _BaseSentimentModel(ABC):
    """
    Interface every sentiment model must satisfy.
    Implementing a new class here is the ONLY change needed to upgrade
    from VADER to FinBERT or another model.
    """

    @abstractmethod
    def score_headlines(self, headlines: List[str]) -> float:
        """Return a single score in [-1.0, 1.0] for a list of headlines."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Model identifier, e.g. 'VADER', 'FinBERT'."""

    @property
    @abstractmethod
    def method_type(self) -> str:
        """Method type: 'lexicon_rule_based', 'transformer', etc."""

    @property
    @abstractmethod
    def is_available(self) -> bool:
        """True if the model can currently run (library installed, etc.)."""


# ---------------------------------------------------------------------------
# VADER model wrapper
# ---------------------------------------------------------------------------

class _VADERModel(_BaseSentimentModel):
    """
    VADER lexicon/rule-based sentiment analyser.

    VADER is NOT a machine-learning model.
    It uses a curated word dictionary + linguistic rules.
    Designed for short social/financial text; no training data or GPU needed.

    compound score range: -1.0 (most negative) to +1.0 (most positive)
    We use the raw compound score, which is already in [-1, 1].
    """

    def __init__(self):
        self._analyzer = None  # lazy init

    def _get_analyzer(self):
        if self._analyzer is None:
            try:
                from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
                self._analyzer = SentimentIntensityAnalyzer()
            except ImportError:
                return None
        return self._analyzer

    @property
    def name(self) -> str:
        return "VADER"

    @property
    def method_type(self) -> str:
        return "lexicon_rule_based"

    @property
    def is_available(self) -> bool:
        return self._get_analyzer() is not None

    def score_headlines(self, headlines: List[str]) -> float:
        """
        Score multiple headlines and return the average compound score.

        Compound score is already in [-1.0, 1.0].
        We weight longer/more informative headlines equally (simple average).
        """
        analyzer = self._get_analyzer()
        if not analyzer or not headlines:
            return 0.0

        scores = []
        for headline in headlines:
            if not headline or not headline.strip():
                continue
            try:
                vs = analyzer.polarity_scores(headline)
                scores.append(vs["compound"])
            except Exception:
                continue

        if not scores:
            return 0.0

        return sum(scores) / len(scores)


# ---------------------------------------------------------------------------
# Keyword fallback model (zero dependencies)
# ---------------------------------------------------------------------------

_POSITIVE_KEYWORDS = {
    "surge", "surges", "surged", "jump", "jumps", "jumped",
    "rally", "rallies", "rallied", "rise", "rises", "rose",
    "gain", "gains", "gained", "profit", "profits",
    "record", "beat", "beats", "strong", "strength",
    "growth", "grows", "grew", "upgrade", "upgraded",
    "buy", "outperform", "overweight", "bullish",
    "positive", "good", "great", "excellent", "milestone",
    "expand", "expands", "expansion", "win", "wins", "won",
    "boost", "boosts", "boosted", "exceed", "exceeds", "exceeded",
}

_NEGATIVE_KEYWORDS = {
    "fall", "falls", "fell", "drop", "drops", "dropped",
    "decline", "declines", "declined", "loss", "losses",
    "miss", "misses", "missed", "weak", "weakness",
    "cut", "cuts", "downgrade", "downgraded",
    "sell", "underperform", "underweight", "bearish",
    "negative", "bad", "poor", "concern", "concerns",
    "risk", "risks", "warning", "warns", "warned",
    "slow", "slows", "slowdown", "shrink", "shrinks",
    "probe", "lawsuit", "fraud", "scandal", "crash",
}


class _KeywordModel(_BaseSentimentModel):
    """
    Deterministic keyword-based fallback.
    Used when vaderSentiment is not installed.
    No external dependencies; always available.
    """

    @property
    def name(self) -> str:
        return "Keyword"

    @property
    def method_type(self) -> str:
        return "keyword_baseline"

    @property
    def is_available(self) -> bool:
        return True

    def score_headlines(self, headlines: List[str]) -> float:
        if not headlines:
            return 0.0

        total_score = 0.0
        for headline in headlines:
            words = set(w.lower().strip(".,!?;:") for w in headline.split())
            pos = len(words & _POSITIVE_KEYWORDS)
            neg = len(words & _NEGATIVE_KEYWORDS)
            total = pos + neg
            if total > 0:
                total_score += (pos - neg) / total
            # Headlines with no matched words contribute 0

        return total_score / len(headlines)


# ---------------------------------------------------------------------------
# Model registry (upgrade path)
# ---------------------------------------------------------------------------

def _get_model(model_name: str) -> _BaseSentimentModel:
    """
    Return the best available model.
    To add Phase 3 FinBERT: add it here.
    """
    name = model_name.lower()
    if name == "vader":
        m = _VADERModel()
        if m.is_available:
            return m
        logger.warning("VADER requested but vaderSentiment not installed; using keyword fallback")
        return _KeywordModel()
    if name == "keyword":
        return _KeywordModel()
    # Unknown model name → best available
    vader = _VADERModel()
    if vader.is_available:
        return vader
    return _KeywordModel()


# ---------------------------------------------------------------------------
# Confidence calculation
# ---------------------------------------------------------------------------

def _compute_confidence(article_count: int, avg_abs_score: float) -> float:
    """
    Estimate confidence as a product of:
    - Coverage: how many articles we had (saturates at 10)
    - Signal strength: average absolute compound score (0–1)
    """
    coverage = min(article_count / 10.0, 1.0)
    return round(coverage * avg_abs_score, 4)


# ---------------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------------

class SentimentService:
    """
    Compute sentiment for a ticker from its news headlines.

    Modular design
    --------------
    The model is selected by SENTIMENT_MODEL env var (default: "vader").
    To upgrade to FinBERT or another model in Phase 3, implement
    _BaseSentimentModel and add it to _get_model().

    Unavailable handling
    --------------------
    If no headlines are available, returns _unavailable_result() with
    score=None and unavailable=True. The AttentionScoringService
    handles this by redistributing the 20% sentiment weight.
    """

    def __init__(self, db: Session):
        self.db = db
        self._news_svc = NewsService(db)
        model_name = getattr(settings, "SENTIMENT_MODEL", "vader")
        self._model = _get_model(model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_sentiment(self, ticker: str) -> Dict[str, Any]:
        """
        Return sentiment result for ticker.
        Always returns a dict — never raises.

        If news is unavailable: returns unavailable_result with score=None.
        If headlines exist: returns real VADER/keyword score in [-1, 1].
        """
        try:
            return self._compute_sentiment(ticker)
        except Exception as exc:
            logger.error("SentimentService.get_sentiment failed for '%s': %s", ticker, exc)
            return _unavailable_result()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _compute_sentiment(self, ticker: str) -> Dict[str, Any]:
        headlines = self._news_svc.get_headlines(ticker)

        if not headlines:
            return _unavailable_result()

        # Extract just the title strings for scoring
        titles = [h.get("title", "") for h in headlines if h.get("title")]
        if not titles:
            return _unavailable_result()

        # Score with the selected model
        score = self._model.score_headlines(titles)

        # Confidence
        avg_abs = sum(abs(self._model.score_headlines([t])) for t in titles) / len(titles)
        confidence = _compute_confidence(len(titles), avg_abs)

        result = _make_result(
            score=score,
            article_count=len(titles),
            source=self._model.name,
            method=self._model.method_type,
            confidence=confidence,
        )

        # Update the cache row with computed scores
        self._news_svc.update_cache_sentiment(
            ticker=ticker,
            score=score,
            label=result["label"],
            confidence=confidence,
            source=self._model.name,
        )

        return result
