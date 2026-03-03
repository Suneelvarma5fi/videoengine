"""
Highlight Engine — assigns per-word style state within a block.

Responsibilities:
  • Mark low-confidence words with "low_confidence" style (optional faded rendering)
  • For kinetic_single_word templates (max_words == 1), mark the word as "highlight"
    since there is no "currently playing" concept — the word IS the active moment.
  • All other words default to "normal"; the renderer applies live highlighting
    at playback time using word.start / word.end vs current_time.

Style values:
  "normal"         → renderer applies base styling
  "highlight"      → pre-marked active (e.g. kinetic single-word mode)
  "low_confidence" → renderer applies muted/faded styling
"""
from __future__ import annotations

from typing import List

from .models import InputWord, StyledWord, TemplateConfig

_LOW_CONFIDENCE_THRESHOLD = 0.6


def apply_word_styles(
    words: List[InputWord],
    template: TemplateConfig,
    *,
    is_single_word_block: bool = False,
) -> List[StyledWord]:
    """
    Return StyledWord list for a block's words.

    Args:
        words: The words in this block (from block_generator output).
        template: Active TemplateConfig (determines highlight rules).
        is_single_word_block: True when the template uses one-word-per-block
            (kinetic_single_word style) — marks the lone word as "highlight".
    """
    styled: List[StyledWord] = []

    for word in words:
        style = _resolve_style(word, template, is_single_word_block)
        styled.append(
            StyledWord(
                text=word.text,
                start=word.start,
                end=word.end,
                style=style,
                confidence=word.confidence,
            )
        )

    return styled


def _resolve_style(
    word: InputWord,
    template: TemplateConfig,
    is_single_word_block: bool,
) -> str:
    # Low-confidence words take priority — renderer should fade/mute them.
    if (
        word.confidence is not None
        and word.confidence < _LOW_CONFIDENCE_THRESHOLD
    ):
        return "low_confidence"

    # Single-word blocks are always "active" — the whole block IS one word.
    if is_single_word_block:
        return "highlight"

    return "normal"
