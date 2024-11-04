import pytest
from unittest.mock import Mock, AsyncMock
from fastapi.testclient import TestClient
from src.main import app
from dask.distributed import Client
from src.config.dask_config import DaskSettings
import io
from src.services.constants import MAX_SENTENCE_LENGTH
from src.utils.text_processing import word_tokenize
import asyncio
from fastapi import UploadFile


def pytest_configure(config):
    """Configure pytest for parallel execution"""
    config.addinivalue_line("markers", "parallel: mark test as able to run in parallel")


@pytest.fixture
def test_client():
    """Create a test client for the FastAPI app"""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def mock_dask_client():
    """Create a mock Dask client for testing"""
    mock_client = Mock(spec=Client)

    # Mock the map method to return a list of futures
    def mock_map(func, *iterables, **kwargs):
        results = []
        for args in zip(*iterables):
            result = func(*args)
            mock_future = Mock()
            mock_future.result = lambda: result
            results.append(mock_future)
        return results

    # Mock the gather method to return actual results
    def mock_gather(futures):
        return [future.result() for future in futures]

    # Set up the mock methods
    mock_client.map = mock_map
    mock_client.gather = mock_gather

    # Mock the close method
    async def mock_close():
        return None

    mock_client.close = mock_close

    # Mock scheduler info
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
    return """
    This is a test sentence about artificial intelligence.
    Machine learning and natural language processing are important.
    Deep learning and neural networks are fascinating.
    Data science and statistics help us understand patterns.
    Computer vision enables machines to see and interpret images.
    """


@pytest.fixture
def sample_file(sample_text):
    """Create a sample file-like object for testing"""
    content = sample_text.encode("utf-8")
    file = UploadFile(filename="test.txt", file=io.BytesIO(content))
    yield file
    file.file.close()


@pytest.fixture
async def sentence_generator(sample_text):
    """Returns an async generator of sentences"""
    for sentence in sample_text.split("\n"):
        if sentence.strip():
            yield sentence.strip()


@pytest.fixture
def word_to_index(sample_text):
    """Returns a sample word-to-index mapping"""
    words = word_tokenize(sample_text.lower())
    unique_words = sorted(set(words))  # Sort for deterministic indexing
    return {word: idx for idx, word in enumerate(unique_words)}


@pytest.fixture(autouse=True)
async def setup_teardown():
    """Setup and teardown for each test"""
    yield
    await asyncio.sleep(0)  # Allow any pending tasks to complete


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
