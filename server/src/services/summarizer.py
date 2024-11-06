from typing import AsyncIterator, List, Dict, Tuple, Union, NamedTuple, Literal, Optional
import numpy as np
from collections import Counter
import logging
from scipy.sparse import csr_matrix, vstack
from sklearn.feature_extraction.text import TfidfTransformer, CountVectorizer
from src.utils.text_processing import word_tokenize, STOP_WORDS
from functools import lru_cache
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from src.api.models import TextStatistics
from src.services.language import LanguageType
from src.services.text_processor import TextProcessor
from src.services.types import TokenizedSentence

logger = logging.getLogger(__name__)

class ProcessedData(NamedTuple):
    word_to_index: Dict[str, int]
    sentences: List[TokenizedSentence]
    word_counts: Counter
    total_words: int
    language: LanguageType

async def process_text(
    sentence_iterator: Union[AsyncIterator[str], List[str]],
    language: LanguageType = "english",
    compute_statistics: bool = True,
    num_sentences: Optional[int] = None,
    early_termination_factor: float = 2.0
) -> ProcessedData:
    """Process text and optionally compute statistics using parallel processing"""
    # Handle both async iterator and list inputs
    if isinstance(sentence_iterator, list):
        sentences = sentence_iterator
    else:
        sentences = [s async for s in sentence_iterator]
    
    processor = TextProcessor(language)
    return await processor.process_text(
        sentences, 
        compute_statistics=compute_statistics,
        num_sentences=num_sentences,
        early_termination_factor=early_termination_factor
    )

def calculate_text_statistics(
    processed_data: ProcessedData,
    word_scores: Optional[Dict[str, float]] = None
) -> TextStatistics:
    """Calculate text statistics from processed data"""
    if processed_data.language not in STOP_WORDS:
        raise ValueError(f"Unsupported language: {processed_data.language}")
        
    if not processed_data.metrics:
        raise ValueError("No metrics available - statistics computation was disabled")
        
    stop_words = STOP_WORDS[processed_data.language]
    
    # Use metrics from processed_data instead of direct word_counts
    word_counts = processed_data.metrics.word_frequencies
    sentence_count = len(processed_data.sentences)
    unique_words = processed_data.metrics.unique_words
    
    # Get vocabulary size from word_to_index
    vocabulary_size = len(processed_data.word_to_index)
    
    # Filter stop words for most common words using language-specific stop words
    content_words = {
        word: count for word, count in word_counts.items()
        if word not in stop_words
    }
    most_common = sorted(
        content_words.items(),
        key=lambda x: (-x[1], x[0])
    )[:10]

    # Process top scoring words if available
    top_scoring_words = []
    if word_scores:
        filtered_scores = {
            word: score for word, score in word_scores.items()
            if word not in stop_words
        }
        top_scoring_words = sorted(
            filtered_scores.items(),
            key=lambda x: (-x[1], x[0])
        )[:10]

    return TextStatistics(
        word_count=processed_data.metrics.word_count,
        sentence_count=sentence_count,
        unique_words=unique_words,
        vocabulary_size=vocabulary_size,
        avg_sentence_length=(
            processed_data.metrics.word_count / sentence_count 
            if sentence_count > 0 else 0
        ),
        most_common_words=most_common,
        top_scoring_words=top_scoring_words
    )

async def summarize_text(
    sentence_iterator: Union[AsyncIterator[str], List[str]],
    num_sentences: int,
    early_termination_factor: float = 2.0,
    algorithm: str = "default",
    language: LanguageType = "english",
    compute_statistics: bool = True
) -> Tuple[List[str], Optional[TextStatistics]]:
    """Summarize text and optionally compute statistics using parallel processing."""
    if language not in STOP_WORDS:
        raise ValueError(f"Unsupported language: {language}")

    processed_data = await process_text(
        sentence_iterator, 
        language=language,
        compute_statistics=compute_statistics,
        num_sentences=num_sentences,
        early_termination_factor=early_termination_factor
    )
    
    if not processed_data.sentences:
        raise ValueError("File is empty or contains no valid sentences")

    # Dispatch to appropriate algorithm
    if algorithm == "simple":
        summary, word_scores = summarize_simple(
            processed_data, 
            num_sentences, 
            compute_statistics,
            early_termination_factor=early_termination_factor
        )
    elif algorithm == "sklearn":
        summary, word_scores = summarize_sklearn(
            processed_data, 
            num_sentences, 
            compute_statistics,
            early_termination_factor=early_termination_factor
        )
    else:
        summary, word_scores = await summarize_default(
            processed_data, 
            num_sentences, 
            compute_statistics,
            early_termination_factor=early_termination_factor
        )

    # Always create basic statistics with vocabulary size
    statistics = TextStatistics(
        word_count=0,
        sentence_count=len(processed_data.sentences),
        unique_words=0,
        vocabulary_size=len(processed_data.word_to_index),
        avg_sentence_length=0,
        most_common_words=[],
        top_scoring_words=[]
    )

    # Add detailed statistics if enabled
    if compute_statistics and processed_data.metrics:
        try:
            statistics = calculate_text_statistics(processed_data, word_scores)
        except ValueError as e:
            logger.warning(f"Failed to calculate detailed statistics: {e}")
    
    return summary, statistics

def summarize_simple(
    processed_data: ProcessedData,
    num_sentences: int,
    compute_statistics: bool = True,
    early_termination_factor: float = 2.0
) -> Tuple[List[str], Optional[Dict[str, float]]]:
    """Simple summarization using the same approach as the default algorithm."""
    stop_words = list(STOP_WORDS[processed_data.language])
    
    # Create sentence vectors using the same preprocessing as default
    sentence_vectors = []
    for sentence in processed_data.sentences:
        # Use pre-tokenized words directly from TokenizedSentence
        filtered_words = [
            word for word in sentence.tokens 
            if (word in processed_data.word_to_index and 
                word not in stop_words)
        ]
        
        # Create sparse vector for sentence
        word_freq = Counter(filtered_words)
        row = []
        col = []
        data = []
        
        for word, freq in word_freq.items():
            row.append(0)
            col.append(processed_data.word_to_index[word])
            data.append(freq)
                
        sentence_vectors.append(
            csr_matrix(
                (data, (row, col)), 
                shape=(1, len(processed_data.word_to_index))
            )
        )
    
    # Calculate TF-IDF scores
    word_count_matrix = vstack(sentence_vectors)
    tfidf = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_matrix = tfidf.fit_transform(word_count_matrix)
    
    # Calculate sentence scores and get top sentences
    sentence_scores = np.asarray(tfidf_matrix.sum(axis=1)).ravel()
    top_indices = np.argsort(sentence_scores)[-num_sentences:]
    top_indices.sort()
    
    # Only compute word scores if statistics are needed
    word_scores = None
    if compute_statistics:
        word_importance = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
        word_scores = {
            word: float(word_importance[idx])
            for word, idx in processed_data.word_to_index.items()
            if (word not in stop_words and
                len(word) > 2 and
                word_importance[idx] > 0 and
                word.isalnum())
        }
        
        # Normalize word scores
        if word_scores:
            max_score = max(word_scores.values())
            if max_score > 0:
                word_scores = {
                    word: score / max_score
                    for word, score in word_scores.items()
                }
    
    return [processed_data.sentences[i].original for i in top_indices], word_scores

def summarize_sklearn(
    processed_data: ProcessedData,
    num_sentences: int,
    compute_statistics: bool = True,
    early_termination_factor: float = 2.0
) -> Tuple[List[str], Optional[Dict[str, float]]]:
    """Summarize using sklearn's TF-IDF implementation."""
    stop_words = list(STOP_WORDS[processed_data.language])
    token_pattern = r'\b[a-zA-Z]{3,}\b'
    
    # Start with less restrictive min_df
    min_df = 1
    
    # Just join the pre-tokenized words - they're already filtered in TextProcessor
    processed_sentences = [
        ' '.join(sentence.tokens) for sentence in processed_data.sentences
    ]
    
    vectorizer = CountVectorizer(
        lowercase=True,
        stop_words=stop_words,
        token_pattern=token_pattern,
        min_df=min_df
    )
    
    word_count_matrix = vectorizer.fit_transform(processed_sentences)
    
    tfidf = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_matrix = tfidf.fit_transform(word_count_matrix)
    
    sentence_scores = np.asarray(tfidf_matrix.sum(axis=1)).ravel()
    top_indices = np.argsort(sentence_scores)[-num_sentences:]
    top_indices.sort()
    
    # Only compute word scores if statistics are needed
    word_scores = None
    if compute_statistics:
        word_importance = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
        feature_names = vectorizer.get_feature_names_out()
        
        word_scores = {
            word: float(score)
            for word, score in zip(feature_names, word_importance)
            if (word not in STOP_WORDS[processed_data.language] and
                len(word) > 2 and
                score > 0 and
                word.isalnum())
        }
        
        # Normalize word scores
        if word_scores:
            max_score = max(word_scores.values())
            if max_score > 0:
                word_scores = {
                    word: score / max_score
                    for word, score in word_scores.items()
                }
    
    return [processed_data.sentences[i].original for i in top_indices], word_scores
    

async def summarize_default(
    processed_data: ProcessedData,
    num_sentences: int,
    compute_statistics: bool = True,
    early_termination_factor: float = 2.0
) -> Tuple[List[str], Optional[Dict[str, float]]]:
    """Default summarization using custom vectorization."""
    stop_words = list(STOP_WORDS[processed_data.language])
    
    # Use pre-tokenized data from processed_data
    sentence_vectors = await vectorize_sentences(
        word_to_index=processed_data.word_to_index,
        sentences=processed_data.sentences,  # Pass TokenizedSentence objects directly
        language=processed_data.language
    )
    
    word_count_matrix = vstack(sentence_vectors)
    tfidf = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_matrix = tfidf.fit_transform(word_count_matrix)
    
    sentence_scores = np.asarray(tfidf_matrix.sum(axis=1)).ravel()
    top_indices = np.argsort(sentence_scores)[-num_sentences:]
    top_indices.sort()
    
    # Only compute word scores if statistics are needed
    word_scores = None
    if compute_statistics:
        word_importance = np.asarray(tfidf_matrix.mean(axis=0)).ravel()
        
        word_scores = {
            word: float(word_importance[idx])
            for word, idx in processed_data.word_to_index.items()
            if (word not in STOP_WORDS[processed_data.language] and
                len(word) > 2 and
                word_importance[idx] > 0 and
                word.isalnum())
        }
        
        # Normalize word scores
        if word_scores:
            max_score = max(word_scores.values())
            if max_score > 0:
                word_scores = {
                    word: score / max_score
                    for word, score in word_scores.items()
                }
    
    return [processed_data.sentences[i].original for i in top_indices], word_scores

def calculate_tfidf_scores(word_count_matrix: csr_matrix) -> np.ndarray:
    """Calculate TF-IDF scores for a word count matrix"""
    tfidf_transformer = TfidfTransformer(smooth_idf=True, use_idf=True)
    tfidf_matrix = tfidf_transformer.fit_transform(word_count_matrix)
    return np.asarray(tfidf_matrix.sum(axis=1)).ravel()

def vectorize_sentences_simple(sentences: List[str]) -> List[csr_matrix]:
    """Convert sentences into sparse vectors using simple sequential processing"""
    return [process_sentence(sentence) for sentence in sentences]

def process_sentence(sentence: TokenizedSentence, word_to_index: Dict[str, int], language: LanguageType) -> csr_matrix:
    """Process a single sentence into a sparse vector"""
    stop_words = STOP_WORDS[language]
    
    # Use pre-tokenized words directly from TokenizedSentence
    word_freq = Counter(
        word for word in sentence.tokens 
        if word in word_to_index and word not in stop_words
    )
    
    row = []
    col = []
    data = []
    
    for word, freq in word_freq.items():
        row.append(0)
        col.append(word_to_index[word])
        data.append(freq)
            
    return csr_matrix((data, (row, col)), shape=(1, len(word_to_index)))

def process_chunk_vectorize(chunk_data: Tuple[List[str], Dict[str, int], LanguageType]) -> List[csr_matrix]:
    """Process a chunk of sentences into sparse vectors
    
    Args:
        chunk_data: Tuple containing (sentences, word_to_index)
        
    Returns:
        List of sparse matrices representing the vectorized sentences
    """
    sentences, word_to_index, language = chunk_data
    return [process_sentence(sent, word_to_index, language) for sent in sentences]

async def vectorize_sentences(
    word_to_index: Dict[str, int],
    sentences: List[str],
    language: LanguageType
) -> List[csr_matrix]:
    """Convert sentences into sparse vectors using parallel processing"""
    chunk_size = max(1000, len(sentences) // (multiprocessing.cpu_count() * 2))
    chunks = [sentences[i:i + chunk_size] for i in range(0, len(sentences), chunk_size)]
    
    # Create chunks with word_to_index dictionary
    chunk_data = [(chunk, word_to_index, language) for chunk in chunks]
    
    # Process chunks in parallel
    with ProcessPoolExecutor() as executor:
        chunk_results = list(executor.map(process_chunk_vectorize, chunk_data))
        
    # Flatten results
    results = []
    for chunk_result in chunk_results:
        results.extend(chunk_result)
    
    return results
