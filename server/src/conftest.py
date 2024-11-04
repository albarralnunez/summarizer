import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from dask.distributed import Client
from src.config.dask_config import DaskSettings
import io
from src.services.constants import MAX_SENTENCE_LENGTH


def pytest_configure(config):
    """Configure pytest for parallel execution"""
    config.addinivalue_line("markers", "parallel: mark test as able to run in parallel")


@pytest.fixture(scope="function")
def test_client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_dask_client():
    """Create a mock Dask client for testing"""
    mock_client = Mock(spec=Client)

    # Make close() return a coroutine that resolves to None
    async def mock_close():
        return None

    mock_client.close = mock_close
    mock_client.scheduler_info.return_value = {
        "workers": {"worker1": {}, "worker2": {}}
    }
    return mock_client


@pytest.fixture
def mock_dask_settings():
    """Create mock Dask settings for testing"""
    return DaskSettings(
        scheduler_host="localhost",
        scheduler_port=8786,
        dashboard_port=8787,
        n_workers=2,
    )


@pytest.fixture
def sample_text():
    """Provide sample text for testing"""
    return (
        "This is the first test sentence. "
        "This is the second test sentence. "
        "This is the third test sentence. "
        "This is the fourth test sentence."
    )


@pytest.fixture
def sample_file(sample_text):
    """Create a sample file-like object for testing"""
    return io.BytesIO(sample_text.encode())


@pytest.fixture(autouse=True)
def mock_get_dask_client(monkeypatch, mock_dask_client):
    """Automatically patch get_dask_client for all tests"""

    async def mock_get_client():
        return mock_dask_client

    monkeypatch.setattr("src.api.routes.get_dask_client", mock_get_client)


@pytest.fixture(autouse=True)
def mock_cleanup_dask_client(monkeypatch):
    """Automatically patch cleanup_dask_client for all tests"""

    async def mock_cleanup(client):
        """Mock cleanup function that safely handles client cleanup"""
        if client is not None and hasattr(client, "close"):
            try:
                await client.close()
            except Exception:
                pass

    monkeypatch.setattr("src.api.routes.cleanup_dask_client", mock_cleanup)


@pytest.fixture(autouse=True)
def mock_get_dask_settings(monkeypatch, mock_dask_settings):
    """Automatically patch get_dask_settings for all tests"""

    def mock_settings():
        return mock_dask_settings

    monkeypatch.setattr("src.api.routes.get_dask_settings", mock_settings)


@pytest.fixture(autouse=True)
def mock_summarize_text(monkeypatch):
    """Mock the summarize_text function"""

    async def mock_summarize(*args, **kwargs):
        return {
            "summary": ["Mocked summary text"],
            "method": "default",
            "processor": "default",
            "backend_processing_time": 0.1,
        }

    monkeypatch.setattr("src.services.summarizer.summarize_text", mock_summarize)


@pytest.fixture(autouse=True)
def mock_summarize_text_dask(monkeypatch):
    """Mock the summarize_text_dask function"""

    async def mock_summarize(*args, **kwargs):
        return {
            "summary": ["Mocked dask summary text"],
            "method": "dask",
            "processor": "dask",
            "backend_processing_time": 0.1,
        }

    monkeypatch.setattr(
        "src.services.dask_summarizer.summarize_text_dask", mock_summarize
    )


@pytest.fixture(autouse=True)
def mock_process_input(monkeypatch):
    """Mock the process_input function"""

    async def mock_process(*args, **kwargs):
        for sentence in ["This is a test sentence.", "This is another test sentence."]:
            yield sentence

    monkeypatch.setattr("src.services.file_processor.process_input", mock_process)


@pytest.fixture(autouse=True)
def mock_process_with_dask(monkeypatch):
    """Mock the process_with_dask function"""

    async def mock_process(*args, **kwargs):
        sentences = [
            "This is a dask test sentence.",
            "This is another dask test sentence.",
            "This is a third dask test sentence.",
        ]
        for sentence in sentences:
            yield sentence

    monkeypatch.setattr(
        "src.services.dask_processor.process_with_dask", mock_process
    )


@pytest.fixture
def sample_file():
    """Create a sample file-like object for testing"""
    content = (
        "This is a sufficiently long sentence with many words that meets the minimum requirements for length. "
        "Here is another sentence that adds more content to ensure we pass the length check. "
        "And a third sentence to make absolutely sure we have enough content for processing. "
        "The quick brown fox jumps over the lazy dog multiple times to add more meaningful content."
    ).encode("utf-8")
    file = io.BytesIO(content)
    file.seek(0)
    return file


@pytest.fixture
def valid_text():
    """Provide valid text for testing"""
    return (
        "This is a sufficiently long sentence with many words that meets the minimum requirements for length. "
        "Here is another sentence that adds more content to ensure we pass the length check. "
        "And a third sentence to make absolutely sure we have enough content for processing. "
        "The quick brown fox jumps over the lazy dog multiple times to add more meaningful content. "
        "Finally, we add some more text to ensure we are well above the minimum length threshold."
    )


@pytest.fixture
def valid_test_data(valid_text):
    """Provide valid test data for default summarization"""
    return {
        "text": valid_text,
        "num_sentences": 1,
        "algorithm": "default",
        "processor": "default",
        "early_termination_factor": 2.0,
    }


@pytest.fixture
def valid_dask_test_data(valid_text):
    """Provide valid test data for Dask summarization"""
    return {
        "text": valid_text,
        "num_sentences": 1,
        "algorithm": "dask",
        "processor": "dask",
        "early_termination_factor": 2.0,
    }


@pytest.fixture
def invalid_test_data():
    """Provide various invalid test data scenarios"""
    return {
        "too_short": {
            "text": "Short.",
            "num_sentences": 1,
            "algorithm": "default",
            "processor": "default",
            "early_termination_factor": 2.0,
        },
        "too_few_words": {
            "text": "This is not enough words.",
            "num_sentences": 1,
            "algorithm": "default",
            "processor": "default",
            "early_termination_factor": 2.0,
        },
        "invalid_num_sentences": {
            "text": "This is a test sentence.",
            "num_sentences": 0,
            "algorithm": "default",
            "processor": "default",
            "early_termination_factor": 2.0,
        },
        "invalid_algorithm": {
            "text": "This is a test sentence.",
            "num_sentences": 1,
            "algorithm": "invalid_algorithm",
            "processor": "default",
            "early_termination_factor": 2.0,
        },
    }


@pytest.fixture
def too_long_text():
    """Provide text that exceeds maximum length"""
    base_sentence = (
        "This is a properly formatted sentence with good structure and meaning. "
    )
    return base_sentence * (MAX_SENTENCE_LENGTH // len(base_sentence) + 1)
