# VideoEngine — Product Roadmap

---

## Current (V1) — Local Tool

Single-user, local server. Upload a video, apply subtitles, download.
No auth, no external storage, no API access for third parties.

---

## V2 — API-First Platform + Google Drive Integration

### The product shift

V1 is a tool. V2 is a platform. The distinction:
- A **tool** is used directly by one person in a UI.
- A **platform** exposes APIs so other apps, scripts, and automations can use it.

Anyone with an API key should be able to call VideoEngine programmatically —
no UI required.

---

### Google Drive Integration

#### Two connection modes

| Mode | How | Use case |
|---|---|---|
| **OAuth (private folder)** | User signs in with Google, grants Drive read access | Personal or team folders, restricted content |
| **Shared folder link** | User pastes a public Drive folder URL | Easy onboarding, no sign-in required |

#### What it enables

- VideoEngine lists all `.mp4 / .mov / .avi` files in the connected folder
- User picks one or more to subtitle (batch support)
- Processed video is written back to Drive (or to a separate output folder)
- No manual upload/download — fully Drive-native workflow

#### Drive API flow (OAuth)

```
User → "Connect Google Drive" → OAuth2 consent screen
     → VideoEngine stores refresh token
     → Lists videos in target folder via Drive API
     → Streams video to local processing pipeline
     → Uploads output back to Drive
```

#### Drive API flow (shared link)

```
User pastes: https://drive.google.com/drive/folders/<FOLDER_ID>
VideoEngine extracts FOLDER_ID
→ Drive API (API key, no OAuth) lists public files
→ Downloads video, processes, returns download link
```

---

### API-First Architecture

#### Versioned public API

All routes move under `/v1/`:

```
POST   /v1/sources              Connect a video source (Drive folder, upload, URL)
GET    /v1/sources              List connected sources
DELETE /v1/sources/{id}         Disconnect a source

GET    /v1/sources/{id}/videos  List videos in a source

POST   /v1/jobs                 Create a subtitle job
GET    /v1/jobs                 List jobs (with filters: status, source, date)
GET    /v1/jobs/{id}            Get job status + result
DELETE /v1/jobs/{id}            Cancel a job

GET    /v1/templates            List subtitle templates
POST   /v1/templates            Create a custom template
PUT    /v1/templates/{id}       Update a template
DELETE /v1/templates/{id}       Delete a template

GET    /v1/presets              List style presets
POST   /v1/presets              Save a preset
DELETE /v1/presets/{id}         Delete a preset

POST   /v1/webhooks             Register a webhook endpoint
DELETE /v1/webhooks/{id}        Remove a webhook
```

#### Authentication — API keys

Every request must include:
```
Authorization: Bearer ve_live_xxxxxxxxxxxxxxxx
```

- Keys are scoped: `read`, `write`, `admin`
- Keys can be revoked without affecting others
- Usage is logged per key (requests, processing minutes)

#### Webhooks

Instead of polling `/v1/jobs/{id}`, clients register a URL and receive events:

```json
{
  "event": "job.completed",
  "job_id": "abc-123",
  "status": "done",
  "output_url": "https://drive.google.com/...",
  "timestamp": "2025-03-04T10:22:00Z"
}
```

Events: `job.queued`, `job.transcribing`, `job.rendering`, `job.completed`, `job.failed`

#### Create a job via API (example)

```bash
curl -X POST https://api.videoengine.io/v1/jobs \
  -H "Authorization: Bearer ve_live_xxxx" \
  -H "Content-Type: application/json" \
  -d '{
    "source": "drive_folder",
    "source_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs",
    "video_filename": "my_clip.mp4",
    "template": "center_minimal_v1",
    "output": {
      "destination": "drive",
      "folder_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs"
    },
    "webhook_url": "https://yourapp.com/webhooks/videoengine"
  }'
```

---

### New Components Required

| Component | Purpose |
|---|---|
| **Auth service** | Issue + validate API keys, manage users |
| **Google OAuth handler** | OAuth2 flow, token storage + refresh |
| **Drive connector** | List, download, upload via Drive API |
| **Job queue** | Handle multiple concurrent jobs (Celery + Redis, or asyncio queue) |
| **Webhook dispatcher** | POST events to registered URLs with retry logic |
| **User/workspace model** | Each user has their own keys, sources, jobs, templates |
| **Database** | Replace status.json files with Postgres (jobs, users, sources, keys) |

---

### Processing Architecture (V2)

```
API Request
    │
    ▼
Auth middleware (validate API key)
    │
    ▼
Job created in DB  ──────────────────────────► Webhook: job.queued
    │
    ▼
Job queue (worker picks up)
    │
    ├── Source = Drive?  → Stream video from Drive API
    ├── Source = Upload? → Read from temp storage
    └── Source = URL?    → Download video
    │
    ▼
Existing pipeline:
  FFmpeg audio extract
    → WhisperX transcribe
    → Subtitle engine
    → ASS export
    → FFmpeg burn
    │
    ▼
Output destination:
  Drive? → Upload back to Drive  ──────────► Webhook: job.completed
  Download? → Presigned URL
```

---

## V3 — Scale + Multi-language

- Multi-language transcription (WhisperX supports 90+ languages)
- Batch processing — subtitle an entire Drive folder in one job
- Custom font upload
- Subtitle editor — edit word timings before render
- Team workspaces — shared templates and presets across a team
- Usage-based billing (processing minutes)

---

## Priority Order for V2 Build

1. **Versioned API + API key auth** — foundational, everything else depends on it
2. **Database** (Postgres) — replace JSON status files
3. **Google Drive shared-link connector** — no OAuth complexity, fastest to ship
4. **Webhooks** — enables async workflows for API users
5. **Google OAuth (private Drive)** — full Drive integration
6. **Job queue** (Celery) — needed for concurrent multi-user processing
