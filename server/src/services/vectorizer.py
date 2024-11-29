from typing import Dict, List
from scipy.sparse import csr_matrix
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
from sklearn.feature_extraction.text import TfidfTransformer, CountVectorizer
from src.utils.text_processing import word_tokenize, STOP_WORDS
from src.services.types import LanguageType


class TextVectorizer:
    """Handles text vectorization using different methods"""

    @staticmethod
    def vectorize_sklearn(sentences: List[str], language: LanguageType) -> csr_matrix:
        """Vectorize sentences using sklearn's CountVectorizer"""
        stop_words = list(STOP_WORDS[language])
        token_pattern = r"\b[a-zA-Z]{3,}\b"

        vectorizer = CountVectorizer(
            lowercase=True, stop_words=stop_words, token_pattern=token_pattern, min_df=2
        )

        processed_sentences = [
            " ".join(
                [
                    word
                    for word in word_tokenize(sentence.lower(), language)
                    if (
                        word not in STOP_WORDS[language]
                        and word.isalnum()
                        and len(word) > 2
                    )
                ]
            )
            for sentence in sentences
        ]

        return vectorizer.fit_transform(processed_sentences)

    @staticmethod
    def _process_sentence(
        sentence: str, word_to_index: Dict[str, int], language: LanguageType
    ) -> csr_matrix:
        """Convert a single sentence to a sparse vector"""
        words = word_tokenize(sentence.lower(), language)
        word_freq = Counter(
            word
            for word in words
            if word in word_to_index and word not in STOP_WORDS[language]
        )

        row, col, data = [], [], []
        for word, freq in word_freq.items():
            row.append(0)
            col.append(word_to_index[word])
            data.append(freq)

        return csr_matrix((data, (row, col)), shape=(1, len(word_to_index)))

    @classmethod
    async def vectorize_custom(
        cls, word_to_index: Dict[str, int], sentences: List[str], language: LanguageType
    ) -> List[csr_matrix]:
        """Vectorize sentences using custom parallel processing"""
        chunk_size = max(1000, len(sentences) // (multiprocessing.cpu_count() * 2))
        chunks = [
            sentences[i : i + chunk_size] for i in range(0, len(sentences), chunk_size)
        ]

        chunk_data = [(chunk, word_to_index, language) for chunk in chunks]

        with ProcessPoolExecutor() as executor:
            chunk_results = list(executor.map(cls._process_chunk_vectorize, chunk_data))

        results = []
        for chunk_result in chunk_results:
            results.extend(chunk_result)

        return results

    @classmethod
    def _process_chunk_vectorize(cls, chunk_data: tuple) -> List[csr_matrix]:
        """Process a chunk of sentences into sparse vectors"""
        sentences, word_to_index, language = chunk_data
        return [
            cls._process_sentence(sent, word_to_index, language) for sent in sentences
        ]
