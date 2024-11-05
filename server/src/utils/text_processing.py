import re
from nltk.tokenize import word_tokenize, sent_tokenize
from nltk.corpus import stopwords
from typing import List, Union

SENTENCE_SPLIT_PATTERN = re.compile(r"(?<!\w\.\w.)(?![A-Z][a-z]\.)(?<=\.|\?|\!)\s")
PREPROCESS_PATTERN = re.compile(r"[^\w\s]")
STOP_WORDS = set(stopwords.words("english"))


def preprocess_text(text):
    return PREPROCESS_PATTERN.sub("", text.lower())


def split_into_sentences(text: Union[str, List[str]]) -> List[str]:
    """
    Split text into sentences using both regex and NLTK for better accuracy.
    Handles both string and list inputs.
    """
    if isinstance(text, list):
        text = " ".join(str(item) for item in text)

    # Clean up extra whitespace
    text = re.sub(r"\s+", " ", text.strip())

    # First use NLTK's sentence tokenizer
    sentences = sent_tokenize(text)

    # Then split long sentences using regex
    final_sentences = []
    for sentence in sentences:
        # Split if sentence is too long (more than 200 characters)
        if len(sentence) > 200:
            splits = re.split(r"(?<=[.!?])\s+", sentence)
            final_sentences.extend([s.strip() for s in splits if s.strip()])
        else:
            final_sentences.append(sentence.strip())

    # Filter out invalid sentences
    return [
        s
        for s in final_sentences
        if (
            s
            and len(s) >= 10  # Minimum length - TODO:Make this configurable
            and any(c.isalpha() for c in s)  # Contains letters
            and s.strip(".-_,;:!? ").strip()  # Not just punctuation
        )
    ]


async def yield_sentences(text: str):
    for sentence in split_into_sentences(text):
        yield sentence
