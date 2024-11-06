import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from typing import List, Union, Tuple, Dict
from collections import Counter
from src.api.models import TextStatistics
import concurrent.futures
from functools import lru_cache
from src.services.language import LanguageType

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<!\w\.\w.)(?![A-Z][a-z]\.)(?<=\.|\?|\!)\s")
PREPROCESS_PATTERN = re.compile(r"[^\w\s]")
STOP_WORDS = {
    "english": set(stopwords.words("english")),
    "spanish": set(stopwords.words("spanish"))
}

@lru_cache(maxsize=1024)
def tokenize_and_clean_sentence(sentence: str, language: LanguageType = "english") -> List[str]:
    """Tokenize and clean words from a sentence with caching"""
    return [
        word.lower() for word in word_tokenize(sentence, language=language)
        if word.isalnum()
    ]

def calculate_text_statistics(sentences: List[str], language: LanguageType = "english") -> TextStatistics:
    """Calculate various statistics about the input text using parallel processing"""
    # Early return for empty input
    if not sentences:
        return TextStatistics(
            word_count=0,
            sentence_count=0,
            unique_words=0,
            avg_word_length=0,
            avg_sentence_length=0,
            most_common_words=[]
        )

    if language not in STOP_WORDS:
        raise ValueError(f"Unsupported language: {language}")
    
    stop_words = STOP_WORDS[language]  # Get language-specific stop words

    # Determine optimal chunk size based on number of sentences
    chunk_size = max(1, len(sentences) // (4 * concurrent.futures.cpu_count()))
    sentence_chunks = [
        sentences[i:i + chunk_size] 
        for i in range(0, len(sentences), chunk_size)
    ]

    # Process chunks in parallel
    word_counts_total = Counter()
    total_words = 0
    total_word_length = 0

    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Submit all chunks for processing with language parameter
        future_to_chunk = {
            executor.submit(process_chunk, chunk, language): chunk 
            for chunk in sentence_chunks
        }

        # Collect results as they complete
        for future in concurrent.futures.as_completed(future_to_chunk):
            word_counts, words_count, word_length = future.result()
            word_counts_total.update(word_counts)
            total_words += words_count
            total_word_length += word_length

    # Calculate final statistics
    sentence_count = len(sentences)
    unique_words = len(word_counts_total)
    
    # Filter stop words using language-specific stop words
    content_words = {
        word: count for word, count in word_counts_total.items()
        if word not in stop_words
    }
    most_common = sorted(
        content_words.items(),
        key=lambda x: (-x[1], x[0])  # Sort by count desc, then word asc
    )[:10]

    return TextStatistics(
        word_count=total_words,
        sentence_count=sentence_count,
        unique_words=unique_words,
        avg_word_length=round(total_word_length / total_words, 2) if total_words > 0 else 0,
        avg_sentence_length=round(total_words / sentence_count, 2) if sentence_count > 0 else 0,
        most_common_words=most_common
    )

def split_into_sentences(text: Union[str, List[str]]) -> List[str]:
    """Split text into sentences using both regex and NLTK for better accuracy."""
    if isinstance(text, list):
        text = " ".join(str(item) for item in text)

    text = re.sub(r"\s+", " ", text.strip())
    sentences = sent_tokenize(text)

    final_sentences = []
    for sentence in sentences:
        if len(sentence) > 200:
            splits = re.split(r"(?<=[.!?])\s+", sentence)
            final_sentences.extend(s.strip() for s in splits if s.strip())
        else:
            final_sentences.append(sentence.strip())

    return [
        s for s in final_sentences
        if (
            s
            and len(s) >= 10
            and any(c.isalpha() for c in s)
            and s.strip(".-_,;:!? ").strip()
        )
    ]

async def yield_sentences(text: str):
    for sentence in split_into_sentences(text):
        yield sentence
