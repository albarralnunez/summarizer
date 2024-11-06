from typing import Literal, List, NamedTuple

LanguageType = Literal["english", "spanish"]

class TokenizedSentence(NamedTuple):
    original: str
    tokens: List[str] 