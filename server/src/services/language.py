from typing import Set, Dict, Literal
from nltk.corpus import stopwords

LanguageType = Literal["english", "spanish"]

class LanguageManager:
    """Manages language-specific operations and resources"""
    
    _stop_words: Dict[str, Set[str]] = {
        "english": set(stopwords.words("english")),
        "spanish": set(stopwords.words("spanish"))
    }
    
    @classmethod
    def get_stop_words(cls, language: LanguageType) -> Set[str]:
        """Get stop words for specified language"""
        if language not in cls._stop_words:
            raise ValueError(f"Unsupported language: {language}")
        return cls._stop_words[language]
    
    @classmethod
    def is_supported(cls, language: str) -> bool:
        """Check if language is supported"""
        return language in cls._stop_words
    
    @classmethod
    def validate_language(cls, language: str) -> None:
        """Validate language support"""
        if not cls.is_supported(language):
            raise ValueError(f"Unsupported language: {language}") 