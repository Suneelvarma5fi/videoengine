# VideoEngine — Feature List

## Pipeline

- **Video upload** — drag-and-drop or file picker; supports `.mp4`, `.mov`, `.avi`, `.mkv`, `.webm`
- **Audio extraction** — FFmpeg strips the audio track from the uploaded video (`-vn`, 16kHz mono WAV)
- **Word-level transcription** — WhisperX (faster-whisper + forced alignment) produces per-word start/end timestamps and confidence scores
- **Subtitle block grouping** — words are grouped into readable blocks with configurable rules (max words, max duration, pause threshold, punctuation splits)
- **ASS subtitle export** — blocks are converted to Advanced SubStation Alpha format with karaoke `\k` timing tags and `\fad()` fade animations
- **Subtitle burn** — FFmpeg's `subtitles=` filter (libass) burns styled captions permanently into the video pixels
- **Video download** — final MP4 streamed directly to the browser

---

## Subtitle Templates

| Template | Position | Highlight mode | Words/block |
|---|---|---|---|
| `center_minimal_v1` | Center | Color karaoke | up to 8 |
| `bottom_classic_v1` | Bottom | Bold on active word | up to 10 |
| `kinetic_single_word_v1` | Center | Scale pop | 1 (kinetic) |

---

## Style Controls (UI)

- Template picker (dropdown)
- Base text color (color picker + hex input)
- Highlight / active-word color (color picker + hex input)
- Max words per block (slider, 1–12)
- Pause threshold — gap between words that forces a block split (slider)
- Max block duration (slider)

---

## API Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/api/upload` | Upload video, create job |
| `GET` | `/api/jobs/{id}` | Poll job status |
| `POST` | `/api/jobs/{id}/transcribe` | Start WhisperX pipeline |
| `GET` | `/api/jobs/{id}/transcript` | Fetch word-level JSON |
| `GET` | `/api/templates` | List available templates |
| `POST` | `/api/jobs/{id}/render` | Burn subtitles into video |
| `GET` | `/api/jobs/{id}/download` | Download final MP4 |
| `GET` | `/api/presets` | List saved user presets |
| `POST` | `/api/presets` | Save a preset |
| `DELETE` | `/api/presets/{name}` | Delete a preset |

---

## Job Status Flow

```
uploaded → extracting_audio → transcribing → transcribed
       → rendering_queued → building_subtitles → rendering → done
```

Any step can transition to `error` with a message.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | FastAPI + Uvicorn |
| Transcription | WhisperX (faster-whisper + ctranslate2) |
| Audio extraction | FFmpeg subprocess |
| Subtitle format | ASS (Advanced SubStation Alpha) |
| Subtitle rendering | FFmpeg libass filter |
| Frontend | Vanilla HTML / CSS / JS (no framework) |
| Storage | Local filesystem (jobs/, uploads/, presets/) |

---

## Known Constraints (V1)

- Transcription runs on **CPU only** (faster-whisper/ctranslate2 does not support Apple MPS)
- English language only (WhisperX alignment model is loaded for `en`)
- No authentication — single-user local tool
- Jobs and uploads are not automatically cleaned up
