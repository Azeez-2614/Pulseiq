from __future__ import annotations
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from datetime import datetime
import sys
import os

# Add parent directory to path so config can be imported when running directly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

analyzer = SentimentIntensityAnalyzer()
_finbert_pipeline = None


def get_finbert_pipeline():
    """
    Lazily loads the FinBERT pipeline to avoid startup delays when not in use.

    Returns:
        The transformers classification pipeline, or "fallback" string on loading errors.
    """
    global _finbert_pipeline
    if _finbert_pipeline is None:
        try:
            from transformers import pipeline

            print(
                "Loading ProsusAI/finbert transformer model (this may take a minute on first run)..."
            )
            _finbert_pipeline = pipeline(
                "text-classification", model="ProsusAI/finbert"
            )
        except Exception as e:
            print(f"Error loading FinBERT model: {e}. Falling back to VADER.")
            _finbert_pipeline = "fallback"
    return _finbert_pipeline


def score_text_vader(text: str) -> dict[str, float | str]:
    """
    Scores a text string using the VADER sentiment analyzer.

    Args:
        text: Raw text to analyze (headline, article body, description).

    Returns:
        dict with keys: compound (-1.0 to 1.0), positive, negative, neutral, and label.
    """
    scores = analyzer.polarity_scores(text)
    compound = scores["compound"]
    label = (
        "positive"
        if compound >= config.SENTIMENT_POSITIVE_THRESHOLD
        else "negative"
        if compound <= config.SENTIMENT_NEGATIVE_THRESHOLD
        else "neutral"
    )
    return {
        "compound": round(compound, 4),
        "positive": round(scores["pos"], 4),
        "negative": round(scores["neg"], 4),
        "neutral": round(scores["neu"], 4),
        "label": label,
    }


def score_text_finbert(text: str) -> dict[str, float | str]:
    """
    Scores a text string using the ProsusAI/finbert transformer model.
    Falls back to VADER if FinBERT model fails to load or inference fails.

    Args:
        text: Raw text to analyze.

    Returns:
        dict with keys: compound, positive, negative, neutral, and label.
    """
    pipeline_instance = get_finbert_pipeline()
    if pipeline_instance == "fallback":
        return score_text_vader(text)

    try:
        # FinBERT has a max token length of 512, slice text to keep it safe
        result = pipeline_instance(text[:512])[0]
        label = result["label"].lower()  # positive, negative, neutral
        score = result["score"]  # confidence score

        # Map label and score to compound format
        label_map = {"positive": 1.0, "negative": -1.0, "neutral": 0.0}
        compound = label_map.get(label, 0.0) * score

        return {
            "compound": round(compound, 4),
            "positive": round(score if label == "positive" else 0.0, 4),
            "negative": round(score if label == "negative" else 0.0, 4),
            "neutral": round(score if label == "neutral" else 0.0, 4),
            "label": label,
        }
    except Exception as e:
        print(f"Error running FinBERT inference: {e}. Falling back to VADER.")
        return score_text_vader(text)


def score_text(text: str) -> dict[str, float | str]:
    """
    Scores text using the active model configured in config.py (FinBERT or VADER).

    Args:
        text: Raw text to analyze.

    Returns:
        dict with keys: compound, positive, negative, neutral, and label.
    """
    if config.USE_FINBERT:
        return score_text_finbert(text)
    else:
        return score_text_vader(text)


def score_article(article: dict) -> dict:
    """
    Calculates sentiment scores on an article description/title and attaches results.

    Args:
        article: Dictionary containing article details (title, description, source).

    Returns:
        Updated dictionary with a 'sentiment' sub-dictionary and 'scored_at' timestamp.
    """
    # Combine title and description for richer context
    text = f"{article.get('title', '')} {article.get('description', '')}"
    sentiment = score_text(text)

    # Standardize output to include source
    source = article.get("source", "unknown")
    if isinstance(source, dict):
        source = source.get("name", "unknown")

    return {
        **article,
        "source": source,
        "sentiment": sentiment,
        "scored_at": datetime.utcnow().isoformat(),
    }


def score_batch(articles: list[dict]) -> list[dict]:
    """
    Scores a list of articles in batch.

    Args:
        articles: A list of raw article dictionaries.

    Returns:
        A list of updated article dictionaries with scored sentiment metrics.
    """
    return [score_article(a) for a in articles]


if __name__ == "__main__":
    test_text = "Apple reports blow-out earnings that smash Wall Street predictions, stock surges in pre-market trading."
    print("Test scoring using VADER:")
    print(score_text_vader(test_text))

    # Try testing FinBERT if configured
    if config.USE_FINBERT:
        print("\nTest scoring using FinBERT:")
        print(score_text_finbert(test_text))
