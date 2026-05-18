// NEX 5.0 — HUD app.js

// ── Theme toggle ──────────────────────────────────────────────────────────────

function applyTheme(mode) {
  const html = document.documentElement;
  if (mode === "light") {
    html.classList.add("light-mode");
  } else {
    html.classList.remove("light-mode");
  }
  const icon = document.getElementById("theme-toggle-icon");
  if (icon) icon.textContent = (mode === "light") ? "☀" : "☾";
}

function initTheme() {
  const saved = localStorage.getItem("nex5_theme") || "dark";
  applyTheme(saved);
  const wrap = document.getElementById("theme-toggle-wrap");
  if (wrap) {
    wrap.addEventListener("click", () => {
      const current = localStorage.getItem("nex5_theme") || "dark";
      const next = current === "dark" ? "light" : "dark";
      localStorage.setItem("nex5_theme", next);
      applyTheme(next);
    });
  }
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initTheme);
} else {
  initTheme();
}

// ── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch(url, options = {}) {
  const r = await fetch(url, options);
  if (!r.ok) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function fmtTs(sec) {
  if (!sec) return "—";
  return new Date(sec * 1000).toLocaleTimeString("en-GB", { hour12: false });
}

function focusBar(focusNum) {
  const filled = Math.round((focusNum ?? 0) * 10);
  return "█".repeat(filled) + "░".repeat(10 - filled);
}

function magBar(mag) {
  if (!mag || mag <= 0) return "░░░░░";
  const bars = Math.min(5, Math.max(1, Math.ceil(Math.log10(mag * 1000))));
  return "▮".repeat(bars) + "░".repeat(5 - bars);
}

function readinessBar(score) {
  const filled = Math.round(Math.min(1, score ?? 0) * 10);
  return "█".repeat(filled) + "░".repeat(10 - filled);
}

// ── Clock ────────────────────────────────────────────────────────────────────

function tickClock() {
  document.getElementById("tb-clock").textContent =
    new Date().toLocaleTimeString("en-GB", { hour12: false });
}
tickClock();
setInterval(tickClock, 1000);

// ── Sense stream ─────────────────────────────────────────────────────────────

const MAX_ROWS = 200;
let senseCount = 0;
let lastSenseId = 0;

function streamBadge(stream) {
  if (stream === "internal.fountain") return ['badge-fountain', 'FOUNTAIN'];
  if (stream.startsWith("internal."))    return ['badge-internal', 'INTERNAL'];
  if (stream.startsWith("ai_research.")) return ['badge-ai', 'AI'];
  if (stream.startsWith("crypto.") || stream.startsWith("markets.")) return ['badge-market', 'MARKET'];
  if (stream.startsWith("cognition."))   return ['badge-cognit', 'COGNIT'];
  if (stream.startsWith("computing."))   return ['badge-compute', 'COMPUTE'];
  if (stream.startsWith("news."))        return ['badge-news', 'NEWS'];
  return ['badge-feed', 'FEED'];
}

function parsePreview(payload, stream) {
  try {
    const p = JSON.parse(payload);
    if (stream === "internal.fountain") return (p.thought || "").slice(0, 55);
    if (stream === "internal.meta_awareness") return `beliefs:${p.beliefs ?? "?"} pipeline:${p.pipeline_runs ?? "?"}`;
    if (p.title)   return p.title.slice(0, 55);
    if (p.symbol)  return p.symbol;
    if (p.cpu_percent !== undefined) return `cpu:${p.cpu_percent}% mem:${p.memory_percent ?? "?"}%`;
    if (p.iso_local) return p.iso_local;
    if (p.belief_count !== undefined) return `beliefs:${p.belief_count}`;
    if (p.thought) return p.thought.slice(0, 55);
    const first = Object.values(p)[0];
    return (typeof first === "object" && first !== null
      ? JSON.stringify(first) : String(first ?? "")).slice(0, 55);
  } catch (_) { return ""; }
}

async function refreshSense() {
  const data = await apiFetch("/api/sense/recent?limit=100").catch(() => null);
  if (!data) return;
  const events = (data.events || []).filter(e => e.id > lastSenseId);
  if (!events.length) return;

  const feed = document.getElementById("sense-feed");
  events.forEach(ev => {
    lastSenseId = Math.max(lastSenseId, ev.id);
    senseCount++;
    const [cls, label] = streamBadge(ev.stream);
    const preview = parsePreview(ev.payload, ev.stream);
    const isFountain = ev.stream === "internal.fountain";

    const row = document.createElement("div");
    row.className = "feed-row" + (isFountain ? " fountain-row" : "");
    if (isFountain) {
      row.innerHTML = `<span class="feed-ts">${fmtTs(ev.timestamp)}</span>`
        + `<span class="badge ${cls}">${label}</span> `
        + `<span>${esc(preview)}</span>`;
    } else {
      row.innerHTML = `<span class="feed-ts">${fmtTs(ev.timestamp)}</span>`
        + `<span class="badge ${cls}">${label}</span>`
        + `<span class="feed-stream">${esc(ev.stream)}</span>`
        + `<span class="feed-preview">${esc(preview)}</span>`;
    }
    feed.prepend(row);
  });

  // Cap rows
  while (feed.children.length > MAX_ROWS) feed.lastChild.remove();
  document.getElementById("sense-count").textContent = senseCount;
}

// ── Bonsai ───────────────────────────────────────────────────────────────────

async function refreshBonsai() {
  const data = await apiFetch("/api/dynamic/status").catch(() => null);
  if (!data || data.error) return;

  const branches = (data.branches || []).slice().sort((a, b) => b.focus_num - a.focus_num);
  const hotCount = branches.filter(b => "efg".includes(b.focus_increment)).length;

  // Metric strip
  document.getElementById("ms-hot").textContent = hotCount;

  // Bonsai meta
  document.getElementById("bonsai-meta").textContent =
    `aperture ${data.aperture != null ? data.aperture.toFixed(3) : "—"} | ` +
    `consolidation ${data.consolidation_active ? "ACTIVE" : "idle"} | ` +
    `${data.active_branch_count}/${data.total_branches} active`;

  const feed = document.getElementById("bonsai-feed");
  feed.innerHTML = branches.map(b => {
    const hot  = "efg".includes(b.focus_increment);
    const self = b.branch_id === "systems";
    const cls  = (hot ? " hot" : "") + (self ? " self" : "");
    return `<div class="branch-row${cls}">`
      + `<span class="branch-id">${esc(b.branch_id)}</span>`
      + `<span class="branch-bar">${focusBar(b.focus_num)}</span>`
      + `<span class="branch-focus-letter">${esc(b.focus_increment)}</span>`
      + `<span class="branch-focus-num">${(b.focus_num ?? 0).toFixed(2)}</span>`
      + `<span class="branch-curiosity">c:${b.curiosity_weight}</span>`
      + `<span class="branch-texture">${esc(b.texture_increment)}</span>`
      + `</div>`;
  }).join("");
}

// ── Moltbook chats ───────────────────────────────────────────────────────────
const seenMbEvents = new Set();
async function refreshPipeline() {
  const data = await apiFetch("/api/moltbook/chats").catch(() => null);
  if (!data || data.error) return;
  const events = (data.events || []).filter(e => !seenMbEvents.has(e.id));
  if (!events.length) return;
  const feed = document.getElementById("pipeline-feed");
  events.slice().reverse().forEach(ev => {
    seenMbEvents.add(ev.id);
    const row = document.createElement("div");
    row.className = "pipe-row mb-row mb-" + ev.kind;
    if (ev.kind === "post") {
      const stCls = ev.status === "posted" ? "valence-like" : "valence-dislike";
      row.innerHTML =
        `<span class="pipe-ts">${fmtTs(ev.ts)}</span>` +
        `<span class="pipe-valence ${stCls}">${esc(ev.status)}</span>` +
        `<span class="pipe-src">${esc(ev.content)}</span>`;
    } else if (ev.kind === "dm_in") {
      row.innerHTML =
        `<span class="pipe-ts">${fmtTs(ev.ts)}</span>` +
        `<span class="pipe-step step-IN">DM</span>` +
        `<span class="pipe-branch">${esc(ev.from_agent || "")}</span>` +
        `<span class="pipe-valence valence-neutral">${esc(ev.status)}</span>` +
        `<span class="pipe-src">${esc(ev.content)}</span>`;
    } else {
      row.innerHTML =
        `<span class="pipe-ts">${fmtTs(ev.ts)}</span>` +
        `<span class="pipe-step">?</span>` +
        `<span class="pipe-src">${esc(JSON.stringify(ev))}</span>`;
    }
    feed.prepend(row);
  });
  while (feed.children.length > MAX_ROWS) feed.lastChild.remove();
  if (seenMbEvents.size > 500) {
    const arr = Array.from(seenMbEvents).slice(-300);
    seenMbEvents.clear();
    arr.forEach(x => seenMbEvents.add(x));
  }
}
// ── Fountain ──────────────────────────────────────────────────────────────────

let _ftnCurrentId = null;

async function refreshFountain() {
  const data = await apiFetch("/api/fountain/status").catch(() => null);
  if (!data || data.error) return;

  const el = document.getElementById("fountain-thought");
  _ftnCurrentId = data.last_id || null;

  if (data.last_thought) {
    const suffix = data.last_tag ? ` : ${data.last_tag}` : "";
    el.textContent = data.last_thought + suffix;
    el.classList.remove("empty");
    el.classList.remove("ftn-tagged-coin","ftn-tagged-maybe","ftn-tagged-non");
    if (data.last_tag) el.classList.add(`ftn-tagged-${data.last_tag}`);
  }

  // Highlight active button if already tagged
  ["coin","maybe","non"].forEach(t => {
    const b = document.getElementById(`ftn-tag-${t}`);
    if (b) b.classList.toggle("active", data.last_tag === t);
  });

  document.getElementById("fountain-fires").textContent = data.total_fires ?? 0;
  document.getElementById("sb-fires").textContent = data.total_fires ?? 0;
  document.getElementById("fountain-readiness").textContent =
    data.readiness_score != null ? data.readiness_score.toFixed(2) : "—";
  const bar = document.getElementById("fountain-bar");
  bar.textContent = readinessBar(data.readiness_score);
  if ((data.readiness_score ?? 0) >= 0.7) {
    bar.classList.add("pulsing");
  } else {
    bar.classList.remove("pulsing");
  }
  document.getElementById("fountain-last").textContent =
    data.last_fire_ts ? fmtTs(data.last_fire_ts) : "never";
}

// ── Belief stats ──────────────────────────────────────────────────────────────

async function refreshBeliefStats() {
  const data = await apiFetch("/api/beliefs/stats").catch(() => null);
  if (!data || data.error) return;

  document.getElementById("ms-beliefs").textContent = data.total ?? "—";
  document.getElementById("sb-beliefs").textContent = data.total ?? "—";

  const dist = data.tier_distribution || {};
  const tierStr = Object.entries(dist)
    .filter(([_, n]) => n > 0)
    .map(([t, n]) => `T${t}:${n}`)
    .join(" ");
  document.getElementById("sb-tiers").textContent = tierStr || "—";

  const edgeEl = document.getElementById("sb-edges");
  if (edgeEl) edgeEl.textContent = `edges: ${data.edge_count ?? 0}`;

  const tempEl = document.getElementById("sb-epistemic-temp");
  if (tempEl) {
    const t = data.epistemic_temperature ?? 0;
    const bar = "█".repeat(Math.round(t * 10)).padEnd(10, "░");
    tempEl.textContent = `temp: ${bar} ${t.toFixed(2)}`;
  }

  const synthEl = document.getElementById("sb-synth");
  if (synthEl) synthEl.textContent = data.synergized_count ?? 0;
}

// ── System status + metric strip ──────────────────────────────────────────────

function setDot(elId, on) {
  const el = document.getElementById(elId);
  if (!el) return;
  const dot = el.querySelector(".dot");
  if (dot) { dot.className = "dot " + (on ? "dot-on" : "dot-off"); }
}

async function refreshSystemStatus() {
  const data = await apiFetch("/api/system/status").catch(() => null);
  if (!data) return;

  setDot("ms-sched", data.scheduler);
  setDot("ms-dyn",   data.dynamic);
  setDot("ms-wm",    data.world_model);
  setDot("ms-mem2",  data.membrane);
  setDot("ms-sl",    data.self_location_committed);
  setDot("ms-ftn",   data.fountain);

  // Titlebar dots
  const dots = document.getElementById("tb-dots");
  const subsystems = ["scheduler","dynamic","world_model","membrane","fountain"];
  dots.innerHTML = subsystems.map(k =>
    `<span class="dot ${data[k] ? "dot-on" : "dot-off"}" title="${k}"></span>`
  ).join("");

  // Stillness pill (admin-only row, shown when stillness is active)
  const sRow = document.getElementById("stillness-pill-row");
  if (sRow) {
    const si = data.stillness_info;
    if (si && si.active) {
      document.getElementById("stillness-pill-left").textContent =
        si.seconds_left > 0 ? si.seconds_left.toFixed(0) + "s left" : "expiring";
      sRow.style.display = "";
    } else {
      sRow.style.display = "none";
    }
  }

  // Drive pill (admin-only row, shown when a drive is active)
  const dRow = document.getElementById("drive-pill-row");
  if (dRow) {
    const di = data.drives_info;
    if (di && di.topic) {
      const topic = di.topic.length > 40 ? di.topic.slice(0, 38) + "…" : di.topic;
      document.getElementById("drive-pill-topic").textContent = topic;
      document.getElementById("drive-pill-strength").textContent =
        "str:" + (di.drive_strength != null ? di.drive_strength.toFixed(2) : "—");
      document.getElementById("drive-pill-count").textContent =
        "×" + (di.reinforce_count ?? 0);
      dRow.style.display = "";
    } else {
      document.getElementById("drive-pill-topic").textContent = "—";
      document.getElementById("drive-pill-strength").textContent = "";
      document.getElementById("drive-pill-count").textContent = "";
      dRow.style.display = "none";
    }
  }
}

// ── Membrane snapshot (CPU, mem, time) ────────────────────────────────────────

async function refreshMembraneSnapshot() {
  const data = await apiFetch("/api/membrane/snapshot").catch(() => null);
  if (!data || data.error) return;

  const prop = data.proprioception || {};
  const temp = data.temporal || {};

  if (prop.cpu_percent != null)
    document.getElementById("ms-cpu").textContent = prop.cpu_percent.toFixed(0);
  if (prop.mem_percent != null)
    document.getElementById("ms-mem").textContent = prop.mem_percent.toFixed(0);
  if (temp.iso_local)
    document.getElementById("ms-time").textContent =
      temp.iso_local.split("T")[1]?.slice(0, 5) ?? "—";
}

// ── Feeds toggle ──────────────────────────────────────────────────────────────

let feedsRunning = false;

async function refreshFeedsStatus() {
  const data = await apiFetch("/api/sense/status").catch(() => null);
  if (!data || data.error) return;
  feedsRunning = data.global_running;
  const el  = document.getElementById("sb-feeds-status");
  const btn = document.getElementById("sb-feeds-toggle");
  const hdrBtn = document.getElementById("sense-feeds-btn");
  if (feedsRunning) {
    el.textContent = "feeds: RUNNING";
    el.className = "feeds-running";
    btn.textContent = "STOP";
    if (hdrBtn) { hdrBtn.textContent = "STOP"; hdrBtn.className = "sense-feeds-btn running"; }
  } else {
    el.textContent = "feeds: PAUSED";
    el.className = "feeds-paused";
    btn.textContent = "START";
    if (hdrBtn) { hdrBtn.textContent = "START"; hdrBtn.className = "sense-feeds-btn paused"; }
  }
}

async function toggleFeeds() {
  const url = feedsRunning ? "/api/sense/stop" : "/api/sense/start";
  await fetch(url, { method: "POST" }).catch(() => {});
  refreshFeedsStatus();
}

document.getElementById("sb-feeds-toggle").addEventListener("click", toggleFeeds);
document.getElementById("sense-feeds-btn")?.addEventListener("click", toggleFeeds);

// ── Admin ─────────────────────────────────────────────────────────────────────

document.getElementById("admin-toggle-btn").addEventListener("click", () => {
  document.getElementById("admin-panel").classList.toggle("open");
});

async function checkAdminState() {
  const s = await apiFetch("/api/admin/status").catch(() => null);
  if (!s) return;
  const line = document.getElementById("admin-state-line");
  if (!s.configured)       line.textContent = "admin: not configured";
  else if (s.authenticated) line.textContent = "admin: authenticated ✓";
  else                      line.textContent = "admin: locked";
  const vmRow = document.getElementById("voice-mode-row");
  if (vmRow) vmRow.style.display = s.authenticated ? "block" : "none";
}

// ── Voice mode toggle ──────────────────────────────────────────────────────────

let _voiceMode = "use_llm";

async function refreshVoiceMode() {
  try {
    const d = await apiFetch("/api/system/status");
    if (d && d.voice_engine) {
      _voiceMode = d.voice_engine.mode || "use_llm";
      const pill = document.getElementById("voice-mode-pill");
      const stats = document.getElementById("voice-mode-stats");
      if (pill) {
        pill.textContent = _voiceMode === "use_substrate" ? "Substrate mode" : "LLM mode";
        pill.style.background = _voiceMode === "use_substrate" ? "var(--accent)" : "var(--fg3)";
      }
      if (stats && d.voice_engine) {
        const ve = d.voice_engine;
        stats.textContent = `replies:${ve.reply_count ?? 0} miss:${ve.miss_count ?? 0}${ve.last_score != null ? " last:" + ve.last_score.toFixed(2) : ""}`;
      }
    }
  } catch (_) {}
}

document.getElementById("voice-mode-toggle-btn").addEventListener("click", async () => {
  const newMode = _voiceMode === "use_substrate" ? "use_llm" : "use_substrate";
  try {
    const r = await fetch("/api/voice_mode", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: newMode }),
    });
    const d = await r.json();
    if (d.ok) {
      _voiceMode = d.mode;
      await refreshVoiceMode();
    }
  } catch (e) {
    document.getElementById("admin-feedback").textContent = String(e);
  }
});

document.getElementById("admin-login-btn").addEventListener("click", async () => {
  const pw = document.getElementById("admin-pw").value;
  const fb = document.getElementById("admin-feedback");
  try {
    const r = await fetch("/api/admin/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ password: pw }),
    });
    const d = await r.json();
    fb.textContent = d.authenticated ? "ok" : "failed";
    document.getElementById("admin-pw").value = "";
    checkAdminState();
  } catch (e) { fb.textContent = String(e); }
});

document.getElementById("admin-logout-btn").addEventListener("click", async () => {
  await fetch("/api/admin/logout", { method: "POST" }).catch(() => {});
  document.getElementById("admin-feedback").textContent = "logged out";
  checkAdminState();
});

// ── Chat ──────────────────────────────────────────────────────────────────────

// ── Auto-pull messages Nex initiated (focus_loop stuck-pings, etc) ───
let lastChatTs = Math.floor(Date.now() / 1000) - 60;  // start 1 min ago
async function refreshChatRecent() {
  try {
    const data = await apiFetch(`/api/chat/recent?since=${lastChatTs}`);
    if (!data || !data.messages) return;
    for (const m of data.messages) {
      if (m.timestamp > lastChatTs) lastChatTs = m.timestamp;
      // Skip messages from session_id we already rendered via sendChat
      // (those came from a direct user prompt; auto-pulled ones come from
      // session_id 'internal_focus_loop' or similar daemon-written rows)
      if (m.session_id && m.session_id.startsWith("internal_")) {
        appendChat(m.role, m.content, "(unprompted: " + (m.register || "") + ")");
      }
    }
  } catch (e) { /* silent */ }
}
setInterval(refreshChatRecent, 15000);  // every 15s

function appendChat(role, text, meta) {
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "chat-msg " + (role === "user" ? "user-msg" : "nex-msg");
  div.innerHTML = `<div class="who">${role === "user" ? "you" : "nex"}</div>`
    + `<div class="text">${esc(text)}</div>`
    + (meta ? `<div class="chat-meta">${esc(meta)}</div>` : "");
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
}

function streamIntoDiv(textEl, fullText, onDone) {
  const chars = fullText.split("");
  let i = 0;
  const iv = setInterval(() => {
    if (i >= chars.length) {
      clearInterval(iv);
      if (onDone) onDone();
      return;
    }
    textEl.textContent += chars[i++];
    const log = document.getElementById("chat-log");
    log.scrollTop = log.scrollHeight;
  }, 14);
}

async function sendChat() {
  const input = document.getElementById("chat-input");
  const reg   = document.getElementById("chat-register").value;
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = "";
  appendChat("user", prompt, null);

  // Update membrane side display optimistically
  const isSelf = /\b(you|your|yourself|feel|feeling|think|thinking|believe|want|inside|who are you|what are you|how are you|do you)\b/i.test(prompt);
  const memEl = document.getElementById("sb-membrane").querySelector("span");
  if (memEl) {
    memEl.textContent = isSelf ? "INSIDE" : "OUTSIDE";
    memEl.className = isSelf ? "mem-inside" : "mem-outside";
  }

  // Create nex div immediately with streaming placeholder
  const log = document.getElementById("chat-log");
  const div = document.createElement("div");
  div.className = "chat-msg nex-msg";
  div.innerHTML = `<div class="who">nex</div><div class="text"></div>`;
  log.appendChild(div);
  log.scrollTop = log.scrollHeight;
  const textEl = div.querySelector(".text");

  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, register: reg || undefined }),
    });
    const d = await r.json();
    streamIntoDiv(textEl, d.text, () => {
      const metaEl = document.createElement("div");
      metaEl.className = "chat-meta";
      let metaStr = `[${d.register}${d.voice_ok ? "" : " · voice offline"}]`;
      if (d.tool_used) metaStr += ` [${d.tool_used}]`;
      metaEl.textContent = metaStr;
      div.appendChild(metaEl);
    });
  } catch (e) {
    textEl.textContent = `error: ${e}`;
  }
}

document.getElementById("chat-send").addEventListener("click", sendChat);
document.getElementById("chat-input").addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendChat(); }
});

// ── Strike modal ──────────────────────────────────────────────────────────────

let currentStrikeId = null;

function openModal(record) {
  currentStrikeId = record.id;
  document.getElementById("modal-type").textContent    = record.strike_type;
  document.getElementById("modal-ts").textContent      = fmtTs(record.fired_at);
  document.getElementById("modal-input").textContent   = record.input_text;
  document.getElementById("modal-response").textContent = record.response_text;
  document.getElementById("modal-branch").textContent  = record.hottest_branch || "—";
  document.getElementById("modal-readiness").textContent = (record.readiness_score ?? 0).toFixed(2);
  document.getElementById("modal-bb").textContent      = record.beliefs_before;
  document.getElementById("modal-ba").textContent      = record.beliefs_after;
  document.getElementById("modal-notes").value         = record.notes || "";
  document.getElementById("strike-modal").classList.add("open");
}

function closeModal() {
  document.getElementById("strike-modal").classList.remove("open");
  currentStrikeId = null;
}

document.getElementById("modal-close").addEventListener("click", closeModal);
document.getElementById("modal-cancel").addEventListener("click", closeModal);
document.getElementById("strike-modal").addEventListener("click", e => {
  if (e.target === document.getElementById("strike-modal")) closeModal();
});

document.getElementById("modal-save").addEventListener("click", async () => {
  if (currentStrikeId == null) return;
  const notes = document.getElementById("modal-notes").value;
  await fetch("/api/strikes/notes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ id: currentStrikeId, notes }),
  }).catch(() => {});
  closeModal();
});

document.getElementById("strike-fire-btn").addEventListener("click", async () => {
  const type = document.getElementById("strike-select").value;
  const status = document.getElementById("strike-status");
  status.textContent = `firing ${type}…`;

  let record;
  try {
    const r = await fetch("/api/strikes/fire", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strike_type: type }),
    });
    const body = await r.text();
    try {
      record = JSON.parse(body);
    } catch (_) {
      status.textContent = `failed: server returned non-JSON (${r.status})`;
      console.error("Strike: non-JSON response:", body.slice(0, 200));
      return;
    }
    if (!r.ok || record.error) {
      status.textContent = `failed: ${record.error || r.status}`;
      console.error("Strike: error response:", record);
      return;
    }
  } catch (e) {
    status.textContent = `failed: ${e}`;
    console.error("Strike: fetch error:", e);
    return;
  }

  console.log("Strike record:", record);
  status.textContent = `done (id=${record.id})`;
  try {
    openModal(record);
  } catch (e) {
    console.error("Strike: openModal threw:", e);
    status.textContent = `fired (id=${record.id}) — modal error: ${e}`;
  }
});

// ── AGI Watch ─────────────────────────────────────────────────────────────────

const _AGI_SELF_RE = /\b(i want|i am|i notice|i feel|i think|i wonder|i realize|i find|i see|i know|i have|i need|my )\b/i;

let agiSignals       = [];      // { type, ts, excerpt }
let agiLastFtnTs     = 0;
let agiLastBeliefTs  = 0;
let agiLastStrikeId  = 0;
let agiFtnTimestamps = [];
let agiIgnitionFired = false;
let agiCollapseTimer = null;
let agiUserExpanded  = false;
let agiActiveTab     = "signals";

function _agiTypeClass(type) {
  return `agi-type-${type.replace(/[^A-Z_]/g, "")}`;
}

function _agiRenderLog() {
  const log = document.getElementById("agi-log");
  if (!log) return;
  log.innerHTML = agiSignals.slice(0, 200).map(s => {
    const existing = s.eventId ? (window.coincidenceTags || {})[s.eventId] : null;
    const tagButtons = s.eventId
      ? `<span class="coin-tag-row" data-event-id="${s.eventId}">`
        + `<button class="coin-btn coin-coin${existing==='coin'?' active':''}" title="coincidence">coin</button>`
        + `<button class="coin-btn coin-maybe${existing==='maybe'?' active':''}" title="maybe">maybe</button>`
        + `<button class="coin-btn coin-non${existing==='non'?' active':''}" title="non">non</button>`
        + (existing ? `<span class="coin-tagged">: ${existing}</span>` : "")
        + `</span>`
      : "";
    return `<div class="agi-log-row" data-event-id="${s.eventId || ''}">`
      + `<span class="agi-log-ts">${fmtTs(s.ts)}</span>`
      + `<span class="agi-log-type ${_agiTypeClass(s.type)}">${s.type}</span>`
      + `<span class="agi-log-txt">${esc(s.excerpt)}</span>`
      + tagButtons
      + `</div>`;
  }).join("");
  log.querySelectorAll(".coin-btn").forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.stopPropagation();
      const row = btn.closest(".coin-tag-row");
      const fid = parseInt(row.dataset.eventId, 10);
      let tag = null;
      if (btn.classList.contains("coin-coin")) tag = "coin";
      else if (btn.classList.contains("coin-maybe")) tag = "maybe";
      else if (btn.classList.contains("coin-non")) tag = "non";
      if (!fid || !tag) return;
      try {
        const resp = await fetch("/api/coincidence/tag", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({fountain_event_id: fid, tag})
        });
        if (resp.ok) {
          window.coincidenceTags = window.coincidenceTags || {};
          window.coincidenceTags[fid] = tag;
          _agiRenderLog();
        }
      } catch (err) {
        console.error("tag failed", err);
      }
    });
  });
}

(async function loadCoincidenceTags() {
  try {
    const r = await fetch("/api/coincidence/tags");
    if (r.ok) {
      const data = await r.json();
      window.coincidenceTags = data.tags || {};
    }
  } catch (e) { /* silent */ }
})();

function _agiToggleExpand(force) {
  const panel = document.getElementById("agi-watch");
  if (!panel) return;
  agiUserExpanded = force !== undefined ? force : !agiUserExpanded;
  if (agiUserExpanded) {
    panel.classList.add("expanded");
    if (agiCollapseTimer) { clearTimeout(agiCollapseTimer); agiCollapseTimer = null; }
    if (agiActiveTab === "insights") refreshInsights();
  } else {
    panel.classList.remove("expanded");
  }
}

function _agiSetTab(tab) {
  agiActiveTab = tab;
  document.querySelectorAll(".agi-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.tab === tab);
  });
  document.getElementById("agi-tab-signals")?.classList.toggle("active", tab === "signals");
  document.getElementById("agi-tab-insights")?.classList.toggle("active", tab === "insights");
  document.getElementById("agi-tab-coinlab")?.classList.toggle("active", tab === "coinlab");
  if (tab === "insights") refreshInsights();
  if (tab === "coinlab") refreshCoinLab();
}

function _agiShowSignal(type, ts, excerpt, eventId) {
  const msg    = document.getElementById("agi-strip-msg");
  const count  = document.getElementById("agi-sig-count");
  const status = document.getElementById("agi-status");
  if (!msg) return;

  agiSignals.unshift({ type, ts, excerpt, eventId: eventId || null });
  _agiRenderLog();

  count.textContent = `signals: ${agiSignals.length}`;
  if (status) status.textContent = "⚡";
  msg.innerHTML = `<span class="${_agiTypeClass(type)}">${type}</span>`
    + `<span class="agi-strip-ts">${fmtTs(ts)}</span>`
    + `<span class="agi-strip-txt">"${esc(excerpt.slice(0, 60))}"</span>`;

  if (!agiUserExpanded) {
    const panel = document.getElementById("agi-watch");
    if (panel) panel.classList.add("expanded");
    if (agiCollapseTimer) clearTimeout(agiCollapseTimer);
    agiCollapseTimer = setTimeout(() => {
      if (!agiUserExpanded) {
        const p = document.getElementById("agi-watch");
        if (p) p.classList.remove("expanded");
      }
      agiCollapseTimer = null;
    }, 9000);
  }
}

// Strip click → toggle expand
document.getElementById("agi-strip")?.addEventListener("click", () => _agiToggleExpand());

// Tab buttons
document.querySelectorAll(".agi-tab").forEach(btn => {
  btn.addEventListener("click", (e) => {
    e.stopPropagation();
    _agiSetTab(btn.dataset.tab);
  });
});

// Close button
document.getElementById("agi-close-btn")?.addEventListener("click", (e) => {
  e.stopPropagation();
  _agiToggleExpand(false);
});

// Copy all button
document.getElementById("agi-copy-btn")?.addEventListener("click", (e) => {
  e.stopPropagation();
  if (agiActiveTab === "signals") {
    const text = agiSignals.map(s =>
      `${fmtTs(s.ts)}  ${s.type.padEnd(18)}  ${s.excerpt}`
    ).join("\n");
    navigator.clipboard.writeText(text).catch(() => {});
  } else {
    const rows = document.querySelectorAll("#agi-insights-log .insights-row");
    const lines = [];
    rows.forEach(r => lines.push(r.innerText.replace(/\s+/g, " ").trim()));
    navigator.clipboard.writeText(lines.join("\n")).catch(() => {});
  }
});

// Ctrl+Shift+L keyboard shortcut
document.addEventListener("keydown", (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === "L") {
    e.preventDefault();
    _agiToggleExpand();
  }
});

async function refreshInsights() {
  const log = document.getElementById("agi-insights-log");
  if (!log) return;
  const data = await apiFetch("/api/beliefs/insights").catch(() => null);
  if (!data || data.error) return;
  const items = data.insights || [];
  if (!items.length) {
    log.innerHTML = `<div style="color:var(--fg3);padding:0.5rem;font-size:11px;">No insights yet.</div>`;
    return;
  }
  log.innerHTML = items.map(b => {
    const ts = fmtTs(b.created_at || 0);
    const meta = `T${b.tier} · ${b.source} · conf=${(b.confidence||0).toFixed(2)}`;
    return `<div class="insights-row">`
      + `<span class="insights-row-ts">${esc(ts)}</span>`
      + `<span class="insights-row-meta">[${esc(meta)}]</span>`
      + `<span class="insights-row-txt">${esc(b.content || "")}</span>`
      + `</div>`;
  }).join("");
}

async function pollAgi() {
  const now = Date.now() / 1000;

  // ── 1. Fountain: SELF_SIGNAL + IGNITION_PATTERN ──────────────────────────
  const ftnData = await apiFetch("/api/fountain/recent").catch(() => null);
  if (ftnData && ftnData.events) {
    for (const ev of ftnData.events) {
      if (!ev.ts || ev.ts <= agiLastFtnTs) continue;
      agiLastFtnTs = Math.max(agiLastFtnTs, ev.ts);
      const thought = ev.thought || "";
      agiFtnTimestamps.push(ev.ts);

      if (_AGI_SELF_RE.test(thought)) {
        _agiShowSignal("SELF_SIGNAL", ev.ts, thought);
      }
    }

    // Prune timestamps older than 1 hour, then check count
    agiFtnTimestamps = agiFtnTimestamps.filter(t => now - t < 3600);
    if (agiFtnTimestamps.length > 3 && !agiIgnitionFired) {
      agiIgnitionFired = true;
      _agiShowSignal("IGNITION_PATTERN", now,
        `${agiFtnTimestamps.length} fountain fires in the last hour`);
    }
    if (agiFtnTimestamps.length <= 3) agiIgnitionFired = false;
  }

  // ── 2. Beliefs: DEEP_BELIEF (tier >= 5, newly crystallised) ──────────────
  const beliefData = await apiFetch("/api/beliefs/recent").catch(() => null);
  if (beliefData && beliefData.beliefs) {
    for (const b of beliefData.beliefs) {
      const bTs = b.created_at || b.timestamp || 0;
      if (bTs <= agiLastBeliefTs) continue;
      if ((b.tier || 0) >= 5) {
        agiLastBeliefTs = Math.max(agiLastBeliefTs, bTs);
        _agiShowSignal("DEEP_BELIEF", bTs,
          `Tier ${b.tier}: ${(b.content || "").slice(0, 200)}`);
      } else {
        agiLastBeliefTs = Math.max(agiLastBeliefTs, bTs);
      }
    }
  }

  // ── 3. Strikes: RECURSION ────────────────────────────────────────────────
  const strikeData = await apiFetch("/api/strikes/recent").catch(() => null);
  if (strikeData && strikeData.strikes) {
    for (const s of strikeData.strikes) {
      if ((s.id || 0) <= agiLastStrikeId) continue;
      agiLastStrikeId = Math.max(agiLastStrikeId, s.id || 0);
      const resp = s.response_text || "";
      const hasI       = /\bI\b/.test(resp);
      const hasMy      = /\bmy\b/i.test(resp);
      const hasThinking = /\bthinking\b/i.test(resp);
      if (hasI && hasMy && hasThinking) {
        _agiShowSignal("RECURSION", s.fired_at || 0,
          resp.slice(0, 200));
      }
    }
  }
}

// ── Open Problems ─────────────────────────────────────────────────────────────

async function refreshProblems() {
  const data = await apiFetch("/api/problems").catch(() => null);
  if (!data) return;
  const feed = document.getElementById("problems-feed");
  const meta = document.getElementById("problems-meta");
  if (!feed || !meta) return;
  const problems = data.problems || [];
  meta.textContent = problems.length ? `${problems.length} open` : "none";
  feed.innerHTML = problems.slice(0, 5).map(p =>
    `<div class="problem-row" title="${esc(p.description || '')}">`
    + `<span style="color:var(--accent2);margin-right:4px;">▸</span>`
    + `<span>${esc(p.title)}</span>`
    + `<span style="color:var(--fg3);margin-left:4px;font-size:9px;">${fmtTs(p.last_touched_at)}</span>`
    + `</div>`
  ).join("");
}

// ── Drive proposals ───────────────────────────────────────────────────────────

async function refreshDriveProposals() {
  const data = await apiFetch("/api/dynamic/drive_proposals").catch(() => null);
  if (!data || data.error) return;
  const feed = document.getElementById("drives-feed");
  const meta = document.getElementById("drives-meta");
  if (!feed || !meta) return;
  const pending = (data.proposals || []).filter(p => p.status === "pending");
  meta.textContent = pending.length ? `${pending.length} pending` : "none";
  feed.innerHTML = "";
  for (const p of data.proposals.slice(0, 8)) {
    const row = document.createElement("div");
    row.style.cssText = "display:flex;align-items:center;gap:4px;margin-bottom:2px;";
    const badge = document.createElement("span");
    badge.style.cssText = "font-size:9px;padding:1px 3px;border-radius:2px;background:var(--bg2);";
    badge.textContent = p.status.toUpperCase();
    const label = document.createElement("span");
    label.textContent = `${p.branch_id} p=${p.pressure.toFixed(2)}`;
    row.appendChild(badge);
    row.appendChild(label);
    if (p.status === "pending") {
      const approve = document.createElement("button");
      approve.textContent = "✓";
      approve.style.cssText = "font-size:9px;padding:0 3px;cursor:pointer;margin-left:4px;";
      approve.onclick = async () => {
        await apiFetch(`/api/dynamic/drive_proposals/${p.id}/approve`, {method:"POST"}).catch(()=>null);
        refreshDriveProposals();
      };
      const reject = document.createElement("button");
      reject.textContent = "✗";
      reject.style.cssText = "font-size:9px;padding:0 3px;cursor:pointer;";
      reject.onclick = async () => {
        await apiFetch(`/api/dynamic/drive_proposals/${p.id}/reject`, {method:"POST"}).catch(()=>null);
        refreshDriveProposals();
      };
      row.appendChild(approve);
      row.appendChild(reject);
    }
    feed.appendChild(row);
  }
}

// ── Polling ───────────────────────────────────────────────────────────────────

async function pollFast() {
  try {
    await Promise.all([refreshSense(), refreshPipeline()]);
  } catch (_) {}
}

async function pollMedium() {
  try {
    await Promise.all([
      refreshBonsai(),
      refreshFountain(),
      refreshFeedsStatus(),
      refreshBeliefStats(),
      refreshMembraneSnapshot(),
      refreshDriveProposals(),
    ]);
  } catch (_) {}
}

async function pollSlow() {
  try {
    await Promise.all([refreshSystemStatus(), checkAdminState(), refreshVoiceMode()]);
  } catch (_) {}
}

// ── Speech ────────────────────────────────────────────────────────────────────

async function pollSpeech() {
  try {
    const data = await apiFetch("/api/speech/status");
    const ind   = document.getElementById("speech-indicator");
    const icon  = document.getElementById("speech-icon");
    const depth = document.getElementById("speech-depth");
    if (!ind || !icon) return;
    if (data.enabled) {
      ind.classList.remove("paused");
      icon.textContent = "🔊";
    } else {
      ind.classList.add("paused");
      icon.textContent = "🔇";
    }
    if (depth) depth.textContent = data.queue_depth > 0 ? `[${data.queue_depth}]` : "";
  } catch (_) {}
}

document.addEventListener("click", async (e) => {
  const indicator = e.target.closest("#speech-indicator");
  if (!indicator) return;
  e.stopPropagation();
  e.preventDefault();
  try {
    const data = await apiFetch("/api/speech/status");
    const path = data.enabled ? "/api/speech/pause" : "/api/speech/resume";
    await apiFetch(path, { method: "POST" });
    pollSpeech();
  } catch (err) {
    console.error("Speech toggle failed:", err);
  }
});

// Initial load
pollFast();
pollMedium();
pollSlow();
pollAgi();
pollSpeech();
refreshProblems();

// Intervals
setInterval(pollFast,        2000);
setInterval(pollMedium,      5000);
setInterval(pollSlow,       10000);
setInterval(pollAgi,        30000);
setInterval(pollSpeech,      5000);
setInterval(refreshProblems, 30000);

// --- Mode selector ---
async function loadModes() {
  try {
    const [listData, currentData] = await Promise.all([
      apiFetch("/api/mode/list"),
      apiFetch("/api/mode/current"),
    ]);
    const sel = document.getElementById("mode-select");
    sel.innerHTML = "";
    (listData.modes || []).forEach(m => {
      const opt = document.createElement("option");
      opt.value = m.name;
      opt.textContent = m.display_name;
      opt.title = m.description;
      if (m.name === currentData.name) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.warn("Mode load failed:", err);
  }
}

document.getElementById("mode-select").addEventListener("change", async (e) => {
  try {
    await apiFetch("/api/mode/set", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ name: e.target.value }) });
  } catch (err) {
    console.error("Mode set failed:", err);
    loadModes(); // revert
  }
});

loadModes();

// --- Voice selector ---
async function loadVoices() {
  try {
    const [listData, currentData] = await Promise.all([
      apiFetch("/api/voice/list"),
      apiFetch("/api/voice/current"),
    ]);
    const sel = document.getElementById("voice-select");
    sel.innerHTML = "";
    (listData.voices || []).forEach(v => {
      const opt = document.createElement("option");
      opt.value = v.id;
      opt.textContent = v.display_name;
      opt.title = v.description || "";
      if (v.id === currentData.id) opt.selected = true;
      sel.appendChild(opt);
    });
  } catch (err) {
    console.warn("Voice load failed:", err);
  }
}

document.getElementById("voice-select").addEventListener("change", async (e) => {
  try {
    await apiFetch("/api/voice/set", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ id: e.target.value }) });
  } catch (err) {
    console.error("Voice set failed:", err);
    loadVoices(); // revert
  }
});

loadVoices();

// --- Signals panel ---
async function loadSignals() {
  try {
    const data = await apiFetch("/api/signals/recent?limit=10");
    const el = document.getElementById("signals-feed");
    const meta = document.getElementById("signals-meta");
    if (!el) return;

    const patterns = data.patterns || [];
    const signals = data.signals || [];

    if (meta) meta.textContent = `${patterns.length} patterns · ${signals.length} signals`;

    if (patterns.length === 0) {
      el.innerHTML = '<span style="color:var(--fg3)">No patterns matched yet.</span>';
      return;
    }

    let html = "";
    for (const p of patterns.slice(0, 5)) {
      const t = new Date(p.matched_at * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"});
      const validated = p.validated_at
        ? ` · score: ${p.outcome_score != null ? p.outcome_score.toFixed(2) : "?"}`
        : " · pending";
      html += `<div style="margin-bottom:3px;border-left:2px solid var(--accent);padding-left:4px;">` +
        `<span style="color:var(--fg3)">${t}</span> ` +
        `<span style="color:var(--accent)">${p.template_name}</span>` +
        `<span style="color:var(--fg3)">${validated}</span>` +
        `<div style="color:var(--fg2);margin-top:1px;">${p.prediction}</div>` +
        `</div>`;
    }
    el.innerHTML = html;
  } catch (err) {
    console.warn("Load signals failed:", err);
  }
}

setInterval(loadSignals, 30000);
loadSignals();

// --- Diversity panel ---
async function loadDiversity() {
  try {
    const data = await apiFetch("/api/diversity/overview");
    const el = document.getElementById("diversity-feed");
    const meta = document.getElementById("diversity-meta");
    if (!el) return;
    const lines = [];

    if (data.top_collisions && data.top_collisions.length > 0) {
      lines.push('<span style="color:var(--accent)">crossbreeds</span>');
      data.top_collisions.slice(0, 3).forEach(c => {
        const grade = c.grade != null ? c.grade.toFixed(2) : "?";
        const snippet = (c.content || "").substring(0, 70);
        lines.push(`<span style="color:var(--fg)">${grade}</span> — ${snippet}`);
      });
    }

    if (data.groove_alerts && data.groove_alerts.length > 0) {
      lines.push('<span style="color:var(--warn,#e5a)">groove alerts</span>');
      data.groove_alerts.slice(0, 2).forEach(g => {
        lines.push(`${g.alert_type} (sev ${(g.severity||0).toFixed(2)}): ${g.pattern||""}`);
      });
    }

    if (data.dormant && data.dormant.length > 0) {
      lines.push('<span style="color:var(--fg2)">dormant territory</span>');
      data.dormant.slice(0, 3).forEach(d => {
        const score = d.dormancy_score != null ? d.dormancy_score.toFixed(2) : "?";
        const snippet = (d.content || "").substring(0, 60);
        lines.push(`${score} — ${snippet}`);
      });
    }

    if (data.grader_versions && data.grader_versions.length > 0) {
      const w = data.grader_versions[0];
      const v = w.version != null ? `v${w.version}` : "";
      lines.push(
        `<span style="color:var(--fg2)">grader weights ${v}:</span> ` +
        `in=${(w.w_input_distance||0).toFixed(2)} ` +
        `out=${(w.w_output_distance||0).toFixed(2)} ` +
        `rare=${(w.w_rarity||0).toFixed(2)}`
      );
    }

    el.innerHTML = lines.join("<br>");
    if (meta) meta.textContent = data.top_collisions && data.top_collisions.length > 0
      ? `${data.top_collisions.length} collisions`
      : "—";
  } catch (err) {
    console.warn("Load diversity failed:", err);
  }
}

setInterval(loadDiversity, 30000);
loadDiversity();

// --- Arcs panel ---
async function loadArcs() {
  try {
    const data = await apiFetch("/api/arcs/recent");
    const el = document.getElementById("arcs-feed");
    const meta = document.getElementById("arcs-meta");
    if (!el) return;

    const arcs = data.arcs || [];
    if (arcs.length === 0) {
      el.innerHTML = '<span style="color:var(--fg2)">no arcs yet</span>';
      if (meta) meta.textContent = "—";
      return;
    }

    const lines = arcs.slice(0, 8).map(a => {
      const ts = a.last_active_at
        ? new Date(a.last_active_at * 1000).toLocaleTimeString([], {hour: "2-digit", minute: "2-digit"})
        : "—";
      const type = a.arc_type === "progression" ? "prog" : "rtrn";
      const closed = a.closed_by_belief_id ? " ✓" : "";
      const theme = (a.theme_summary || "").substring(0, 55);
      const grade = a.quality_grade != null ? a.quality_grade.toFixed(2) : "?";
      return `<span style="color:var(--fg2)">${ts}</span> · <span style="color:var(--accent)">${type}</span> · ${a.member_count}f · ${grade} · ${theme}${closed}`;
    });
    el.innerHTML = lines.join("<br>");
    if (meta) meta.textContent = `${arcs.length} arc${arcs.length !== 1 ? "s" : ""}`;
  } catch (err) {
    console.warn("Load arcs failed:", err);
  }
}

setInterval(loadArcs, 60000);
loadArcs();

// ── Fountain tag buttons (coincidence tracking) ───────────────────────────
(function wireFountainTagButtons() {
  ["coin","maybe","non"].forEach(tag => {
    const btn = document.getElementById(`ftn-tag-${tag}`);
    if (!btn) return;
    btn.addEventListener("click", async () => {
      if (!_ftnCurrentId) {
        console.warn("no current fountain id to tag");
        return;
      }
      try {
        const resp = await fetch("/api/coincidence/tag", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({fountain_event_id: _ftnCurrentId, tag})
        });
        if (resp.ok) {
          const el = document.getElementById("fountain-thought");
          if (el) {
            const text = el.textContent.split(" : ")[0];
            el.textContent = text + " : " + tag;
            el.classList.remove("ftn-tagged-coin","ftn-tagged-maybe","ftn-tagged-non");
            el.classList.add(`ftn-tagged-${tag}`);
          }
          ["coin","maybe","non"].forEach(t => {
            const b = document.getElementById(`ftn-tag-${t}`);
            if (b) b.classList.toggle("active", t === tag);
          });
        } else {
          console.error("tag failed", await resp.text());
        }
      } catch (err) {
        console.error("tag exception", err);
      }
    });
  });
})();

// ── COINCIDENCE LAB ─────────────────────────────────────────────────────
async function refreshCoinLab() {
  try {
    const [stats, analytics, hyps] = await Promise.all([
      fetch("/api/coincidence/stats").then(r => r.json()),
      fetch("/api/coincidence/analytics").then(r => r.json()),
      fetch("/api/hypothesis").then(r => r.json()),
    ]);
    _coinlabRenderSummary(stats);
    _coinlabRenderByHour(stats);
    _coinlabRenderByBranch(analytics);
    _coinlabRenderAperture(analytics);
    _coinlabRenderTrigrams(analytics);
    _coinlabRenderFingerprint(analytics);
    _coinlabRenderHypotheses(hyps);
  } catch (err) {
    console.error("coinlab refresh failed", err);
  }
}

function _coinlabRenderSummary(stats) {
  const el = document.getElementById("coinlab-summary");
  if (!el) return;
  const c = stats.counts || {};
  const total = stats.total_tagged || 0;
  const coins = c.coin || 0;
  const rate = total > 0 ? (coins / total * 100).toFixed(1) : "0.0";
  el.innerHTML = `
    <div class="coinlab-h">SUMMARY</div>
    <div class="coinlab-grid">
      <div><span class="coin-label coin-coin-lbl">coin</span> <b>${coins}</b></div>
      <div><span class="coin-label coin-maybe-lbl">maybe</span> <b>${c.maybe || 0}</b></div>
      <div><span class="coin-label coin-non-lbl">non</span> <b>${c.non || 0}</b></div>
      <div>tagged: <b>${total}</b> / ${stats.total_fountain || 0}</div>
      <div>hit rate: <b>${rate}%</b></div>
    </div>
  `;
}

function _coinlabRenderByHour(stats) {
  const el = document.getElementById("coinlab-byhour");
  if (!el) return;
  const buckets = stats.by_hour || {};
  if (Object.keys(buckets).length === 0) {
    el.innerHTML = `<div class="coinlab-h">BY HOUR</div><div class="coinlab-empty">no data yet</div>`;
    return;
  }
  let rows = "";
  for (let h = 0; h < 24; h++) {
    const b = buckets[h] || {coin: 0, maybe: 0, non: 0};
    const total = b.coin + b.maybe + b.non;
    if (total === 0) continue;
    const maxBar = 20;
    const cb = "█".repeat(Math.min(maxBar, b.coin));
    const mb = "▒".repeat(Math.min(maxBar, b.maybe));
    const nb = "░".repeat(Math.min(maxBar, b.non));
    rows += `<div class="coinlab-row">
      <span class="coinlab-hour">${String(h).padStart(2,"0")}:00</span>
      <span class="coinlab-bar coin-coin-lbl">${cb}</span><span class="coinlab-bar coin-maybe-lbl">${mb}</span><span class="coinlab-bar coin-non-lbl">${nb}</span>
      <span class="coinlab-n">${total}</span>
    </div>`;
  }
  el.innerHTML = `<div class="coinlab-h">BY HOUR</div>${rows}`;
}

function _coinlabRenderByBranch(analytics) {
  const el = document.getElementById("coinlab-bybranch");
  if (!el) return;
  const branches = analytics.by_branch || {};
  if (Object.keys(branches).length === 0) {
    el.innerHTML = `<div class="coinlab-h">BY BRANCH</div><div class="coinlab-empty">no data yet</div>`;
    return;
  }
  const rows = Object.entries(branches).map(([b, t]) => {
    const total = (t.coin || 0) + (t.maybe || 0) + (t.non || 0);
    const coinRate = total > 0 ? (t.coin / total * 100).toFixed(0) : "0";
    return `<div class="coinlab-row">
      <span class="coinlab-branch">${esc(b)}</span>
      <span class="coin-coin-lbl">c:${t.coin || 0}</span>
      <span class="coin-maybe-lbl">m:${t.maybe || 0}</span>
      <span class="coin-non-lbl">n:${t.non || 0}</span>
      <span class="coinlab-rate">${coinRate}% hit</span>
    </div>`;
  }).join("");
  el.innerHTML = `<div class="coinlab-h">BY BRANCH</div>${rows}`;
}

function _coinlabRenderAperture(analytics) {
  const el = document.getElementById("coinlab-aperture");
  if (!el) return;
  const s = analytics.aperture_summary || {};
  const fmt = v => (v == null ? "—" : v.toFixed(3));
  el.innerHTML = `<div class="coinlab-h">APERTURE AT TAG-TIME</div>
    <div class="coinlab-grid">
      <div><span class="coin-coin-lbl">coin</span> (n=${s.coin?.n || 0}): mean <b>${fmt(s.coin?.mean)}</b> [${fmt(s.coin?.min)}–${fmt(s.coin?.max)}]</div>
      <div><span class="coin-maybe-lbl">maybe</span> (n=${s.maybe?.n || 0}): mean <b>${fmt(s.maybe?.mean)}</b> [${fmt(s.maybe?.min)}–${fmt(s.maybe?.max)}]</div>
      <div><span class="coin-non-lbl">non</span> (n=${s.non?.n || 0}): mean <b>${fmt(s.non?.mean)}</b> [${fmt(s.non?.min)}–${fmt(s.non?.max)}]</div>
    </div>`;
}

function _coinlabRenderTrigrams(analytics) {
  const el = document.getElementById("coinlab-trigrams");
  if (!el) return;
  const tris = analytics.top_trigrams_in_coins || [];
  if (tris.length === 0) {
    el.innerHTML = `<div class="coinlab-h">TOP TRIGRAMS IN COINS</div><div class="coinlab-empty">no coins tagged yet</div>`;
    return;
  }
  const rows = tris.map(([phrase, n]) =>
    `<div class="coinlab-row"><span class="coinlab-tri">${esc(phrase)}</span><span class="coinlab-n">${n}</span></div>`
  ).join("");
  el.innerHTML = `<div class="coinlab-h">TOP TRIGRAMS IN COINS</div>${rows}`;
}

function _coinlabRenderFingerprint(analytics) {
  const el = document.getElementById("coinlab-fingerprint");
  if (!el) return;
  const f = analytics.coin_fingerprint || {};
  if (!f.n) {
    el.innerHTML = `<div class="coinlab-h">COIN FINGERPRINT</div><div class="coinlab-empty">no coins tagged yet — fingerprint emerges from 3+ coins</div>`;
    return;
  }
  const branchRows = Object.entries(f.branch_freq || {})
    .sort((a, b) => b[1] - a[1])
    .map(([b, n]) => `<span class="coinlab-pill">${esc(b)} (${n})</span>`).join(" ");
  const daemonRows = (f.common_recent_daemons || [])
    .map(([d, n]) => `<span class="coinlab-pill">${esc(d || "?")} (${n})</span>`).join(" ");
  el.innerHTML = `<div class="coinlab-h">COIN FINGERPRINT (n=${f.n})</div>
    <div class="coinlab-grid">
      <div>avg aperture: <b>${f.avg_aperture != null ? f.avg_aperture.toFixed(3) : "—"}</b></div>
      <div>avg fires last 1h: <b>${f.avg_belief_delta_1h != null ? f.avg_belief_delta_1h.toFixed(1) : "—"}</b></div>
      <div>branches: ${branchRows || "—"}</div>
      <div>daemons fired near coins: ${daemonRows || "—"}</div>
    </div>`;
}

function _coinlabRenderHypotheses(hyps) {
  const el = document.getElementById("coinlab-hypotheses");
  if (!el) return;
  const list = (hyps && hyps.hypotheses) || [];
  let formHTML = `
    <div class="coinlab-form">
      <input type="text" id="hyp-claim" placeholder="claim (e.g. tea coincidences cluster after 21:00)" />
      <input type="text" id="hyp-keywords" placeholder="keywords (comma-separated)" />
      <input type="text" id="hyp-window" placeholder="time window (e.g. 21:00-23:00)" />
      <button id="hyp-create-btn">create</button>
    </div>`;
  let rows = "";
  for (const h of list) {
    const total = (h.supporting || 0) + (h.contradicting || 0);
    const score = total > 0 ? ((h.supporting / total) * 100).toFixed(0) : "—";
    rows += `<div class="coinlab-hyp coinlab-hyp-${h.status}">
      <div class="coinlab-hyp-claim">${esc(h.claim || "")}</div>
      <div class="coinlab-hyp-meta">
        keywords: ${esc(h.keywords || "—")} · window: ${esc(h.time_window || "—")} · status: ${h.status}
      </div>
      <div class="coinlab-hyp-counts">
        <span class="coin-coin-lbl">+${h.supporting || 0}</span>
        <span class="coin-non-lbl">-${h.contradicting || 0}</span>
        score: <b>${score}${total > 0 ? "%" : ""}</b>
        <span style="margin-left:auto">
          <button class="coinlab-hyp-btn" data-hid="${h.id}" data-action="confirmed">confirm</button>
          <button class="coinlab-hyp-btn" data-hid="${h.id}" data-action="refuted">refute</button>
          <button class="coinlab-hyp-btn" data-hid="${h.id}" data-action="abandoned">abandon</button>
        </span>
      </div>
    </div>`;
  }
  el.innerHTML = `<div class="coinlab-h">HYPOTHESES</div>${formHTML}${rows || '<div class="coinlab-empty">no hypotheses yet</div>'}`;
  // Wire create button
  const createBtn = document.getElementById("hyp-create-btn");
  if (createBtn) {
    createBtn.addEventListener("click", async () => {
      const claim = document.getElementById("hyp-claim").value.trim();
      const keywords = document.getElementById("hyp-keywords").value.trim();
      const time_window = document.getElementById("hyp-window").value.trim() || null;
      if (!claim) { alert("claim required"); return; }
      try {
        const r = await fetch("/api/hypothesis", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({claim, keywords, time_window})
        });
        if (r.ok) refreshCoinLab();
      } catch (e) { console.error(e); }
    });
  }
  // Wire status-change buttons
  el.querySelectorAll(".coinlab-hyp-btn").forEach(btn => {
    btn.addEventListener("click", async () => {
      const hid = btn.dataset.hid;
      const action = btn.dataset.action;
      try {
        const r = await fetch(`/api/hypothesis/${hid}`, {
          method: "PATCH",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({status: action})
        });
        if (r.ok) refreshCoinLab();
      } catch (e) { console.error(e); }
    });
  });
}

document.getElementById("coinlab-refresh-btn")?.addEventListener("click", refreshCoinLab);


// ── Compute pause button (SIGSTOP self) ───────────────────────────────────
document.getElementById("compute-pause-btn")?.addEventListener("click", async () => {
  if (!confirm("Pause NEX (SIGSTOP)? GUI will freeze. Resume from terminal with:\n  kill -CONT $(cat /tmp/nex5.pid)")) return;
  try { await fetch("/api/compute/pause", {method: "POST"}); } catch (e) { /* expected: process froze before responding */ }
});


// ── Decoder panel ─────────────────────────────────────────────────────────
let decoderActiveTab = "live";
let decoderLiveTimer = null;
let decoderTopLoaded = false;

function _decoderSetTab(tab) {
  decoderActiveTab = tab;
  document.querySelectorAll(".decoder-tab").forEach(btn => {
    btn.classList.toggle("active", btn.dataset.dtab === tab);
  });
  document.getElementById("decoder-tab-live")?.classList.toggle("active", tab === "live");
  document.getElementById("decoder-tab-top")?.classList.toggle("active", tab === "top");
  document.getElementById("decoder-tab-word")?.classList.toggle("active", tab === "word");
  if (tab === "live") refreshDecoderLive();
  if (tab === "top" && !decoderTopLoaded) refreshDecoderTop();
}

async function refreshDecoderLive() {
  try {
    const r = await fetch("/api/decoder/recent?limit=15");
    const d = await r.json();
    const el = document.getElementById("decoder-tab-live");
    if (!el || !d.recent) return;
    if (d.recent.length === 0) {
      el.innerHTML = '<div class="decoder-empty">no fires logged yet</div>';
      return;
    }
    el.innerHTML = d.recent.map(f => {
      const ts = new Date(f.ts * 1000).toLocaleTimeString("en-GB", {hour: "2-digit", minute: "2-digit", second: "2-digit"});
      const tagClass = f.tag ? ` tag-${f.tag}` : "";
      const tagLabel = f.tag ? ` [${f.tag}]` : "";
      const words = (f.words || []).slice(0, 12).map(w =>
        `<span class="decoder-word-chip" data-word="${esc(w)}">${esc(w)}</span>`
      ).join(" ");
      return `<div class="decoder-fire${tagClass}">
        <div class="decoder-fire-head">
          <span class="decoder-fid">#${f.fid}</span>
          <span class="decoder-ts">${ts}</span>
          <span class="decoder-tag">${tagLabel}</span>
        </div>
        <div class="decoder-thought">${esc(f.thought)}</div>
        <div class="decoder-words">${words}</div>
      </div>`;
    }).join("");
    // Wire word chips to jump to WORD tab
    el.querySelectorAll(".decoder-word-chip").forEach(chip => {
      chip.addEventListener("click", () => {
        document.getElementById("decoder-word-input").value = chip.dataset.word;
        _decoderSetTab("word");
        refreshDecoderWord(chip.dataset.word);
      });
    });
    document.getElementById("decoder-meta").textContent = `${d.recent.length} recent fires`;
  } catch (e) { console.error("decoder live failed", e); }
}

async function refreshDecoderTop() {
  try {
    const r = await fetch("/api/decoder/top?limit=50");
    const d = await r.json();
    const el = document.getElementById("decoder-tab-top");
    if (!el || !d.top) return;
    decoderTopLoaded = true;
    if (d.top.length === 0) {
      el.innerHTML = '<div class="decoder-empty">no words logged yet</div>';
      return;
    }
    const maxN = d.top[0].n;
    el.innerHTML = `<div class="decoder-top-list">${
      d.top.map(w => {
        const barW = Math.max(2, Math.round((w.n / maxN) * 80));
        return `<div class="decoder-top-row" data-word="${esc(w.word)}">
          <span class="decoder-top-word">${esc(w.word)}</span>
          <span class="decoder-top-bar" style="width:${barW}px"></span>
          <span class="decoder-top-n">${w.n}</span>
        </div>`;
      }).join("")
    }</div>`;
    el.querySelectorAll(".decoder-top-row").forEach(row => {
      row.addEventListener("click", () => {
        document.getElementById("decoder-word-input").value = row.dataset.word;
        _decoderSetTab("word");
        refreshDecoderWord(row.dataset.word);
      });
    });
    document.getElementById("decoder-meta").textContent = `top ${d.top.length}`;
  } catch (e) { console.error("decoder top failed", e); }
}

async function refreshDecoderWord(word) {
  if (!word) return;
  word = word.trim().toLowerCase();
  const el = document.getElementById("decoder-word-result");
  if (!el) return;
  el.innerHTML = '<div class="decoder-empty">loading...</div>';
  try {
    const r = await fetch(`/api/decoder/word/${encodeURIComponent(word)}`);
    if (r.status === 404) {
      el.innerHTML = `<div class="decoder-empty">word "${esc(word)}" not in dictionary yet</div>`;
      return;
    }
    const d = await r.json();
    if (d.error) { el.innerHTML = `<div class="decoder-empty">${esc(d.error)}</div>`; return; }
    const fmt = v => (v == null || isNaN(v)) ? "—" : v;
    const fmtSecs = v => {
      if (v == null || isNaN(v)) return "—";
      if (v < 60) return `${Math.round(v)}s`;
      if (v < 3600) return `${Math.round(v/60)}m`;
      return `${(v/3600).toFixed(1)}h`;
    };
    const branches = (d.top_branches || []).map(b =>
      `<span class="decoder-pill">${esc(b.hot_branch)} (${b.n})</span>`
    ).join(" ");
    const tagsHtml = Object.entries(d.tags || {}).map(([t, n]) =>
      `<span class="decoder-pill tag-${t}">${esc(t)}: ${n}</span>`
    ).join(" ");
    const samples = (d.sample_thoughts || []).map(s =>
      `<div class="decoder-sample">"${esc(s)}"</div>`
    ).join("");
    el.innerHTML = `
      <div class="decoder-word-head">"${esc(d.word)}" <span class="decoder-word-n">(used ${d.count} times)</span></div>
      <div class="decoder-fingerprint">
        <div class="decoder-fpr"><span class="decoder-fp-k">avg hour:</span> <b>${fmt(d.avg_hour)}</b></div>
        <div class="decoder-fpr"><span class="decoder-fp-k">aperture:</span> <b>${fmt(d.aperture?.avg)}</b> [${fmt(d.aperture?.min)}–${fmt(d.aperture?.max)}]</div>
        <div class="decoder-fpr"><span class="decoder-fp-k">since last daemon:</span> <b>${fmtSecs(d.avg_secs_daemon)}</b></div>
        <div class="decoder-fpr"><span class="decoder-fp-k">since last feed:</span> <b>${fmtSecs(d.avg_secs_feed)}</b></div>
        <div class="decoder-fpr"><span class="decoder-fp-k">active branches:</span> <b>${fmt(d.avg_active_branches)}</b></div>
        <div class="decoder-fpr"><span class="decoder-fp-k">fires last 1h:</span> <b>${fmt(d.avg_fires_1h)}</b></div>
      </div>
      <div class="decoder-section"><span class="decoder-fp-k">branches:</span> ${branches || "—"}</div>
      <div class="decoder-section"><span class="decoder-fp-k">tags:</span> ${tagsHtml || "(untagged)"}</div>
      <div class="decoder-section"><span class="decoder-fp-k">samples:</span>${samples}</div>
    `;
    document.getElementById("decoder-meta").textContent = `"${d.word}" — ${d.count} uses`;
  } catch (e) { el.innerHTML = `<div class="decoder-empty">error: ${esc(e.message || e)}</div>`; }
}

document.querySelectorAll(".decoder-tab").forEach(btn => {
  btn.addEventListener("click", () => _decoderSetTab(btn.dataset.dtab));
});
document.getElementById("decoder-word-go")?.addEventListener("click", () => {
  refreshDecoderWord(document.getElementById("decoder-word-input").value);
});
document.getElementById("decoder-word-input")?.addEventListener("keydown", e => {
  if (e.key === "Enter") { e.preventDefault(); refreshDecoderWord(e.target.value); }
});

// Initial load + poll LIVE every 20s
refreshDecoderLive();
decoderLiveTimer = setInterval(() => { if (decoderActiveTab === "live") refreshDecoderLive(); }, 20000);
