from unittest.mock import patch, MagicMock
from processing.sentiment import score_text_vader, score_text_finbert, score_batch

def test_score_text_vader_positive():
    result = score_text_vader("This stock is surging and doing incredibly well.")
    assert result["label"] == "positive"
    assert result["compound"] > 0
    assert "positive" in result

def test_score_text_vader_negative():
    result = score_text_vader("This company is failing, horrible, and facing bankruptcy.")
    assert result["label"] == "negative"
    assert result["compound"] < 0
    assert "negative" in result

def test_score_text_vader_neutral():
    result = score_text_vader("Apple is a tech company based in Cupertino.")
    assert result["label"] == "neutral"
    assert -0.05 < result["compound"] < 0.05

@patch("processing.sentiment.get_finbert_pipeline")
def test_score_text_finbert(mock_get_pipeline):
    # Setup a mock pipeline returning positive
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [{"label": "positive", "score": 0.9}]
    mock_get_pipeline.return_value = mock_pipeline
    
    result = score_text_finbert("Mocked text")
    assert result["label"] == "positive"
    assert result["compound"] == 0.9
    assert result["positive"] == 0.9
    assert result["negative"] == 0.0

@patch("processing.sentiment.get_finbert_pipeline")
def test_score_text_finbert_fallback(mock_get_pipeline):
    # Setup mock to simulate fallback to VADER
    mock_get_pipeline.return_value = "fallback"
    
    result = score_text_finbert("This stock is surging and doing incredibly well.")
    assert result["label"] == "positive"
    assert result["compound"] > 0

def test_score_batch():
    articles = [
        {"title": "Positive headline", "description": "Good news about AAPL", "source": "Reuters"},
        {"title": "Negative headline", "description": "Bad news", "source": {"name": "Twitter"}}
    ]
    results = score_batch(articles)
    assert len(results) == 2
    assert "sentiment" in results[0]
    assert "sentiment" in results[1]
    assert results[0]["source"] == "Reuters"
    assert results[1]["source"] == "Twitter"
