from dataclasses import dataclass
from typing import List, Tuple, Dict
from collections import Counter
from src.api.models import TextStatistics
from src.services.language import LanguageType, LanguageManager


@dataclass
class TextMetrics:
    """Container for text metrics"""

    word_count: int
    sentence_count: int
    unique_words: int
    total_word_length: int
    word_frequencies: Counter
    vocabulary_size: int

    def calculate_averages(self) -> Tuple[float, float]:
        """Calculate average word and sentence lengths"""
        avg_word_length = (
            self.total_word_length / self.word_count if self.word_count > 0 else 0
        )
        avg_sentence_length = (
            self.word_count / self.sentence_count if self.sentence_count > 0 else 0
        )
        return round(avg_word_length, 2), round(avg_sentence_length, 2)

    def get_most_common_words(
        self, language: LanguageType, n: int = 10
    ) -> List[Tuple[str, int]]:
        """Get most common words excluding stop words"""
        stop_words = LanguageManager.get_stop_words(language)
        content_words = {
            word: count
            for word, count in self.word_frequencies.items()
            if word not in stop_words
        }
        return sorted(content_words.items(), key=lambda x: (-x[1], x[0]))[:n]

    def to_statistics(
        self, language: LanguageType, word_scores: Dict[str, float] = None
    ) -> TextStatistics:
        """Convert metrics to TextStatistics model"""
        avg_word_length, avg_sentence_length = self.calculate_averages()
        most_common = self.get_most_common_words(language)

        top_scoring_words = []
        if word_scores:
            filtered_scores = {
                word: score
                for word, score in word_scores.items()
                if word not in LanguageManager.get_stop_words(language)
            }
            top_scoring_words = sorted(
                filtered_scores.items(), key=lambda x: (-x[1], x[0])
            )[:10]

        return TextStatistics(
            word_count=self.word_count,
            sentence_count=self.sentence_count,
            unique_words=self.unique_words,
            vocabulary_size=self.vocabulary_size,
            avg_word_length=avg_word_length,
            avg_sentence_length=avg_sentence_length,
            most_common_words=most_common,
            top_scoring_words=top_scoring_words,
        )
