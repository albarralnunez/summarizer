from pydantic import BaseModel, Field
from typing import List, Literal, Optional


class SummaryOutput(BaseModel):
    summary: List[str] = Field(..., description="Summary sentences from the file")
    method: Literal["default", "dask"] = Field(
        ..., description="Summarization method used"
    )
    processor: Optional[Literal["default", "dask"]] = Field(
        None, description="File processor used"
    )
    backend_processing_time: float = Field(
        ..., description="Time taken by the backend to process the request"
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "summary": [
                    "This is the first important sentence.",
                    "This is the second important sentence.",
                ],
                "method": "custom",
                "backend_processing_time": 0.5,
            }
        }
    }
