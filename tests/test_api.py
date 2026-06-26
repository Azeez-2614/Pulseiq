from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch("api.main.get_all_scores")
def test_scores_endpoint(mock_get_all):
    mock_get_all.return_value = {
        "AAPL": {"symbol": "AAPL", "sentiment_score": 0.25, "price": 180.0}
    }
    response = client.get("/scores")
    assert response.status_code == 200
    assert "AAPL" in response.json()
    assert response.json()["AAPL"]["sentiment_score"] == 0.25

@patch("api.main.get_cached_score")
def test_symbol_scores_endpoint(mock_get_cached):
    mock_get_cached.return_value = {
        "symbol": "TSLA",
        "sentiment_score": -0.15,
        "price": 250.0
    }
    response = client.get("/scores/tsla")
    assert response.status_code == 200
    assert response.json()["symbol"] == "TSLA"
    assert response.json()["sentiment_score"] == -0.15

@patch("api.main.get_session")
def test_articles_endpoint(mock_get_session):
    # Setup mock PostgreSQL session and query
    mock_session = MagicMock()
    mock_query = MagicMock()
    
    mock_session.query.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.limit.return_value = mock_query
    
    # Mock some DB scores
    mock_score = MagicMock()
    mock_score.headline = "Test Headline"
    mock_score.source = "Test Source"
    mock_score.published_at = None
    mock_score.symbol = "AAPL"
    mock_score.raw_scores = {"compound": 0.3}
    
    mock_query.all.return_value = [mock_score]
    mock_get_session.return_value = mock_session
    
    response = client.get("/articles")
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test Headline"
    assert response.json()[0]["sentiment"]["compound"] == 0.3

@patch("api.main.pipeline_job")
def test_pipeline_trigger_endpoint(mock_pipeline_job):
    response = client.post("/pipeline/trigger")
    assert response.status_code == 200
    assert response.json()["status"] == "pipeline triggered"
    # Ensure BackgroundTasks executed it
    mock_pipeline_job.assert_called_once()
