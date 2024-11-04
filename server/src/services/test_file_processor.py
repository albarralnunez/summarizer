import pytest
from src.services.file_processor import process_input
from fastapi import HTTPException, UploadFile
import io


class TestFileProcessor:
    @pytest.mark.asyncio
    async def test_process_input_text(self, sample_text):
        sentences = []
        async for sentence in process_input(file=None, text=sample_text):
            sentences.append(sentence)

        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)

    @pytest.mark.asyncio
    async def test_process_input_file(self, sample_file):
        sentences = []
        async for sentence in process_input(file=sample_file, text=None):
            sentences.append(sentence)

        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)

    @pytest.mark.asyncio
    async def test_invalid_file_type(self):
        invalid_file = UploadFile(filename="test.pdf", file=io.BytesIO(b"test content"))

        with pytest.raises(HTTPException):
            async for _ in process_input(file=invalid_file, text=None):
                pass

    @pytest.mark.asyncio
    async def test_invalid_input(self):
        with pytest.raises(HTTPException):
            async for _ in process_input(file=None, text=None):
                pass
