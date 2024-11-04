from typing import AsyncIterator, List, Dict, Tuple
import asyncio
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import numpy as np
import logging
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfTransformer
from src.utils.text_processing import word_tokenize, STOP_WORDS
from src.services.constants import MIN_SENTENCE_LENGTH, MIN_WORDS_COUNT, MAX_SENTENCE_LENGTH

logger = logging.getLogger(__name__)


def process_sentence(sentence: str, word_to_index: dict):
    words = word_tokenize(sentence.lower())
    word_freq = {
        word: words.count(word)
        for word in set(words)
        if word not in STOP_WORDS and word.isalnum()
    }

    row = []
    col = []
    data = []
    for word, freq in word_freq.items():
        if word in word_to_index:
            row.append(0)
            col.append(word_to_index[word])
            data.append(freq)

    sparse_vector = csr_matrix((data, (row, col)), shape=(1, len(word_to_index)))
    return sentence, sparse_vector


async def process_batch(batch: List[str], word_to_index: Dict[str, int]) -> List[str]:
    processed_batch = []
    for sentence in batch:
        words = word_tokenize(sentence.lower())
        for word in words:
            if word not in STOP_WORDS and word.isalnum() and word not in word_to_index:
                word_to_index[word] = len(word_to_index)
        processed_batch.append(sentence)
    return processed_batch


async def process_sentences_batch(
    batch: List[str], word_to_index: Dict[str, int]
) -> List[Tuple[str, csr_matrix]]:
    loop = asyncio.get_running_loop()
    with ProcessPoolExecutor(max_workers=multiprocessing.cpu_count()) as executor:
        futures = [
            loop.run_in_executor(executor, process_sentence, sentence, word_to_index)
            for sentence in batch
        ]
        return await asyncio.gather(*futures)


async def summarize_text(
    sentence_iterator: AsyncIterator[str],
    num_sentences: int,
    early_termination_factor: float,
) -> List[str]:
    word_to_index = {}
    sentences = []
    sentence_vectors = []
    current_batch = []

    # First pass: build complete vocabulary
    async for sentence in sentence_iterator:
        # Skip sentences that are too short or too long
        if len(sentence) < MIN_SENTENCE_LENGTH or len(sentence) > MAX_SENTENCE_LENGTH:
            continue

        words = word_tokenize(sentence.lower())
        filtered_words = [
            word for word in words if word not in STOP_WORDS and word.isalnum()
        ]

        # Skip sentences with too few meaningful words
        if len(filtered_words) < MIN_WORDS_COUNT:
            continue

        for word in filtered_words:
            if word not in word_to_index:
                word_to_index[word] = len(word_to_index)
        sentences.append(sentence)

        # Apply early termination checks
        if len(sentences) >= max(num_sentences * 10, 200) * early_termination_factor:
            break

    # Process sentences with complete vocabulary
    batch_size = max(100, 2 * num_sentences)
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i : min(i + batch_size, len(sentences))]
        results = await process_sentences_batch(batch, word_to_index)

        for _, sparse_vector in results:
            sentence_vectors.append(sparse_vector)

    if not sentences:
        raise ValueError("File is empty or contains no valid sentences")

    word_count_matrix = vstack(sentence_vectors)
    tfidf_transformer = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_matrix = tfidf_transformer.fit_transform(word_count_matrix)
    sentence_scores = np.asarray(tfidf_matrix.sum(axis=1)).ravel()
    top_indices = np.argsort(sentence_scores)[-num_sentences:]
    top_indices.sort()

    return [sentences[i] for i in top_indices]
