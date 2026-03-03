"""
Block Generator — groups a flat word list into timed subtitle blocks.

Split conditions (evaluated per word after appending):

  Hard splits (always trigger, regardless of min_words):
    • word_count  >= max_words_per_block
    • block_duration >= max_duration_per_block
    • gap to next word >= pause_threshold
    • last word in list

  Soft splits (only when word_count >= min_words_per_block):
    • word ends with sentence-terminal punctuation  (. ! ?)
    • word ends with clause punctuation             (, ; :)

This separation gives cinematic pacing:
  — hard limits are guardrails,
  — soft limits follow natural speech rhythm.
"""
from __future__ import annotations

import re
from typing import List

from .models import BlockConfig, InputWord

# Punctuation patterns (strip trailing whitespace before matching)
_SENTENCE_END = re.compile(r'[.!?]["\')]?$')
_CLAUSE_END   = re.compile(r'[,;:]$')


def _ends_sentence(text: str) -> bool:
    return bool(_SENTENCE_END.search(text.strip()))


def _ends_clause(text: str) -> bool:
    return bool(_CLAUSE_END.search(text.strip()))


def generate_blocks(
    words: List[InputWord],
    config: BlockConfig,
) -> List[List[InputWord]]:
    """Return a list of word groups (each group becomes one SubtitleBlock)."""
    if not words:
        return []

    blocks: List[List[InputWord]] = []
    current: List[InputWord] = []

    for i, word in enumerate(words):
        current.append(word)

        is_last       = (i == len(words) - 1)
        next_word     = words[i + 1] if not is_last else None
        word_count    = len(current)
        block_duration = word.end - current[0].start

        # ── Hard split conditions ──────────────────────────────────────────
        gap = (next_word.start - word.end) if next_word else 0.0
        hard_split = (
            word_count    >= config.max_words_per_block
            or block_duration >= config.max_duration_per_block
            or gap            >= config.pause_threshold
            or is_last
        )

        # ── Soft split conditions ──────────────────────────────────────────
        soft_split = (
            config.split_on_punctuation
            and word_count >= config.min_words_per_block
            and (_ends_sentence(word.text) or _ends_clause(word.text))
        )

        if hard_split or soft_split:
            blocks.append(current)
            current = []

    # Safety flush — should not normally trigger due to `is_last` above
    if current:
        blocks.append(current)

    return blocks
