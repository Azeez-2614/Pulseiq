from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from api.main import app

client = TestClient(app)
API_HEADERS = {"X-API-Key": "pulseiq-dev-key-change-in-production"}

def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

@patch("api.main.get_all_scores")
def test_scores_endpoint(mock_get_all):
    mock_get_all.return_value = {
        "AAPL": {"symbol": "AAPL", "sentiment_score": 0.25, "price": 180.0}
    }
    response = client.get("/scores", headers=API_HEADERS)
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
    response = client.get("/scores/tsla", headers=API_HEADERS)
    assert response.status_code == 200
    assert response.json()["symbol"] == "TSLA"
    assert response.json()["sentiment_score"] == -0.15

@patch("api.main.get_recent_articles")
def test_articles_endpoint(mock_get_recent):
    mock_get_recent.return_value = [
        {
            "title": "Test Headline",
            "source": "Test Source",
            "published_at": None,
            "symbol": "AAPL",
            "sentiment": {"compound": 0.3}
        }
    ]
    response = client.get("/articles", headers=API_HEADERS)
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["title"] == "Test Headline"
    assert response.json()[0]["sentiment"]["compound"] == 0.3

@patch("api.main.run_pipeline")
def test_pipeline_trigger_endpoint(mock_run_pipeline):
    mock_task = MagicMock()
    mock_task.id = "test-task-id"
    mock_run_pipeline.delay.return_value = mock_task

    response = client.post("/pipeline/trigger", headers=API_HEADERS)
    assert response.status_code == 200
    assert response.json()["status"] == "pipeline triggered"
    assert response.json()["task_id"] == "test-task-id"
    mock_run_pipeline.delay.assert_called_once()
