"""
Data models for the Subtitle Styling & Rendering Engine.

Flow: InputWord → SubtitleBlock → SubtitleLayout (consumed by renderer)
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

@dataclass
class InputWord:
    """A single word with deterministic timing from WhisperX."""
    text: str
    start: float
    end: float
    duration: float
    confidence: Optional[float] = None


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class BlockConfig:
    """Rules for grouping words into subtitle blocks."""
    min_words_per_block: int = 3
    max_words_per_block: int = 8
    max_duration_per_block: float = 4.0
    split_on_punctuation: bool = True
    pause_threshold: float = 0.5   # seconds gap between words triggers split


@dataclass
class HighlightConfig:
    """Animation/style config for the active word."""
    # Supported modes:
    #   color | bold | italic | scale | underline | pill | opacity | tracking
    mode: str = "color"
    transition_in_ms: int = 80
    transition_out_ms: int = 80


@dataclass
class TemplateConfig:
    """Full template definition — layout + typography + highlight rules."""
    name: str
    position: str = "center"          # center | bottom | top
    alignment: str = "center"         # left | center | right
    max_lines: int = 2
    font_family: str = "Inter"
    font_size: int = 64
    base_color: str = "#000000"
    background_color: str = "#FFFFFF"
    highlight_color: str = "#FF0000"
    highlight_style: str = "color"    # mirrors highlight.mode, kept for top-level readability
    highlight: HighlightConfig = field(default_factory=HighlightConfig)
    block_config: BlockConfig = field(default_factory=BlockConfig)


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

@dataclass
class StyledWord:
    """A word annotated with its timing window and default style state."""
    text: str
    start: float
    end: float
    # "normal"         → rendered at base style
    # "highlight"      → pre-marked active (used for single-word templates)
    # "low_confidence" → faded / muted styling
    style: str = "normal"
    confidence: Optional[float] = None


@dataclass
class BlockLayout:
    """Resolved layout metadata for a subtitle block (from template)."""
    position: str
    alignment: str
    font_family: str
    font_size: int
    base_color: str
    background_color: str
    highlight_color: str
    highlight_mode: str
    transition_in_ms: int
    transition_out_ms: int
    max_lines: int


@dataclass
class SubtitleBlock:
    """One subtitle block — a timed group of styled words with layout."""
    block_id: int
    start: float
    end: float
    text: str                    # joined plain text (for quick preview/SRT)
    words: List[StyledWord]
    layout: BlockLayout


@dataclass
class SubtitleLayout:
    """Final output consumed by the renderer."""
    template: str
    subtitles: List[SubtitleBlock]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)
