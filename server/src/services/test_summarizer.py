import pytest
from src.services.summarizer import summarize_text


class TestSummarizer:
    @pytest.mark.asyncio
    async def test_summarize_text(self):
        async def sentence_generator():
            sentences = [
                "This is a comprehensive test sentence about artificial intelligence and its applications in modern technology.",
                "Machine learning and natural language processing are becoming increasingly important in today's technological landscape.",
                "Deep learning and neural networks are fascinating technologies that enable computers to learn from large datasets.",
                "Data science and statistics help us understand complex patterns and make informed decisions in various fields.",
                "Computer vision technology enables machines to accurately see, interpret, and understand visual information from the world.",
            ]
            for sentence in sentences:
                yield sentence

        summary = await summarize_text(
            sentence_iterator=sentence_generator(),
            num_sentences=2,
            early_termination_factor=1.0,
        )

        assert len(summary) == 2
        assert all(isinstance(s, str) for s in summary)
        assert all(len(s) > 0 for s in summary)

    @pytest.mark.asyncio
    async def test_empty_input(self):
        async def empty_generator():
            if False:
                yield

        with pytest.raises(
            ValueError, match="File is empty or contains no valid sentences"
        ):
            await summarize_text(
                sentence_iterator=empty_generator(),
                num_sentences=2,
                early_termination_factor=1.0,
            )
