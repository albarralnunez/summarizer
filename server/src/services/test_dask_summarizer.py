import pytest
import numpy as np
from scipy.sparse import csr_matrix
from src.services.dask_summarizer import (
    summarize_text_dask,
    build_vocabulary,
    process_sentence_dask,
    compute_tfidf,
    compute_sentence_scores,
)


class TestDaskSummarizer:
    @pytest.mark.asyncio
    async def test_summarize_text_dask(self, mock_dask_client):
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

        summary = await summarize_text_dask(
            sentence_iterator=sentence_generator(),
            num_sentences=2,
            early_termination_factor=1.0,
            client=mock_dask_client,
        )

        assert len(summary) == 2
        assert all(isinstance(s, str) for s in summary)

    def test_build_vocabulary(self, word_to_index):
        sentence = "This is artificial intelligence and machine learning"
        vocab = build_vocabulary(sentence, word_to_index.copy())

        assert len(vocab) >= len(word_to_index)
        assert isinstance(vocab, dict)
        assert all(isinstance(k, str) and isinstance(v, int) for k, v in vocab.items())

    def test_process_sentence_dask(self, word_to_index):
        sentence = "artificial intelligence and machine learning"
        result = process_sentence_dask(sentence, word_to_index)

        assert isinstance(result, tuple)
        assert len(result) == 2
        assert isinstance(result[0], str)
        assert isinstance(result[1], csr_matrix)

    def test_compute_tfidf(self):
        data = np.array([[1, 1, 0], [0, 1, 1]])
        matrix = csr_matrix(data)

        tfidf_matrix = compute_tfidf(matrix)
        assert isinstance(tfidf_matrix, csr_matrix)
        assert tfidf_matrix.shape == matrix.shape

    def test_compute_sentence_scores(self):
        tfidf_matrix = csr_matrix([[0.5, 0.5], [0.3, 0.7]])
        sentence_lengths = [["word1", "word2"], ["word1", "word2", "word3"]]

        scores = compute_sentence_scores(tfidf_matrix, sentence_lengths)
        assert isinstance(scores, np.ndarray)
        assert len(scores) == len(sentence_lengths)
        assert all(0 <= score <= 1 for score in scores)

    @pytest.mark.asyncio
    async def test_empty_input(self):
        async def empty_generator():
            if False:
                yield

        with pytest.raises(
            ValueError, match="No valid sentences found in the input text"
        ):
            await summarize_text_dask(
                sentence_iterator=empty_generator(),
                num_sentences=2,
                early_termination_factor=1.0,
                client=None,
            )
