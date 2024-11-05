from typing import AsyncIterator, List, Dict, Tuple
import asyncio
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import numpy as np
from collections import Counter
import logging
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfTransformer
from src.utils.text_processing import word_tokenize, STOP_WORDS
from src.services.constants import MIN_SENTENCE_LENGTH, MIN_WORDS_COUNT, MAX_SENTENCE_LENGTH

logger = logging.getLogger(__name__)


def process_sentence(sentence: Tuple[str, List[str]], word_to_index: dict):
    words = sentence[1]
    
    word_freq = Counter(words)

    row = []
    col = []
    data = []

    for word, freq in word_freq.items():
        if word in word_to_index:
            row.append(0)
            col.append(word_to_index[word])
            data.append(freq)

    sparse_vector = csr_matrix((data, (row, col)), shape=(1, len(word_to_index)))
    return sentence[0], sparse_vector



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

def calculate_tfidf_scores(word_count_matrix) -> np.ndarray:
    """
    Calculate TF-IDF scores for a word count matrix.
    
    Args:
        word_count_matrix: Sparse matrix where each row represents a sentence and each column represents a word
        
    Returns:
        numpy.ndarray: Array of sentence scores based on TF-IDF
    """
    # Initialize a TF-IDF transformer to convert the word count matrix into a TF-IDF matrix
    tfidf_transformer = TfidfTransformer(smooth_idf=True, use_idf=True)
    
    # Fit the transformer to the word count matrix and transform it into a TF-IDF matrix
    tfidf_matrix = tfidf_transformer.fit_transform(word_count_matrix)
    
    # Calculate sentence scores
    # 1. Sum TF-IDF scores for each sentence
    sentence_sums = tfidf_matrix.sum(axis=1)  # Returns sparse matrix of shape (n_sentences, 1)
    
    # 2. Convert to dense array and flatten
    return np.asarray(sentence_sums).ravel()  # Returns 1D array of shape (n_sentences,)



async def process_sentences_and_build_vocabulary(
    sentence_iterator: AsyncIterator[str],
    num_sentences: int,
    early_termination_factor: float
) -> Tuple[Dict[str, int], List[Tuple[str, List[str]]], List[csr_matrix]]:
    """
    Process sentences from iterator, build vocabulary and create sentence vectors.
    
    Args:
        sentence_iterator: Iterator yielding sentences
        num_sentences: Number of sentences to extract
        early_termination_factor: Factor for early termination
        
    Returns:
        Tuple containing:
        - word_to_index: Dictionary mapping words to indices
        - sentences: List of (sentence, filtered_words) tuples
        - sentence_vectors: List of sparse vectors representing sentences
    """
    word_to_index = {}
    sentences = []
    sentence_vectors = []

    # First pass: build complete vocabulary
    async for sentence in sentence_iterator:
        words = word_tokenize(sentence.lower())
        filtered_words = [
            word for word in words if word not in STOP_WORDS and word.isalnum()
        ]

        for word in filtered_words:
            if word not in word_to_index:
                word_to_index[word] = len(word_to_index)
        sentences.append((sentence, filtered_words))

        # Apply early termination checks
        if len(sentences) >= max(num_sentences * 10, 200) * early_termination_factor:
            break

    # Process sentences with complete vocabulary
    batch_size = max(100, 2 * num_sentences)
    for i in range(0, len(sentences), batch_size):
        batch = sentences[i : min(i + batch_size, len(sentences))]
        results = await process_sentences_batch(batch, word_to_index)

        sentence_vectors.extend([vector for _, vector in results])

    return word_to_index, sentences, sentence_vectors

async def summarize_text(
    sentence_iterator: AsyncIterator[str],
    num_sentences: int,
    early_termination_factor: float,
) -> List[str]:
    # Process sentences and build vocabulary
    word_to_index, sentences, sentence_vectors = await process_sentences_and_build_vocabulary(
        sentence_iterator, num_sentences, early_termination_factor
    )

    if not sentences:
        raise ValueError("File is empty or contains no valid sentences")

    # Create a matrix where each row represents a sentence and each column represents a word
    word_count_matrix = vstack(sentence_vectors)
    
    # Calculate sentence scores using TF-IDF
    sentence_scores = calculate_tfidf_scores(word_count_matrix)
    
    # Get the indices of sentences sorted by their scores, then take the last num_sentences entries
    sorted_indices = np.argsort(sentence_scores)  # Sort all indices by score (ascending)
    top_indices = sorted_indices[-num_sentences:]  # Take the last num_sentences indices (highest scores)
    
    # Sort the indices of the top sentences
    top_indices.sort()

    return [sentences[i][0] for i in top_indices]
