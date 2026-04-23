// NEX 5.0 cockpit — vanilla JS. Phase 2: sense stream panel added.

const POLL_MS     = 2000;
const SENSE_MS    = 5000;   // sense events refresh is slightly slower

async function j(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok && r.status !== 401 && r.status !== 503) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

function fmtTs(sec) {
  if (!sec) return "—";
  return new Date(sec * 1000).toLocaleTimeString();
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ---- Phase 1 panels --------------------------------------------------------

async function refreshDbStats() {
  const data = await j("/api/db/stats");
  const tbody = document.querySelector("#db-stats tbody");
  const rows = [];
  for (const [name, info] of Object.entries(data)) {
    if (info.error) {
      rows.push(`<tr><td>${name}</td><td colspan="2" class="muted">${info.error}</td></tr>`);
      continue;
    }
    for (const [t, n] of Object.entries(info.tables)) {
      rows.push(`<tr><td>${name}</td><td>${t}</td><td>${n}</td></tr>`);
    }
  }
  tbody.innerHTML = rows.join("");
}

async function refreshQueues() {
  const data = await j("/api/writers/queues");
  const tbody = document.querySelector("#writer-queues tbody");
  tbody.innerHTML = Object.entries(data)
    .map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`)
    .join("");
}

async function refreshErrors() {
  const { events } = await j("/api/errors/recent?limit=50");
  const el = document.getElementById("error-list");
  const count = document.getElementById("error-count");
  count.textContent = events.length ? `(${events.length})` : "(none)";
  el.innerHTML = events
    .slice().reverse()
    .map(e => `<div class="ev"><span class="ts">${fmtTs(e.timestamp)}</span><span class="lvl ${e.level}">${e.level}</span><span class="src">${escapeHtml(e.source)}</span>${escapeHtml(e.message)}${e.traceback ? `<pre>${escapeHtml(e.traceback)}</pre>` : ""}</div>`)
    .join("");
}

async function refreshAdmin() {
  const s = await j("/api/admin/status");
  const el = document.getElementById("admin-status");
  if (!s.configured)           el.textContent = "admin: not configured";
  else if (s.authenticated)    el.textContent = "admin: authenticated";
  else                         el.textContent = "admin: locked";
}

// ---- Phase 2 — sense stream ------------------------------------------------

async function refreshSenseStatus() {
  const data = await j("/api/sense/status");
  if (data.error) return;

  const badge   = document.getElementById("sense-global-badge");
  const running = data.global_running;
  badge.textContent = running ? "RUNNING" : "PAUSED";
  badge.className   = "badge " + (running ? "badge-on" : "badge-off");

  const tbody   = document.querySelector("#sense-table tbody");
  const adapters = Object.values(data.adapters || {});
  // Sort: internal first, then external alphabetically by id
  adapters.sort((a, b) => {
    if (a.is_internal !== b.is_internal) return a.is_internal ? -1 : 1;
    return a.id.localeCompare(b.id);
  });

  tbody.innerHTML = adapters.map(a => {
    const stateLabel = a.is_internal
      ? `<span class="state-on">always-on</span>`
      : (a.enabled ? `<span class="state-on">enabled</span>` : `<span class="state-off">disabled</span>`);
    const toggleBtn = a.is_internal
      ? `<span class="muted">—</span>`
      : `<button class="toggle-btn" data-id="${a.id}" data-enabled="${a.enabled}">${a.enabled ? "Disable" : "Enable"}</button>`;
    const errCell = a.last_error
      ? `<td class="err" title="${escapeHtml(a.last_error)}">${escapeHtml(a.last_error)}</td>`
      : `<td class="ok">—</td>`;
    return `<tr>
      <td>${escapeHtml(a.id)}</td>
      <td class="muted">${escapeHtml(a.stream)}</td>
      <td>${a.is_internal ? "internal" : "external"}</td>
      <td>${stateLabel}</td>
      <td class="muted">${fmtTs(a.last_poll_at)}</td>
      <td>${a.last_event_count}</td>
      ${errCell}
      <td>${toggleBtn}</td>
    </tr>`;
  }).join("");

  // Wire per-adapter toggle buttons
  document.querySelectorAll(".toggle-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const id = btn.dataset.id;
      try {
        await fetch(`/api/sense/toggle/${id}`, { method: "POST" });
        refreshSenseStatus();
      } catch (e) { console.warn(e); }
    });
  });
}

async function refreshSenseEvents() {
  const data = await j("/api/sense/recent?limit=50");
  const events = data.events || [];
  const el = document.getElementById("sense-events");
  const count = document.getElementById("sense-event-count");
  count.textContent = events.length ? `(${events.length})` : "(none)";
  el.innerHTML = events.map(ev => {
    let preview = "";
    try {
      const p = JSON.parse(ev.payload);
      // show first meaningful key
      preview = p.title || p.symbol || p.iso_local || p.cpu_percent !== undefined ? `cpu:${p.cpu_percent}%` : "";
    } catch (_) {}
    return `<div class="ev"><span class="ts">${fmtTs(ev.timestamp)}</span><span class="stream">${escapeHtml(ev.stream)}</span>${escapeHtml(preview)}</div>`;
  }).join("");
}

// ---- Controls --------------------------------------------------------------

document.getElementById("sense-start-btn").addEventListener("click", async () => {
  await fetch("/api/sense/start", { method: "POST" });
  refreshSenseStatus();
});

document.getElementById("sense-stop-btn").addEventListener("click", async () => {
  await fetch("/api/sense/stop", { method: "POST" });
  refreshSenseStatus();
});

document.getElementById("admin-form").addEventListener("submit", async ev => {
  ev.preventDefault();
  const pw = document.getElementById("admin-password").value;
  const fb = document.getElementById("admin-feedback");
  try {
    const r = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pw }),
    });
    const data = await r.json();
    fb.textContent = data.authenticated ? "authenticated" : "login failed";
    document.getElementById("admin-password").value = "";
    refreshAdmin();
  } catch (e) { fb.textContent = String(e); }
});

document.getElementById("admin-logout").addEventListener("click", async () => {
  await fetch("/api/admin/logout", { method: "POST" });
  document.getElementById("admin-feedback").textContent = "logged out";
  refreshAdmin();
});

document.getElementById("chat-form").addEventListener("submit", async ev => {
  ev.preventDefault();
  const input = document.getElementById("chat-input");
  const reg   = document.getElementById("chat-register").value;
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = "";
  const log = document.getElementById("chat-log");
  log.insertAdjacentHTML("beforeend", `<div class="u">&gt; ${escapeHtml(prompt)}</div>`);
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, register: reg || undefined }),
    });
    const data = await r.json();
    log.insertAdjacentHTML("beforeend",
      `<div class="n">${escapeHtml(data.text)}<span class="meta">[${data.register}${data.voice_ok ? "" : " • voice offline"}]</span></div>`);
    log.scrollTop = log.scrollHeight;
  } catch (e) {
    log.insertAdjacentHTML("beforeend", `<div class="n">chat failed: ${escapeHtml(String(e))}</div>`);
  }
});

// ---- Polling loops ---------------------------------------------------------

async function poll() {
  try {
    await Promise.all([
      refreshDbStats(), refreshQueues(), refreshErrors(), refreshAdmin(), refreshSenseStatus(),
    ]);
  } catch (e) { console.warn(e); }
}

async function pollSenseEvents() {
  try { await refreshSenseEvents(); } catch (e) { console.warn(e); }
}

poll();
pollSenseEvents();
setInterval(poll,             POLL_MS);
setInterval(pollSenseEvents,  SENSE_MS);
