"""
ass_v2.py — per-word positioned ASS renderer with animation presets.

Architecture
────────────
For every SubtitleBlock we emit TWO sets of dialogue lines:

  Layer 0 — base (dim) layer
      One line per word, covering the FULL BLOCK duration.
      Word is shown at a darkened version of base_color so all words
      in the block are visible but clearly inactive.

  Layer 1 — active overlay
      One line per word, covering only THAT WORD'S own time window.
      The chosen animation preset controls scale, color, and motion.

Because Layer 1 is drawn on top of Layer 0, the active word's bright
overlay completely replaces the dim base word visually.

Presets
───────
  word_pop       Active word scales 115 → 100% with highlight color.
  karaoke_fill   Smooth color transition base → highlight over 80 ms.
  pill_highlight Colored thick border (pill outline) on active word.
  fade_words     Inactive words very faint; active word fades in.
  bounce_in      Active word overshoots to 128% then settles at 100%.

Usage
─────
  from renderers.ass_v2 import export_ass_v2, PRESET_NAMES
  export_ass_v2(layout, "out.ass", preset="word_pop")
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from subtitle_engine.models import SubtitleLayout
from renderers.text_layout import layout_block, WordPosition


# ---------------------------------------------------------------------------
# Public preset list
# ---------------------------------------------------------------------------

PRESET_NAMES: tuple[str, ...] = (
    "word_pop",
    "karaoke_fill",
    "pill_highlight",
    "fade_words",
    "bounce_in",
)


# ---------------------------------------------------------------------------
# Color helpers
# ---------------------------------------------------------------------------

def _hex_to_ass(hex_color: str, alpha: int = 0) -> str:
    """#RRGGBB → &HAABBGGRR (ASS stores color in BGR order with alpha prefix)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


def _dim_hex(hex_color: str, factor: float = 0.40) -> str:
    """Darken a hex color (factor 0.0 = black, 1.0 = original)."""
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"#{int(r * factor):02X}{int(g * factor):02X}{int(b * factor):02X}"


# ---------------------------------------------------------------------------
# Time formatter
# ---------------------------------------------------------------------------

def _fmt_time(sec: float) -> str:
    """Float seconds → ASS timestamp H:MM:SS.cc"""
    h  = int(sec // 3600)
    m  = int((sec % 3600) // 60)
    s  = sec % 60
    cs = round((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


# ---------------------------------------------------------------------------
# Base-layer tag builder
# ---------------------------------------------------------------------------

def _base_tag(p: WordPosition, dim_ass: str, preset: str) -> str:
    """
    Inline tags for the always-visible dim base word.

    fade_words uses near-invisible alpha so inactive words nearly disappear,
    giving a spotlight feel.  All other presets use a moderately dim alpha
    so the audience can still read the upcoming words.
    """
    alpha = "&HCC&" if preset == "fade_words" else "&H70&"
    return (
        f"{{\\an5\\pos({p.cx:.1f},{p.cy:.1f})"
        f"\\1c{dim_ass}\\alpha{alpha}}}"
    )


# ---------------------------------------------------------------------------
# Active-overlay tag builders (one per preset)
# ---------------------------------------------------------------------------

def _tags_word_pop(p: WordPosition, hi: str) -> str:
    """Scales from 115% to 100% while showing highlight color."""
    return (
        f"{{\\an5\\pos({p.cx:.1f},{p.cy:.1f})"
        f"\\1c{hi}"
        f"\\fscx115\\fscy115"
        f"\\t(0,150,\\fscx100\\fscy100)}}"
    )


def _tags_karaoke_fill(p: WordPosition, base: str, hi: str) -> str:
    """Color cross-fades from base → highlight over 80 ms, then fades out."""
    return (
        f"{{\\an5\\pos({p.cx:.1f},{p.cy:.1f})"
        f"\\1c{base}"
        f"\\t(0,80,\\1c{hi})"
        f"\\fad(0,60)}}"
    )


def _tags_pill_highlight(p: WordPosition, base: str, hi: str) -> str:
    """Colored thick border frames the active word like a pill."""
    return (
        f"{{\\an5\\pos({p.cx:.1f},{p.cy:.1f})"
        f"\\1c{base}"
        f"\\3c{hi}"
        f"\\bord8\\shad0}}"
    )


def _tags_fade_words(p: WordPosition, base: str) -> str:
    """Active word fades in from invisible to full brightness."""
    return (
        f"{{\\an5\\pos({p.cx:.1f},{p.cy:.1f})"
        f"\\1c{base}"
        f"\\fad(120,60)}}"
    )


def _tags_bounce_in(p: WordPosition, hi: str) -> str:
    """Overshoots to 128% scale → snaps back through 93% → settles at 100%."""
    return (
        f"{{\\an5\\pos({p.cx:.1f},{p.cy:.1f})"
        f"\\1c{hi}"
        f"\\fscx128\\fscy128"
        f"\\t(0,100,\\fscx93\\fscy93)"
        f"\\t(100,220,\\fscx100\\fscy100)}}"
    )


def _active_tag(p: WordPosition, preset: str, base_ass: str, hi_ass: str) -> str:
    if preset == "word_pop":
        return _tags_word_pop(p, hi_ass)
    if preset == "karaoke_fill":
        return _tags_karaoke_fill(p, base_ass, hi_ass)
    if preset == "pill_highlight":
        return _tags_pill_highlight(p, base_ass, hi_ass)
    if preset == "fade_words":
        return _tags_fade_words(p, base_ass)
    # bounce_in (default fallback)
    return _tags_bounce_in(p, hi_ass)


# ---------------------------------------------------------------------------
# Main exporter
# ---------------------------------------------------------------------------

def export_ass_v2(
    layout: SubtitleLayout,
    output_path: str | Path,
    preset: str = "word_pop",
    video_width: int = 1080,
    video_height: int = 1920,
    base_color: Optional[str] = None,
    highlight_color: Optional[str] = None,
) -> Path:
    """
    Write a per-word positioned .ass file with the chosen animation preset.

    Args:
        layout:          SubtitleLayout from subtitle_engine.process()
        output_path:     Destination .ass file path
        preset:          Animation preset name (see PRESET_NAMES)
        video_width:     Video width in pixels (PlayResX)
        video_height:    Video height in pixels (PlayResY)
        base_color:      Override base text color (#RRGGBB); uses template default if None
        highlight_color: Override highlight color (#RRGGBB); uses template default if None

    Returns:
        Path to the written .ass file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not layout.subtitles:
        raise ValueError("SubtitleLayout has no subtitle blocks to export")

    if preset not in PRESET_NAMES:
        preset = "word_pop"

    bl = layout.subtitles[0].layout

    # Resolve colors (UI overrides take priority over template defaults)
    base_hex = base_color      or bl.base_color
    hi_hex   = highlight_color or bl.highlight_color

    base_ass = _hex_to_ass(base_hex)
    hi_ass   = _hex_to_ass(hi_hex)
    dim_ass  = _hex_to_ass(_dim_hex(base_hex))
    out_ass  = _hex_to_ass("#000000")
    back_ass = _hex_to_ass("#000000", alpha=200)

    lines: list[str] = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 2",            # no auto-wrapping — we control all positions
        f"PlayResX: {video_width}",
        f"PlayResY: {video_height}",
        "ScaledBorderAndShadow: yes",
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            f"Style: Word,{bl.font_family},{bl.font_size},"
            f"{base_ass},{hi_ass},{out_ass},{back_ass},"
            f"0,0,0,0,"        # Bold Italic Underline StrikeOut
            f"100,100,0,0,"    # ScaleX ScaleY Spacing Angle
            f"1,2,1,"          # BorderStyle Outline Shadow
            f"5,"              # Alignment = 5 (center; overridden per-line with \an5)
            f"0,0,0,"          # MarginL MarginR MarginV
            f"1"               # Encoding
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for block in layout.subtitles:
        b_start = _fmt_time(block.start)
        b_end   = _fmt_time(block.end)
        positions = layout_block(block, video_width, video_height)

        for pos in positions:
            # ── Layer 0: dim base word, entire block duration ─────────────────
            base_tag = _base_tag(pos, dim_ass, preset)
            lines.append(
                f"Dialogue: 0,{b_start},{b_end},"
                f"Word,,0,0,0,,{base_tag}{pos.text}"
            )

            # ── Layer 1: animated active word, word's own time window ─────────
            w_start = _fmt_time(pos.start)
            w_end   = _fmt_time(pos.end)
            act_tag = _active_tag(pos, preset, base_ass, hi_ass)
            lines.append(
                f"Dialogue: 1,{w_start},{w_end},"
                f"Word,,0,0,0,,{act_tag}{pos.text}"
            )

    output_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return output_path
