"""
Configuration for the WhisperX transcription pipeline.
"""
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class WhisperConfig:
    """WhisperX model configuration."""
    model_size: str = "medium"
    language: str = "en"
    device: str = "cpu"
    compute_type: str = "float32"
    batch_size: int = 16

    @property
    def model_name(self) -> str:
        return f"whisperx-{self.model_size}"


@dataclass
class ProcessingConfig:
    """Audio processing constraints."""
    supported_formats: tuple = (".wav", ".mp3")
    max_duration_seconds: int = 3600
    min_confidence_threshold: float = 0.5
    alignment_retries: int = 2

    def validate_format(self, filepath: Path) -> bool:
        return filepath.suffix.lower() in self.supported_formats


@dataclass
class OutputConfig:
    """Output formatting configuration."""
    output_dir: Path = field(default_factory=lambda: Path("output"))
    json_indent: int = 2
    flag_low_confidence: bool = True
    timestamp_precision: int = 3

    def ensure_output_dir(self) -> None:
        self.output_dir.mkdir(parents=True, exist_ok=True)


@dataclass
class ExtractorConfig:
    """Master configuration combining all sub-configs."""
    whisper: WhisperConfig = field(default_factory=WhisperConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    output: OutputConfig = field(default_factory=OutputConfig)

    @classmethod
    def default(cls) -> "ExtractorConfig":
        # WhisperX uses faster-whisper (ctranslate2) which only supports cpu/cuda.
        # MPS is not supported by ctranslate2, so always use cpu on Apple Silicon.
        return cls(
            whisper=WhisperConfig(
                model_size="medium",
                device="cpu",
                compute_type="float32",
            ),
            processing=ProcessingConfig(max_duration_seconds=1800),
            output=OutputConfig(),
        )

    @classmethod
    def cpu_fallback(cls) -> "ExtractorConfig":
        return cls(
            whisper=WhisperConfig(
                model_size="small",
                device="cpu",
                compute_type="float32",
            ),
        )
