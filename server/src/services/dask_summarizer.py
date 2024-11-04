from typing import AsyncIterator, List
import asyncio
import numpy as np
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfTransformer
from ..utils.text_processing import word_tokenize, STOP_WORDS
from dask.distributed import Client, TimeoutError as DaskTimeoutError
from dask import delayed, bag as db
import dask.array as da
import logging
from concurrent.futures import CancelledError
from functools import lru_cache
import dask
from dask.delayed import delayed
from .constants import MIN_SENTENCE_LENGTH, MIN_WORDS_COUNT, MAX_SENTENCE_LENGTH

logger = logging.getLogger(__name__)


# Custom exceptions
class SummarizationError(Exception):
    """Base exception for summarization errors"""

    pass


class EmptyInputError(SummarizationError):
    """Raised when input text is empty"""

    pass


class ProcessingError(SummarizationError):
    """Raised when processing fails"""

    pass


class VocabularyBuildError(SummarizationError):
    """Raised when vocabulary building fails"""

    pass


class TfidfError(SummarizationError):
    """Raised when TF-IDF transformation fails"""

    pass


# Add caching for vocabulary building
@lru_cache(maxsize=1000)
def _tokenize_and_filter(sentence: str) -> tuple:
    """Cached tokenization for better performance"""
    # Skip sentences that are too short or too long
    if len(sentence) < MIN_SENTENCE_LENGTH or len(sentence) > MAX_SENTENCE_LENGTH:
        return tuple()

    words = word_tokenize(sentence.lower())
    filtered_words = tuple(
        word for word in words if word not in STOP_WORDS and word.isalnum()
    )

    # Skip sentences with too few meaningful words
    if len(filtered_words) < MIN_WORDS_COUNT:
        return tuple()

    return filtered_words


def build_vocabulary(sentence: str, existing_vocab: dict) -> dict:
    """Optimized vocabulary building"""
    try:
        words = _tokenize_and_filter(sentence)
        if not words:
            return existing_vocab

        new_vocab = existing_vocab.copy()
        vocab_size = len(existing_vocab)

        # Batch update vocabulary
        new_words = set(words) - set(existing_vocab.keys())
        new_vocab.update({word: vocab_size + i for i, word in enumerate(new_words)})

        return new_vocab
    except Exception as e:
        logger.error("Vocabulary building failed: %s", str(e))
        raise VocabularyBuildError(f"Vocabulary building failed: {str(e)}")


def process_sentence_dask(sentence: str, word_to_index: dict):
    """Process a single sentence into a sparse vector (Dask-compatible version)"""
    logger.debug(
        "Processing sentence of length %d with vocabulary size %d",
        len(sentence),
        len(word_to_index),
    )
    try:
        words = word_tokenize(sentence.lower())
        word_freq = {}
        for word in words:
            if word not in STOP_WORDS and word.isalnum():
                word_freq[word] = word_freq.get(word, 0) + 1

        row = []
        col = []
        data = []
        for word, freq in word_freq.items():
            if word in word_to_index:
                row.append(0)
                col.append(word_to_index[word])
                data.append(freq)

        sparse_vector = csr_matrix((data, (row, col)), shape=(1, len(word_to_index)))
        logger.debug("Created sparse vector with %d non-zero elements", len(data))
        return sentence, sparse_vector
    except ValueError as e:
        logger.error("Sentence processing failed: %s", str(e))
        raise ProcessingError(f"Invalid word processing: {str(e)}")
    except AttributeError as e:
        logger.error("Sentence processing failed: %s", str(e))
        raise ProcessingError(f"Invalid sentence format: {str(e)}")
    except MemoryError as e:
        logger.error("Memory error during processing: %s", str(e))
        raise ProcessingError(f"Memory error during processing: {str(e)}")


def compute_tfidf(word_count_matrix):
    """Optimized TF-IDF computation with proper sparse matrix handling"""
    logger.debug(
        "Computing TF-IDF for matrix of shape %s", str(word_count_matrix.shape)
    )
    try:
        # Ensure input is in CSR format
        if not isinstance(word_count_matrix, csr_matrix):
            word_count_matrix = csr_matrix(word_count_matrix)

        # Convert to dense array for initial calculations
        matrix_array = word_count_matrix.toarray()

        # Compute term frequency (TF)
        row_sums = np.sum(matrix_array, axis=1, keepdims=True)
        # Avoid division by zero
        row_sums = np.where(row_sums == 0, 1, row_sums)
        tf = matrix_array / row_sums

        # Compute IDF
        n_samples = matrix_array.shape[0]
        document_freq = np.sum(matrix_array > 0, axis=0)
        # Avoid log(0) by adding 1
        idf = np.log((n_samples + 1) / (document_freq + 1)) + 1

        # Compute TF-IDF
        tfidf_matrix = tf * idf

        # Convert back to sparse matrix for memory efficiency
        return csr_matrix(tfidf_matrix)

    except Exception as e:
        logger.error("TF-IDF computation failed: %s", str(e), exc_info=True)
        raise TfidfError(f"TF-IDF computation failed: {str(e)}")


def compute_sentence_scores(tfidf_matrix, sentence_lengths):
    """Compute sentence scores using TF-IDF and position information"""
    logger.debug("Computing enhanced sentence scores")

    # Get raw TF-IDF scores
    tfidf_scores = np.asarray(tfidf_matrix.sum(axis=1)).ravel()

    # Normalize scores to 0-1 range
    if tfidf_scores.max() != tfidf_scores.min():
        normalized_scores = (tfidf_scores - tfidf_scores.min()) / (
            tfidf_scores.max() - tfidf_scores.min()
        )
    else:
        normalized_scores = np.ones_like(tfidf_scores)

    # Add position bias (favor sentences near the beginning, but less aggressively)
    position_weights = 1.0 / (1 + np.arange(len(normalized_scores)) * 0.05)

    # Add length bias (favor medium-length sentences)
    length_scores = np.array(
        [
            min(1.0, len(words) / 50) * max(0.1, 1 - (len(words) / 100))
            for words in sentence_lengths
        ]
    )

    # Combine scores with weights
    final_scores = (
        0.5 * normalized_scores + 0.3 * position_weights + 0.2 * length_scores
    )

    logger.debug(
        "Score statistics - Mean: %.3f, Std: %.3f, Max: %.3f, Min: %.3f",
        final_scores.mean(),
        final_scores.std(),
        final_scores.max(),
        final_scores.min(),
    )

    return final_scores


async def summarize_text_dask(
    sentence_iterator: AsyncIterator[str],
    num_sentences: int,
    early_termination_factor: float,
    client: Client,
) -> List[str]:
    logger.debug(f"Starting summarization: requesting {num_sentences} sentences")

    sentences = []
    word_to_index = {}
    sentence_lengths = []

    # First pass: collect sentences and build complete vocabulary
    async for sentence in sentence_iterator:
        # Skip very short sentences
        if len(sentence) < MIN_SENTENCE_LENGTH:
            continue

        words = _tokenize_and_filter(sentence)
        if not words:
            continue

        # Skip sentences with too few meaningful words
        if len(words) < MIN_WORDS_COUNT:
            continue

        # Update vocabulary
        for word in words:
            if word not in word_to_index:
                word_to_index[word] = len(word_to_index)

        sentences.append(sentence)
        sentence_lengths.append(words)  # Store tokenized words for length scoring

        # Early termination check
        if len(sentences) >= max(num_sentences * 10, 200) * early_termination_factor:
            break

    if not sentences:
        raise ValueError("No valid sentences found in the input text")

    try:
        # Process sentences with complete vocabulary
        batch_size = min(max(100, len(sentences) // 20), 1000)
        futures = []

        for i in range(0, len(sentences), batch_size):
            batch = sentences[i : i + batch_size]
            future = client.map(
                process_sentence_dask, batch, [word_to_index] * len(batch)
            )
            futures.extend(future)

        # Process results
        processed = client.gather(futures)
        if not processed:
            raise ValueError("Failed to process sentences")

        processed_sentences, vectors = zip(*processed)
        word_count_matrix = vstack(vectors)

        if word_count_matrix.shape[0] == 0:
            raise ValueError("No valid sentences could be processed")

        tfidf_matrix = compute_tfidf(word_count_matrix)
        sentence_scores = compute_sentence_scores(tfidf_matrix, sentence_lengths)

        # Select sentences with improved diversity
        selected_indices = []
        remaining_indices = set(range(len(sentences)))

        while len(selected_indices) < num_sentences and remaining_indices:
            best_score = float("-inf")
            best_idx = None

            for idx in remaining_indices:
                score = sentence_scores[idx]

                # Penalize sentences that are too close to already selected ones
                if selected_indices:
                    for selected_idx in selected_indices:
                        if (
                            abs(idx - selected_idx) < 3
                        ):  # Minimum distance of 3 sentences
                            score *= 0.3  # Stronger penalty for nearby sentences

                        # Additional penalty for very similar lengths
                        len_diff = abs(
                            len(sentence_lengths[idx])
                            - len(sentence_lengths[selected_idx])
                        )
                        if len_diff < 5:
                            score *= 0.8

                if score > best_score:
                    best_score = score
                    best_idx = idx

            if best_idx is not None:
                selected_indices.append(best_idx)
                remaining_indices.remove(best_idx)

        selected_indices.sort()
        return [processed_sentences[i] for i in selected_indices]

    except DaskTimeoutError:
        raise ValueError("Dask processing timed out - try with a smaller input")
    except CancelledError:
        raise ValueError("Processing was cancelled")
    except MemoryError:
        raise ValueError(
            "Not enough memory to process the input - try with a smaller text"
        )
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {str(e)}")
        raise ValueError(f"Failed to process text: {str(e)}")
