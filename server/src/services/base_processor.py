from abc import ABC, abstractmethod
from typing import List, Dict, Counter
from src.services.language import LanguageType, LanguageManager
from src.utils.text_processing import word_tokenize

class BaseTextProcessor(ABC):
    """Base class for text processing operations"""
    
    def __init__(self, language: LanguageType):
        LanguageManager.validate_language(language)
        self.language = language
        self.stop_words = LanguageManager.get_stop_words(language)
    
    def filter_words(self, words: List[str]) -> List[str]:
        """Filter and clean words based on common criteria"""
        return [
            word for word in words 
            if (word.isalnum() and 
                word not in self.stop_words and 
                len(word) > 2)
        ]
    
    def tokenize_sentence(self, sentence: str) -> List[str]:
        """Tokenize and clean a sentence"""
        words = word_tokenize(sentence.lower(), self.language)
        return self.filter_words(words)
    
    def process_sentence(self, sentence: str) -> Dict[str, int]:
        """Process a single sentence and return word frequencies"""
        words = self.tokenize_sentence(sentence)
        return Counter(words)
    
    @abstractmethod
    async def process_text(self, sentences: List[str]):
        """Process text and return relevant data"""
        pass 