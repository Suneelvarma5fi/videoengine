"""
text_layout.py — word position calculator for per-word ASS rendering.

Given a SubtitleBlock and video dimensions, calculates the absolute pixel
center (cx, cy) for each word using proportional font width estimation.

No font files are required — widths are estimated mathematically for a
medium-weight sans-serif font, which is accurate enough for libass rendering
(libass uses the actual installed font; our estimates just need to be close
enough to space words out sensibly).
"""
from __future__ import annotations

from dataclasses import dataclass

from subtitle_engine.models import SubtitleBlock


@dataclass
class WordPosition:
    """Absolute screen position for one word (uses \an5 center anchor)."""
    text: str
    start: float
    end: float
    cx: float      # center-x in pixels
    cy: float      # center-y in pixels
    width: float   # estimated pixel width
    height: float  # estimated pixel height (~= font_size)


# ---------------------------------------------------------------------------
# Character width estimation
# Approximate widths relative to font_size for a medium-weight sans-serif font.
# ---------------------------------------------------------------------------

_NARROW = frozenset("iIlf!|.,;:'\"()[]{}/ \t")
_WIDE   = frozenset("mwWMQ")


def _char_width(ch: str, font_size: int) -> float:
    if ch in _NARROW:
        return font_size * 0.28
    if ch in _WIDE:
        return font_size * 0.72
    return font_size * 0.55


def estimate_width(text: str, font_size: int) -> float:
    """Approximate pixel width of text rendered at font_size in a sans-serif font."""
    return sum(_char_width(ch, font_size) for ch in text)


# ---------------------------------------------------------------------------
# Block layout
# ---------------------------------------------------------------------------

def layout_block(
    block: SubtitleBlock,
    video_width: int,
    video_height: int,
) -> list[WordPosition]:
    """
    Return a WordPosition list for every word in the block.

    Words are wrapped into lines (capped at 85% of video width) and each
    line is centered horizontally.  Vertical position is controlled by
    block.layout.position: "top" / "center" / "bottom".
    """
    bl        = block.layout
    font_size = bl.font_size
    line_h    = font_size * 1.30           # vertical gap between line centers
    space_w   = estimate_width(" ", font_size)
    max_line_w = video_width * 0.85        # usable width (7.5% padding each side)

    # ── Y anchor for the block ──────────────────────────────────────────────
    if bl.position == "top":
        y_anchor = video_height * 0.15
    elif bl.position == "center":
        y_anchor = video_height * 0.50
    else:                                  # bottom
        y_anchor = video_height * 0.82

    # ── Wrap words into display lines ───────────────────────────────────────
    lines: list[list[tuple]] = []          # list[list[(StyledWord, width)]]
    current: list[tuple] = []
    current_w = 0.0

    for word in block.words:
        w   = estimate_width(word.text, font_size)
        gap = space_w if current else 0.0
        if current and (current_w + gap + w) > max_line_w:
            lines.append(current)
            current   = [(word, w)]
            current_w = w
        else:
            current.append((word, w))
            current_w += gap + w

    if current:
        lines.append(current)

    # ── Center block vertically around y_anchor ─────────────────────────────
    n_lines  = len(lines)
    total_h  = n_lines * line_h
    first_cy = y_anchor - total_h / 2 + line_h / 2

    # ── Assign absolute positions ────────────────────────────────────────────
    positions: list[WordPosition] = []
    for li, line in enumerate(lines):
        cy = first_cy + li * line_h

        # Center the line horizontally
        line_w  = sum(w for _, w in line) + space_w * max(len(line) - 1, 0)
        start_x = (video_width - line_w) / 2

        cursor = start_x
        for word, w in line:
            cx = cursor + w / 2
            positions.append(
                WordPosition(
                    text=word.text,
                    start=word.start,
                    end=word.end,
                    cx=cx,
                    cy=cy,
                    width=w,
                    height=float(font_size),
                )
            )
            cursor += w + space_w

    return positions
