"""
Subtitle Engine — main orchestrator.

Pipeline:
    InputWord list
        → BlockGenerator      (word grouping)
        → TemplateResolver    (layout metadata)
        → HighlightEngine     (per-word style)
        → SubtitleLayout      (renderer-ready JSON)
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .block_generator import generate_blocks
from .highlight_engine import apply_word_styles
from .models import InputWord, SubtitleBlock, SubtitleLayout
from .template_resolver import load_template, resolve_layout


def process(
    words: List[InputWord],
    template_name: str = "center_minimal_v1",
    block_config_override: Optional[Dict[str, Any]] = None,
    templates_dir: Optional[str] = None,
) -> SubtitleLayout:
    """
    Run the full subtitle pipeline.

    Args:
        words: Flat list of InputWord from WhisperX JSON.
        template_name: Name of the template file (no .json extension).
        block_config_override: Optional dict to override specific BlockConfig
            fields, e.g. {"max_words_per_block": 5, "pause_threshold": 0.4}.
        templates_dir: Optional path to templates directory (for testing).

    Returns:
        SubtitleLayout ready for JSON export and renderer consumption.
    """
    # ── 1. Load template ──────────────────────────────────────────────────
    template = load_template(template_name, templates_dir=templates_dir)

    # Apply any runtime overrides to block grouping config
    if block_config_override:
        for key, value in block_config_override.items():
            if hasattr(template.block_config, key):
                setattr(template.block_config, key, value)

    # ── 2. Group words into blocks ────────────────────────────────────────
    word_groups = generate_blocks(words, template.block_config)

    # Is this a single-word-per-block template?
    is_kinetic = template.block_config.max_words_per_block == 1

    # ── 3. Resolve shared layout (same for all blocks in a template) ──────
    layout = resolve_layout(template)

    # ── 4. Build SubtitleBlocks ───────────────────────────────────────────
    subtitle_blocks: List[SubtitleBlock] = []

    for i, group in enumerate(word_groups):
        styled_words = apply_word_styles(
            group,
            template,
            is_single_word_block=is_kinetic,
        )

        subtitle_blocks.append(
            SubtitleBlock(
                block_id=i + 1,
                start=group[0].start,
                end=group[-1].end,
                text=" ".join(w.text for w in group),
                words=styled_words,
                layout=layout,
            )
        )

    # ── 5. Assemble final layout ──────────────────────────────────────────
    total_words = sum(len(b.words) for b in subtitle_blocks)
    duration    = subtitle_blocks[-1].end if subtitle_blocks else 0.0

    return SubtitleLayout(
        template=template_name,
        subtitles=subtitle_blocks,
        metadata={
            "total_blocks": len(subtitle_blocks),
            "total_words": total_words,
            "duration": round(duration, 3),
        },
    )
