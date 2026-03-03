/* VideoEngine — frontend app */

const API = "";  // same origin

// ── State ────────────────────────────────────────────────
let state = {
  jobId: null,
  transcript: null,
  pollTimer: null,
};

// ── Screen navigation ────────────────────────────────────
function showScreen(name) {
  document.querySelectorAll(".screen").forEach(s => s.classList.remove("active"));
  document.getElementById(`screen-${name}`).classList.add("active");
}

// ── Upload screen ────────────────────────────────────────
const dropZone   = document.getElementById("drop-zone");
const fileInput  = document.getElementById("file-input");
const uploadMsg  = document.getElementById("upload-msg");

dropZone.addEventListener("click", () => fileInput.click());
dropZone.addEventListener("dragover", e => { e.preventDefault(); dropZone.classList.add("drag-over"); });
dropZone.addEventListener("dragleave", () => dropZone.classList.remove("drag-over"));
dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("drag-over");
  const file = e.dataTransfer.files[0];
  if (file) handleUpload(file);
});
fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) handleUpload(fileInput.files[0]);
});

async function handleUpload(file) {
  uploadMsg.textContent = `Uploading ${file.name}…`;

  const form = new FormData();
  form.append("file", file);

  try {
    const res  = await fetch(`${API}/api/upload`, { method: "POST", body: form });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || "Upload failed");

    state.jobId = data.job_id;
    uploadMsg.textContent = "Upload complete. Starting transcription…";

    // auto-start transcription
    await startTranscription();
  } catch (err) {
    uploadMsg.textContent = `Error: ${err.message}`;
  }
}

async function startTranscription() {
  await fetch(`${API}/api/jobs/${state.jobId}/transcribe`, { method: "POST" });
  showScreen("editor");
  document.getElementById("editor-status").textContent = "Transcribing… this may take a minute.";
  pollJobStatus();
}

// ── Poll job status ──────────────────────────────────────
function pollJobStatus() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/api/jobs/${state.jobId}`);
      const data = await res.json();
      updateEditorStatus(data);
    } catch (_) {}
  }, 2000);
}

function updateEditorStatus(data) {
  const statusEl  = document.getElementById("editor-status");
  const renderBtn = document.getElementById("btn-render");

  const labels = {
    queued:            "Queued for transcription…",
    extracting_audio:  "Extracting audio…",
    transcribing:      "Transcribing with WhisperX…",
    transcribed:       "Transcription complete.",
    rendering_queued:  "Render queued…",
    building_subtitles:"Building subtitles…",
    rendering:         "Burning subtitles into video…",
    done:              "Done! Video is ready.",
    error:             `Error: ${data.error || "unknown"}`,
  };

  statusEl.textContent = labels[data.status] || data.status;

  if (data.status === "transcribed" || data.status === "done") {
    clearInterval(state.pollTimer);
    renderBtn.disabled = false;
    if (!state.transcript && data.status !== "rendering") {
      loadTranscript();
    }
  }

  if (data.status === "done") {
    clearInterval(state.pollTimer);
    showScreen("export");
    document.getElementById("export-status").textContent = "Done!";
    document.getElementById("export-status").className = "status-badge done";
    document.getElementById("btn-download").disabled = false;
  }

  if (data.status === "error") {
    clearInterval(state.pollTimer);
    renderBtn.disabled = false;
  }

  if (["rendering_queued", "building_subtitles", "rendering"].includes(data.status)) {
    renderBtn.disabled = true;
  }
}

// ── Load & render transcript preview ────────────────────
async function loadTranscript() {
  try {
    const res  = await fetch(`${API}/api/jobs/${state.jobId}/transcript`);
    if (!res.ok) return;
    const data = await res.json();
    state.transcript = data;
    renderTranscriptPreview(data.words);
  } catch (_) {}
}

function renderTranscriptPreview(words) {
  const preview = document.getElementById("transcript-preview");
  preview.innerHTML = "";

  // Group words into simple blocks of up to 8 words for display
  const BLOCK_SIZE = 8;
  for (let i = 0; i < words.length; i += BLOCK_SIZE) {
    const group = words.slice(i, i + BLOCK_SIZE);
    const card  = document.createElement("div");
    card.className = "block-card";

    const time = document.createElement("div");
    time.className = "block-time";
    time.textContent = `${group[0].start.toFixed(2)}s – ${group[group.length - 1].end.toFixed(2)}s`;

    const row = document.createElement("div");
    row.className = "block-words";
    group.forEach(w => {
      const chip = document.createElement("span");
      chip.className = "word-chip" + (w.confidence < 0.6 ? " low-confidence" : "");
      chip.textContent = w.text;
      row.appendChild(chip);
    });

    card.appendChild(time);
    card.appendChild(row);
    preview.appendChild(card);
  }
}

// ── Style editor controls ────────────────────────────────
async function loadTemplates() {
  const res  = await fetch(`${API}/api/templates`);
  const data = await res.json();
  const sel  = document.getElementById("sel-template");
  sel.innerHTML = "";
  data.templates.forEach(t => {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    sel.appendChild(opt);
  });
}

// Range slider live labels
document.querySelectorAll("input[type=range]").forEach(r => {
  const label = document.getElementById(`val-${r.id.replace("rng-", "")}`);
  if (label) {
    r.addEventListener("input", () => { label.textContent = r.value; });
  }
});

// Color pickers → sync hex input
function syncColor(pickerId, textId) {
  const picker = document.getElementById(pickerId);
  const text   = document.getElementById(textId);
  picker.addEventListener("input", () => { text.value = picker.value; });
  text.addEventListener("input", () => {
    if (/^#[0-9a-fA-F]{6}$/.test(text.value)) picker.value = text.value;
  });
}
syncColor("pick-base-color",      "txt-base-color");
syncColor("pick-highlight-color", "txt-highlight-color");

// ── Render ───────────────────────────────────────────────
document.getElementById("btn-render").addEventListener("click", async () => {
  const template = document.getElementById("sel-template").value;
  const maxWords = parseInt(document.getElementById("rng-max-words").value);
  const pause    = parseFloat(document.getElementById("rng-pause").value) / 10;
  const maxDur   = parseFloat(document.getElementById("rng-max-dur").value) / 10;

  const body = {
    template_name: template,
    block_config_override: {
      max_words_per_block: maxWords,
      pause_threshold: pause,
      max_duration_per_block: maxDur,
    },
    video_width: 1080,
    video_height: 1920,
  };

  document.getElementById("btn-render").disabled = true;
  document.getElementById("editor-status").textContent = "Render queued…";

  await fetch(`${API}/api/jobs/${state.jobId}/render`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  showScreen("export");
  document.getElementById("export-status").textContent = "Rendering…";
  document.getElementById("export-status").className = "status-badge working";
  document.getElementById("btn-download").disabled = true;
  pollExportStatus();
});

// ── Export screen ────────────────────────────────────────
function pollExportStatus() {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state.pollTimer = setInterval(async () => {
    try {
      const res  = await fetch(`${API}/api/jobs/${state.jobId}`);
      const data = await res.json();
      const statusEl = document.getElementById("export-status");

      const labels = {
        rendering_queued:  "Render queued…",
        building_subtitles:"Building subtitles…",
        rendering:         "Burning subtitles into video…",
        done:              "Done!",
        error:             `Error: ${data.error || "unknown"}`,
      };

      statusEl.textContent = labels[data.status] || data.status;

      if (data.status === "done") {
        clearInterval(state.pollTimer);
        statusEl.className = "status-badge done";
        document.getElementById("btn-download").disabled = false;
      } else if (data.status === "error") {
        clearInterval(state.pollTimer);
        statusEl.className = "status-badge error";
      } else {
        statusEl.className = "status-badge working";
      }
    } catch (_) {}
  }, 2000);
}

document.getElementById("btn-download").addEventListener("click", () => {
  window.location.href = `${API}/api/jobs/${state.jobId}/download`;
});

document.getElementById("btn-new-upload").addEventListener("click", () => {
  if (state.pollTimer) clearInterval(state.pollTimer);
  state = { jobId: null, transcript: null, pollTimer: null };
  document.getElementById("upload-msg").textContent = "";
  document.getElementById("transcript-preview").innerHTML = "";
  document.getElementById("btn-render").disabled = true;
  showScreen("upload");
});

// ── Init ─────────────────────────────────────────────────
(async () => {
  await loadTemplates();
  showScreen("upload");
})();
