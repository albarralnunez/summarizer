from typing import Dict, List, Counter, NamedTuple, Optional, Tuple
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import logging
from src.services.base_processor import BaseTextProcessor
from src.services.language import LanguageType
from src.services.statistics import TextMetrics

logger = logging.getLogger(__name__)


class TokenizedSentence(NamedTuple):
    original: str
    tokens: List[str]


class ProcessedData(NamedTuple):
    word_to_index: Dict[str, int]
    sentences: List[TokenizedSentence]
    metrics: Optional[TextMetrics]
    language: LanguageType


class TextProcessor(BaseTextProcessor):
    """Handles text processing and statistics calculation"""

    def _process_chunk(self, chunk_data: tuple) -> tuple:
        """Process a chunk of sentences and return local statistics"""
        tokenized_sentences, compute_statistics = chunk_data
        local_word_to_index = {}

        # Only initialize statistics counters if needed
        local_word_counts = Counter() if compute_statistics else None
        local_total_words = 0 if compute_statistics else None
        local_total_word_length = 0 if compute_statistics else None

        for sentence in tokenized_sentences:
            # Use pre-tokenized words
            words = sentence.tokens

            # Only compute statistics if needed
            if compute_statistics:
                local_word_counts.update(words)
                local_total_words += len(words)
                local_total_word_length += sum(len(word) for word in words)

            for word in words:
                if word not in local_word_to_index:
                    local_word_to_index[word] = 0

        return (
            local_word_to_index,
            local_word_counts,
            local_total_words,
            local_total_word_length,
        )

    def _tokenize_sentence(self, sentence: str) -> TokenizedSentence:
        """Tokenize a sentence and store both original and tokens"""
        tokens = [
            word
            for word in self.tokenize_sentence(sentence)
            if word.isalnum() and len(word) > 2
        ]
        return TokenizedSentence(original=sentence, tokens=tokens)

    def _calculate_early_termination(
        self,
        total_sentences: int,
        num_sentences: int,
        early_termination_factor: float = 2.0,
    ) -> int:
        """Calculate early termination point based on text length and requested summary size

        Args:
            total_sentences: Total number of sentences in text
            num_sentences: Number of sentences requested for summary
            early_termination_factor: Custom multiplier for early termination (default: 2.0)
                - Lower values (1.0-3.0): Process fewer sentences, smaller vocabulary
                - Medium values (3.0-7.0): Process more sentences, medium vocabulary
                - Higher values (7.0-10.0): Process most sentences, larger vocabulary
        """
        # Direct mapping of factor to percentage of total sentences to process
        percentage = (early_termination_factor - 1.0) / 9.0
        base_sentences = int(total_sentences * percentage)

        # Ensure we process at least enough sentences for the summary
        min_sentences = int(num_sentences * 1.5)

        # Return the larger of the calculated values, but no more than total sentences
        return min(max(base_sentences, min_sentences), total_sentences)

    def _is_valid_sentence(self, sentence: str, min_length: int = 40) -> bool:
        """Check if a sentence is valid for processing

        Args:
            sentence: The sentence to check
            min_length: Minimum character length (default: 40)

        Returns:
            bool: True if sentence is valid, False otherwise
        """
        # Remove extra whitespace
        cleaned = " ".join(sentence.split())

        # Basic validity checks
        if (
            len(cleaned) < min_length  # Too short
            or not any(c.isalpha() for c in cleaned)  # No letters
            or cleaned.count(" ") < 3
        ):  # Too few words
            return False

        # Check for common invalid patterns
        invalid_patterns = [
            "figure",
            "fig.",
            "table",
            "chapter",  # References
            "http://",
            "https://",
            "www.",  # URLs
            "@",
            "#",  # Social media
        ]

        lower_cleaned = cleaned.lower()
        if any(pattern in lower_cleaned for pattern in invalid_patterns):
            return False

        return True

    async def process_text(
        self,
        sentences: List[str],
        compute_statistics: bool = True,
        num_sentences: Optional[int] = None,
        min_sentence_length: int = 40,
        early_termination_factor: float = 2.0,
    ) -> ProcessedData:
        """Process text and optionally compute statistics using parallel processing"""
        if not sentences:
            return ProcessedData(
                word_to_index={},
                sentences=[],
                metrics=(
                    TextMetrics(0, 0, 0, 0, Counter()) if compute_statistics else None
                ),
                language=self.language,
            )

        # Filter and tokenize sentences in one pass
        valid_sentences = [
            self._tokenize_sentence(s)
            for s in sentences
            if self._is_valid_sentence(s, min_sentence_length)
        ]

        if not valid_sentences:
            logger.warning("No valid sentences found after filtering")
            return ProcessedData(
                word_to_index={},
                sentences=[],
                metrics=(
                    TextMetrics(0, 0, 0, 0, Counter()) if compute_statistics else None
                ),
                language=self.language,
            )

        # Apply early termination if needed
        sentences_to_process = valid_sentences
        if not compute_statistics and num_sentences:
            try:
                termination_point = self._calculate_early_termination(
                    len(valid_sentences), num_sentences, early_termination_factor
                )
                sentences_to_process = valid_sentences[:termination_point]
                logger.info(
                    f"Early termination applied: Processing {termination_point} out of {len(valid_sentences)} sentences "
                    f"(factor: {early_termination_factor})"
                )
            except Exception as e:
                logger.warning(
                    f"Failed to apply early termination: {e}. Processing all sentences."
                )
                sentences_to_process = valid_sentences

        # Process chunks with tokenized sentences
        chunk_size = max(
            1000, len(sentences_to_process) // (multiprocessing.cpu_count() * 2)
        )
        chunks = [
            sentences_to_process[i : i + chunk_size]
            for i in range(0, len(sentences_to_process), chunk_size)
        ]

        chunk_data = [(chunk, compute_statistics) for chunk in chunks]

        with ProcessPoolExecutor() as executor:
            chunk_results = list(executor.map(self._process_chunk, chunk_data))

        processed_data = self._merge_chunk_results(
            chunk_results, sentences_to_process, compute_statistics
        )

        filtered_count = len(sentences) - len(valid_sentences)
        if filtered_count > 0:
            logger.info(
                f"Filtered out {filtered_count} invalid sentences "
                f"({filtered_count/len(sentences)*100:.1f}%)"
            )

        return processed_data

    def _merge_chunk_results(
        self,
        chunk_results: List[tuple],
        sentences: List[TokenizedSentence],
        compute_statistics: bool,
    ) -> ProcessedData:
        """Merge results from parallel processing chunks"""
        word_to_index = {}
        current_index = 0

        # Only initialize statistics variables if needed
        word_counts = Counter() if compute_statistics else None
        total_words = 0 if compute_statistics else None
        total_word_length = 0 if compute_statistics else None

        for (
            local_word_to_index,
            local_counts,
            local_total,
            local_length,
        ) in chunk_results:
            # Always process word indices for summarization
            for word in local_word_to_index:
                if word not in word_to_index:
                    word_to_index[word] = current_index
                    current_index += 1

            # Only process statistics if needed
            if compute_statistics:
                word_counts.update(local_counts)
                total_words += local_total
                total_word_length += local_length

        # Create metrics with basic info even when statistics are disabled
        metrics = TextMetrics(
            word_count=total_words if compute_statistics else 0,
            sentence_count=len(sentences),
            unique_words=len(word_counts) if compute_statistics else 0,
            total_word_length=total_word_length if compute_statistics else 0,
            word_frequencies=word_counts if compute_statistics else Counter(),
            vocabulary_size=len(word_to_index),  # Always include vocabulary size
        )

        return ProcessedData(
            word_to_index=word_to_index,
            sentences=sentences,
            metrics=metrics,  # Always return metrics
            language=self.language,
        )
