import pytest
from src.services.dask_processor import process_with_dask, decode_chunk
from fastapi import HTTPException


class TestDaskProcessor:
    @pytest.mark.asyncio
    async def test_process_with_dask_text(self, sample_text):
        sentences = []
        async for sentence in process_with_dask(
            file=None, text=sample_text, chunk_size=1024, batch_size=2
        ):
            sentences.append(sentence)

        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)

    @pytest.mark.asyncio
    async def test_process_with_dask_file(self, sample_file):
        sentences = []
        async for sentence in process_with_dask(
            file=sample_file, text=None, chunk_size=1024, batch_size=2
        ):
            sentences.append(sentence)

        assert len(sentences) > 0
        assert all(isinstance(s, str) for s in sentences)

    @pytest.mark.asyncio
    async def test_decode_chunk(self):
        encodings = [
            ("utf-8", "Hello, world!"),
            ("latin-1", "Hello, world!"),
            ("utf-16", "Hello, world!"),
        ]

        for encoding, text in encodings:
            encoded = text.encode(encoding)
            result = await decode_chunk(encoded)
            assert result == text

    @pytest.mark.asyncio
    async def test_invalid_input(self):
        with pytest.raises(HTTPException):
            async for _ in process_with_dask(file=None, text=None):
                pass
