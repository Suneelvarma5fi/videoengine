"""
Video Renderer — burns ASS subtitles into a video file using FFmpeg.

Uses the `subtitles` video filter (requires FFmpeg built with --enable-libass).
Hardcoded subtitles are permanently embedded in the output video pixels.
"""
import subprocess
from pathlib import Path


def check_libass() -> bool:
    """Return True if the installed FFmpeg supports libass."""
    result = subprocess.run(
        ["ffmpeg", "-filters"],
        capture_output=True,
        text=True,
    )
    return "subtitles" in result.stdout


def burn_subtitles(
    video_path: str | Path,
    ass_path: str | Path,
    output_path: str | Path,
    crf: int = 18,
    preset: str = "fast",
) -> Path:
    """
    Burn an ASS subtitle file into a video using FFmpeg.

    Args:
        video_path: Input video file (.mp4, .mov, etc.)
        ass_path: ASS subtitle file produced by ass_exporter
        output_path: Output video file path (.mp4)
        crf: H.264 CRF quality (0=lossless, 51=worst; 18 is visually near-lossless)
        preset: FFmpeg encoding speed preset (ultrafast … veryslow)

    Returns:
        Path to the output video file

    Raises:
        RuntimeError: If FFmpeg fails or libass is not available
    """
    video_path  = Path(video_path)
    ass_path    = Path(ass_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Input video not found: {video_path}")
    if not ass_path.exists():
        raise FileNotFoundError(f"ASS subtitle file not found: {ass_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # FFmpeg requires forward slashes and escaped colons on Windows;
    # on macOS/Linux just use the POSIX path. Escape special chars for filtergraph.
    ass_filter_path = str(ass_path).replace("\\", "/").replace(":", "\\:")

    cmd = [
        "ffmpeg",
        "-y",
        "-i", str(video_path),
        "-vf", f"subtitles={ass_filter_path}",
        "-c:v", "libx264",
        "-crf", str(crf),
        "-preset", preset,
        "-c:a", "copy",         # pass audio through unchanged
        str(output_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        stderr = result.stderr
        if "libass" in stderr.lower() or "no such filter" in stderr.lower():
            raise RuntimeError(
                "FFmpeg is missing libass support. "
                "Install FFmpeg with --enable-libass (e.g. `brew install ffmpeg`)."
            )
        raise RuntimeError(
            f"FFmpeg subtitle burn failed (code {result.returncode}):\n{stderr}"
        )

    return output_path
