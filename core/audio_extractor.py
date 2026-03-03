"""
Audio Extractor — pulls audio from a video file using FFmpeg.

Output: 16kHz mono WAV (WhisperX native format).
"""
import subprocess
from pathlib import Path


def extract_audio(video_path: str | Path, output_path: str | Path) -> Path:
    """
    Extract audio track from video using FFmpeg.

    Args:
        video_path: Path to input video (.mp4, .mov, etc.)
        output_path: Destination .wav file path

    Returns:
        Path to the written .wav file

    Raises:
        RuntimeError: If FFmpeg fails or video has no audio stream
    """
    video_path  = Path(video_path)
    output_path = Path(output_path)

    if not video_path.exists():
        raise FileNotFoundError(f"Video file not found: {video_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "ffmpeg",
        "-y",                   # overwrite without prompting
        "-i", str(video_path),
        "-vn",                  # drop video stream
        "-ar", "16000",         # 16kHz — WhisperX native sample rate
        "-ac", "1",             # mono
        "-f", "wav",
        str(output_path),
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        stderr = result.stderr
        if "no audio" in stderr.lower() or "does not contain any stream" in stderr.lower():
            raise RuntimeError(f"Video has no audio stream: {video_path}")
        raise RuntimeError(
            f"FFmpeg audio extraction failed (code {result.returncode}):\n{stderr}"
        )

    return output_path
