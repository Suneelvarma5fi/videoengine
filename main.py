#!/usr/bin/env python3
"""
VideoEngine — entry point.

Usage:
    python main.py
    python main.py --host 0.0.0.0 --port 8080
"""
import argparse
import subprocess
import sys

import uvicorn

from api.app import app  # noqa: F401 — imported so uvicorn can find it


def _check_ffmpeg() -> None:
    """Ensure ffmpeg is installed and print a warning if libass is absent."""
    result = subprocess.run(
        ["ffmpeg", "-version"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print("ERROR: ffmpeg not found. Install it first (e.g. `brew install ffmpeg`).")
        sys.exit(1)

    # Non-fatal warning if libass is missing
    filter_check = subprocess.run(
        ["ffmpeg", "-filters"],
        capture_output=True,
        text=True,
    )
    if "subtitles" not in filter_check.stdout:
        print(
            "WARNING: your ffmpeg does not support the 'subtitles' filter (libass). "
            "Subtitle burning will fail at render time.\n"
            "Fix: brew install ffmpeg  (Homebrew build includes libass by default)"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="VideoEngine server")
    parser.add_argument("--host", default="127.0.0.1", help="Bind host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload for development")
    args = parser.parse_args()

    _check_ffmpeg()

    print(f"\n  VideoEngine running at http://{args.host}:{args.port}\n")

    uvicorn.run(
        "api.app:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
