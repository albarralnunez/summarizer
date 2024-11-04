from fastapi.testclient import TestClient
from src.main import app
import pytest
import io
from src.services.constants import (
    MIN_SENTENCE_LENGTH,
    MIN_WORDS_COUNT,
    MAX_SENTENCE_LENGTH,
)

client = TestClient(app)


@pytest.mark.parallel
def test_root_endpoint(test_client):
    """Test the root endpoint returns welcome message"""
    response = test_client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "Welcome to the File Summarizer API"}


@pytest.mark.parallel
def test_health_check(test_client):
    """Test the health check endpoint"""
    response = test_client.get("/health")
    assert response.status_code == 200
    assert "status" in response.json()
    assert "api" in response.json()
    assert "dask" in response.json()


@pytest.mark.parallel
def test_summarize_with_text(test_client, valid_test_data):
    """Test summarization endpoint with text input"""
    response = test_client.post("/summarize", data=valid_test_data)
    print(response.json())
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert isinstance(data["summary"], list)
    assert len(data["summary"]) > 0
    assert all(isinstance(s, str) for s in data["summary"])
    assert "method" in data
    assert "processor" in data
    assert "backend_processing_time" in data


@pytest.mark.parallel
def test_summarize_with_file(test_client, sample_file):
    """Test summarization endpoint with file upload"""
    response = test_client.post(
        "/summarize",
        files={"file": ("test.txt", sample_file, "text/plain")},
        data={
            "num_sentences": "1",
            "algorithm": "default",
            "processor": "default",
            "early_termination_factor": "2.0",
        },
    )

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert isinstance(data["summary"], list)
    assert len(data["summary"]) > 0
    assert all(isinstance(s, str) for s in data["summary"])
    assert "method" in data
    assert "processor" in data
    assert "backend_processing_time" in data


@pytest.mark.parallel
def test_summarize_invalid_input(test_client):
    """Test summarization endpoint with no input"""
    response = test_client.post(
        "/summarize",
        data={
            "num_sentences": 1,
            "algorithm": "default",
            "processor": "default",
            "early_termination_factor": 2.0,
        },
    )

    assert response.status_code == 400
    assert "detail" in response.json()


@pytest.mark.parallel
def test_summarize_with_dask(test_client, valid_dask_test_data):
    """Test summarization endpoint with Dask algorithm"""
    response = test_client.post("/summarize", data=valid_dask_test_data, timeout=30.0)

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")
    print(f"Response headers: {response.headers}")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert isinstance(data["summary"], list)
    assert len(data["summary"]) > 0
    assert data["method"] == "dask"
    assert data["processor"] == "dask"
    assert "backend_processing_time" in data


@pytest.mark.parallel
def test_health_check_with_dask_error(test_client, monkeypatch):
    """Test health check when Dask is unavailable"""

    async def mock_client_error():
        raise Exception("Dask connection error")

    monkeypatch.setattr("dask.distributed.Client", mock_client_error)

    response = test_client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["dask"]["status"] == "unhealthy"


@pytest.mark.parallel
def test_summarize_text_too_short(test_client, invalid_test_data):
    """Test summarization endpoint with text that's too short"""
    response = test_client.post("/summarize", data=invalid_test_data["too_short"])

    assert response.status_code == 400
    assert "detail" in response.json()
    error_message = response.json()["detail"].lower()
    assert "file is empty or contains no valid sentences" in error_message


@pytest.mark.parallel
def test_summarize_text_too_few_words(test_client, invalid_test_data):
    """Test summarization endpoint with text that has too few words"""
    response = test_client.post("/summarize", data=invalid_test_data["too_few_words"])

    assert response.status_code == 400
    assert "detail" in response.json()
    error_message = response.json()["detail"].lower()
    assert "file is empty or contains no valid sentences" in error_message


@pytest.mark.parallel
def test_summarize_text_too_long(test_client, too_long_text, valid_test_data):
    """Test summarization endpoint with text that exceeds maximum length"""
    test_data = {**valid_test_data, "text": too_long_text}

    response = test_client.post("/summarize", data=test_data)

    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.json()}")

    assert response.status_code == 400
    assert "detail" in response.json()
    error_message = response.json()["detail"].lower()
    assert any(msg in error_message for msg in ["maximum length", "no valid sentences"])


@pytest.mark.parallel
def test_summarize_invalid_num_sentences(test_client, invalid_test_data):
    """Test summarization endpoint with invalid number of sentences"""
    response = test_client.post(
        "/summarize", data=invalid_test_data["invalid_num_sentences"]
    )

    assert response.status_code == 422  # Validation error


@pytest.mark.parallel
def test_summarize_invalid_algorithm(test_client, invalid_test_data):
    """Test summarization endpoint with invalid algorithm"""
    response = test_client.post(
        "/summarize", data=invalid_test_data["invalid_algorithm"]
    )

    assert response.status_code == 422  # Validation error
