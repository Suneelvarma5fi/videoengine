# VideoEngine — Phased Roadmap

---

## Phase 1 — Output Quality (NOW)
> Goal: make the rendered subtitles look premium before anything else ships.

The current renderer uses basic ASS `\k` karaoke — one color change per word, no motion,
no entrance, no depth. This phase replaces it with a per-word positioned renderer.

### What changes
- Each word gets its own ASS dialogue line, positioned absolutely with `\pos(x,y)`
- Words outside the active window are visible but dimmed (base layer)
- The active word gets its own overlay with animation for its exact time window
- `\t()` transform tags animate scale, alpha, and color per word
- Multiple named animation presets — switchable at render time

### Animation presets
| Preset | Effect |
|---|---|
| `word_pop` | Active word scales 115%→100% with highlight color, others dimmed |
| `karaoke_fill` | Smooth left-to-right color fill (upgraded `\kf`) |
| `pill_highlight` | Active word gets a colored border box (pill-style) |
| `fade_words` | Each word fades in at full brightness when active |
| `bounce_in` | Each word overshoots to 125% then settles to 100% |

### How it works (architecture)
```
SubtitleLayout
    │
    ▼
renderers/text_layout.py     — PIL font metrics, word x/y positions
    │
    ▼
renderers/ass_v2.py          — per-word dialogue lines with \pos + \t() animations
    │
    ▼
FFmpeg subtitles= filter     — burns into video (unchanged)
```

### Deliverables
- `renderers/text_layout.py`
- `renderers/ass_v2.py`
- Preset selector in render API (`preset` field on POST /api/jobs/{id}/render)
- UI dropdown to pick preset

---

## Phase 2 — Platform Foundation
> Goal: turn the local tool into a callable API.

- Versioned routes (`/v1/`)
- API key auth (`Authorization: Bearer ve_live_xxx`)
- Postgres replaces `status.json` files (jobs, keys, users)
- Job queue (asyncio or Celery) for concurrent processing

---

## Phase 3 — Google Drive Integration
> Goal: let users connect their video library without uploading manually.

- **Mode A — shared link**: paste a public Drive folder URL, VideoEngine lists + pulls videos
- **Mode B — OAuth**: sign in with Google, access private folders, write output back to Drive
- `/v1/sources` API to manage connected Drive folders

---

## Phase 4 — Full Platform
> Goal: webhooks, multi-user workspaces, usage billing.

- Webhooks for async job completion events
- Team workspaces (shared templates + presets)
- Multi-language support (WhisperX 90+ languages)
- Batch processing (subtitle an entire Drive folder in one job)
- Custom font upload
- Usage-based billing (processing minutes per API key)
