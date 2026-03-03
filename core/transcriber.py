"""
Transcriber — WhisperX word-level transcription pipeline.

Adapted from audio-to-transcript/src/extractor.py.
Takes a .wav audio file, returns TranscriptOutput with word-level timestamps.
"""
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import torch
import whisperx

from transcriber_models.models import TranscriptMetadata, TranscriptOutput, WordSegment
from transcriber_models.config import ExtractorConfig

logger = logging.getLogger(__name__)


class Transcriber:
    """
    Word-level transcription using WhisperX.

    Pipeline:
        1. Load audio
        2. Run Whisper ASR
        3. Run forced alignment
        4. Extract word_segments
        5. Normalize to TranscriptOutput schema
    """

    def __init__(self, config: Optional[ExtractorConfig] = None):
        self.config = config or ExtractorConfig.default()
        self._model = None
        self._align_model = None
        self._align_metadata = None
        self._validate_device()

    def _validate_device(self) -> None:
        device = self.config.whisper.device
        if device == "mps" and not torch.backends.mps.is_available():
            logger.warning("MPS not available, falling back to CPU")
            self.config.whisper.device = "cpu"
        elif device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA not available, falling back to CPU")
            self.config.whisper.device = "cpu"

    def _load_model(self) -> None:
        if self._model is not None:
            return
        cfg = self.config.whisper
        logger.info(f"Loading WhisperX model: {cfg.model_size} on {cfg.device}")
        self._model = whisperx.load_model(
            cfg.model_size,
            device=cfg.device,
            compute_type=cfg.compute_type,
            language=cfg.language,
        )

    def _load_alignment_model(self) -> None:
        if self._align_model is not None:
            return
        logger.info("Loading alignment model")
        self._align_model, self._align_metadata = whisperx.load_align_model(
            language_code=self.config.whisper.language,
            device=self.config.whisper.device,
        )

    def transcribe(self, audio_path: str | Path) -> TranscriptOutput:
        """
        Full transcription pipeline for a .wav file.

        Args:
            audio_path: Path to 16kHz mono WAV file

        Returns:
            TranscriptOutput with word-level timing data
        """
        start_time = time.time()
        audio_path = Path(audio_path)

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        if not self.config.processing.validate_format(audio_path):
            raise ValueError(
                f"Unsupported format: {audio_path.suffix}. "
                f"Supported: {self.config.processing.supported_formats}"
            )

        # Load audio
        logger.info(f"Loading audio: {audio_path}")
        audio = whisperx.load_audio(str(audio_path))
        audio_duration = len(audio) / 16000

        max_dur = self.config.processing.max_duration_seconds
        if audio_duration > max_dur:
            raise ValueError(
                f"Audio duration ({audio_duration:.1f}s) exceeds maximum ({max_dur}s)"
            )

        # ASR
        self._load_model()
        logger.info("Running transcription...")
        result = self._model.transcribe(
            audio,
            batch_size=self.config.whisper.batch_size,
            language=self.config.whisper.language,
        )

        self._load_alignment_model()
        logger.info("Running forced alignment...")
        aligned = whisperx.align(
            result["segments"],
            self._align_model,
            self._align_metadata,
            audio,
            device=self.config.whisper.device,
            return_char_alignments=False,
        )

        # Extract words
        precision = self.config.output.timestamp_precision
        words = self._extract_words(aligned, precision)

        processing_time = time.time() - start_time
        threshold = self.config.processing.min_confidence_threshold
        avg_conf = sum(w.confidence for w in words) / len(words) if words else 0.0

        metadata = TranscriptMetadata(
            duration=round(audio_duration, 3),
            language=self.config.whisper.language,
            model=self.config.whisper.model_name,
            word_count=len(words),
            source_file=audio_path.name,
            processing_time=round(processing_time, 2),
            avg_confidence=round(avg_conf, 3),
            low_confidence_count=sum(1 for w in words if w.is_low_confidence(threshold)),
        )

        logger.info(
            f"Transcription done: {len(words)} words in {processing_time:.2f}s"
        )
        return TranscriptOutput(metadata=metadata, words=words)

    def _extract_words(
        self, aligned_result: Dict[str, Any], precision: int
    ) -> List[WordSegment]:
        word_segments = aligned_result.get("word_segments", [])

        if not word_segments:
            for segment in aligned_result.get("segments", []):
                word_segments.extend(segment.get("words", []))

        words = []
        word_id = 1
        for w in word_segments:
            if "start" not in w or "end" not in w:
                continue
            text = w.get("word", "").strip()
            if not text:
                continue
            words.append(
                WordSegment(
                    id=word_id,
                    text=text,
                    start=round(w["start"], precision),
                    end=round(w["end"], precision),
                    confidence=round(w.get("score", 0.0), precision),
                )
            )
            word_id += 1

        return words
