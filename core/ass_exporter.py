"""
ASS Exporter — converts SubtitleLayout → Advanced SubStation Alpha (.ass) file.

ASS format is natively supported by FFmpeg's libass filter, enabling:
  • Rich font styling (family, size, color)
  • Word-level karaoke timing via \\k tags
  • Position control (top / center / bottom)
  • Fade animations via \\fad()

Reference: http://www.aegisub.org/docs/manual/ass_file_format/
"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from subtitle_engine.models import SubtitleBlock, SubtitleLayout


# ---------------------------------------------------------------------------
# Color conversion helpers
# ---------------------------------------------------------------------------

def _hex_to_ass(hex_color: str, alpha: int = 0) -> str:
    """
    Convert #RRGGBB hex to ASS color format: &HAABBGGRR.

    ASS stores colors in BGR order with leading alpha byte.
    alpha=0 means fully opaque; alpha=255 means fully transparent.
    """
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"&H{alpha:02X}{b:02X}{g:02X}{r:02X}"


# ---------------------------------------------------------------------------
# Position mapping
# ---------------------------------------------------------------------------

# ASS Numpad alignment:  7 8 9
#                        4 5 6
#                        1 2 3
_POSITION_ALIGNMENT = {
    "top":    8,   # top-center
    "center": 5,   # screen center
    "bottom": 2,   # bottom-center
}


# ---------------------------------------------------------------------------
# Time formatting
# ---------------------------------------------------------------------------

def _fmt_time(seconds: float) -> str:
    """Format seconds as ASS timestamp: H:MM:SS.cc (centiseconds)."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    cs = round((s - int(s)) * 100)
    return f"{h}:{m:02d}:{int(s):02d}.{cs:02d}"


# ---------------------------------------------------------------------------
# Karaoke tag builder
# ---------------------------------------------------------------------------

def _karaoke_text(block: SubtitleBlock) -> str:
    """
    Build karaoke-tagged text for a SubtitleBlock.

    Uses \\k<centiseconds> for color-based karaoke (active word highlighted
    with SecondaryColour as it plays).
    For 'bold' mode: wraps active word with {\\b1}…{\\b0}.
    For 'scale' mode: uses \\K (fill karaoke).

    The renderer / playback engine handles which word is "active" — the \\k
    tags encode exact word durations so the highlight advances automatically.
    """
    mode = block.layout.highlight_mode
    parts = []

    for i, word in enumerate(block.words):
        # Duration in centiseconds
        duration_cs = max(1, round((word.end - word.start) * 100))
        text = word.text

        if mode == "bold":
            parts.append(f"{{\\k{duration_cs}}}{{\\b1}}{text}{{\\b0}} ")
        elif mode == "scale":
            # \\K is fill karaoke (highlights character-by-character fill)
            parts.append(f"{{\\K{duration_cs}}}{text} ")
        else:
            # Default: color karaoke
            parts.append(f"{{\\k{duration_cs}}}{text} ")

    return "".join(parts).rstrip()


# ---------------------------------------------------------------------------
# Main exporter
# ---------------------------------------------------------------------------

def export_ass(
    layout: SubtitleLayout,
    output_path: str | Path,
    video_width: int = 1080,
    video_height: int = 1920,
    font_path: Optional[str] = None,
) -> Path:
    """
    Write a SubtitleLayout to an ASS file.

    Args:
        layout: SubtitleLayout from subtitle_engine.process()
        output_path: Destination .ass file path
        video_width: Video width in pixels (for PlayResX)
        video_height: Video height in pixels (for PlayResY)
        font_path: Optional path to font file (not embedded; just for reference)

    Returns:
        Path to the written .ass file
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not layout.subtitles:
        raise ValueError("SubtitleLayout has no subtitle blocks to export")

    # Grab layout from first block (all blocks share the same layout in a template)
    bl = layout.subtitles[0].layout

    primary_color   = _hex_to_ass(bl.base_color)
    secondary_color = _hex_to_ass(bl.highlight_color)
    outline_color   = _hex_to_ass("#000000")
    back_color      = _hex_to_ass("#000000", alpha=180)  # semi-transparent shadow
    alignment       = _POSITION_ALIGNMENT.get(bl.position, 2)
    font_name       = bl.font_family

    lines: list[str] = []

    # ── Script Info ────────────────────────────────────────────────────────
    lines += [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        f"PlayResX: {video_width}",
        f"PlayResY: {video_height}",
        "ScaledBorderAndShadow: yes",
        "",
    ]

    # ── V4+ Styles ─────────────────────────────────────────────────────────
    lines += [
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        (
            f"Style: Default,{font_name},{bl.font_size},"
            f"{primary_color},{secondary_color},{outline_color},{back_color},"
            f"0,0,0,0,"          # Bold, Italic, Underline, StrikeOut
            f"100,100,0,0,"      # ScaleX, ScaleY, Spacing, Angle
            f"1,2,1,"            # BorderStyle, Outline, Shadow
            f"{alignment},"      # Alignment (numpad)
            f"10,10,20,"         # MarginL, MarginR, MarginV
            f"1"                 # Encoding (1 = default)
        ),
        "",
    ]

    # ── Events ────────────────────────────────────────────────────────────
    lines += [
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    for block in layout.subtitles:
        fade_in  = block.layout.transition_in_ms
        fade_out = block.layout.transition_out_ms
        start    = _fmt_time(block.start)
        end      = _fmt_time(block.end)
        text     = _karaoke_text(block)

        # \\fad(in_ms, out_ms) — fade the whole block in/out
        effect_tags = f"{{\\fad({fade_in},{fade_out})}}"

        lines.append(
            f"Dialogue: 0,{start},{end},Default,,0,0,0,,{effect_tags}{text}"
        )

    output_path.write_text("\n".join(lines), encoding="utf-8-sig")
    return output_path
