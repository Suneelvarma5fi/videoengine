"""
Pydantic models for structured transcription output.

Defines the schema for word-level transcription data from WhisperX.
"""
from typing import List, Optional
from pydantic import BaseModel, Field, computed_field


class WordSegment(BaseModel):
    """Individual word with timing and confidence data."""

    id: int = Field(..., description="Sequential word index (1-based)")
    text: str = Field(..., description="Cleaned word string")
    start: float = Field(..., ge=0, description="Word start time in seconds")
    end: float = Field(..., ge=0, description="Word end time in seconds")
    confidence: float = Field(..., ge=0, le=1, description="Model confidence score (0-1)")

    @computed_field
    @property
    def duration(self) -> float:
        """Computed duration in seconds."""
        return round(self.end - self.start, 3)

    def is_low_confidence(self, threshold: float = 0.5) -> bool:
        return self.confidence < threshold


class TranscriptMetadata(BaseModel):
    """Metadata about the transcription process."""

    duration: float
    language: str = "en"
    model: str
    word_count: int
    source_file: Optional[str] = None
    processing_time: Optional[float] = None
    avg_confidence: Optional[float] = None
    low_confidence_count: Optional[int] = None


class TranscriptOutput(BaseModel):
    """Complete transcription output with metadata and word segments."""

    metadata: TranscriptMetadata
    words: List[WordSegment]

    def get_text(self, separator: str = " ") -> str:
        return separator.join(word.text for word in self.words)

    def to_json(self, indent: int = 2) -> str:
        return self.model_dump_json(indent=indent)
