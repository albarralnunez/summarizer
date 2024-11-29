from pydantic import BaseModel
from typing import List, Optional, Tuple, NamedTuple


class TokenizedSentence(NamedTuple):
    original: str
    tokens: List[str]


class MemoryDetail(BaseModel):
    file: str
    line: int
    size: float
    count: int


class FunctionProfile(BaseModel):
    function_name: str
    total_time: float
    total_exec_time: float
    percentage: float
    calls: int
    memory_per_call: float


class ProfilingData(BaseModel):
    functions: List[FunctionProfile]
    memory_usage: float
    memory_peak: float
    memory_details: List[MemoryDetail]


class TextStatistics(BaseModel):
    word_count: int
    sentence_count: int
    unique_words: int
    avg_sentence_length: float
    most_common_words: List[Tuple[str, int]]
    top_scoring_words: List[Tuple[str, float]]
    vocabulary_size: int


class SummaryOutput(BaseModel):
    summary: List[str]
    method: str
    processor: str
    backend_processing_time: float
    compute_statistics: bool
    profiling_data: Optional[ProfilingData] = None
    text_statistics: Optional[TextStatistics] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "summary": [
                    "This is the first important sentence.",
                    "This is another key point.",
                ],
                "method": "custom",
                "backend_processing_time": 0.5,
            }
        }
    }
