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

// ── Pipeline ─────────────────────────────────────────────────────────────────

let lastPipeId = 0;

async function refreshPipeline() {
  const data = await apiFetch("/api/dynamic/pipeline").catch(() => null);
  if (!data || data.error) return;

  const events = (data.events || []).filter(e => e.id > lastPipeId);
  if (!events.length) return;

  const feed = document.getElementById("pipeline-feed");
  events.forEach(ev => {
    lastPipeId = Math.max(lastPipeId, ev.id);
    const valCls = ev.valence === "like" ? "valence-like"
                 : ev.valence === "dislike" ? "valence-dislike"
                 : "valence-neutral";
    const valTxt = ev.valence || "";
    const mag = ev.magnitude != null ? magBar(ev.magnitude) : "";

    const row = document.createElement("div");
    row.className = "pipe-row";
    row.innerHTML = `<span class="pipe-ts">${fmtTs(ev.ts)}</span>`
      + `<span class="pipe-step step-${ev.step}">${esc(ev.step)}</span>`
      + `<span class="pipe-branch">${esc(ev.branch_id || "")}</span>`
      + `<span class="pipe-mag">${mag}</span>`
      + `<span class="pipe-valence ${valCls}">${esc(valTxt)}</span>`
      + `<span class="pipe-src">${esc((ev.sensation_source || "").slice(0, 30))}</span>`;
    feed.prepend(row);
  });

  while (feed.children.length > MAX_ROWS) feed.lastChild.remove();
}

// ── Fountain ──────────────────────────────────────────────────────────────────

async function refreshFountain() {
  const data = await apiFetch("/api/fountain/status").catch(() => null);
  if (!data || data.error) return;

  const el = document.getElementById("fountain-thought");
  if (data.last_thought) {
    el.textContent = data.last_thought;
    el.classList.remove("empty");
  }

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
}

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
  log.innerHTML = agiSignals.slice(0, 200).map(s =>
    `<div class="agi-log-row">`
    + `<span class="agi-log-ts">${fmtTs(s.ts)}</span>`
    + `<span class="agi-log-type ${_agiTypeClass(s.type)}">${s.type}</span>`
    + `<span class="agi-log-txt">${esc(s.excerpt)}</span>`
    + `</div>`
  ).join("");
}

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
  if (tab === "insights") refreshInsights();
}

function _agiShowSignal(type, ts, excerpt) {
  const msg    = document.getElementById("agi-strip-msg");
  const count  = document.getElementById("agi-sig-count");
  const status = document.getElementById("agi-status");
  if (!msg) return;

  agiSignals.unshift({ type, ts, excerpt });
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
          `Tier ${b.tier}: ${(b.content || "").slice(0, 80)}`);
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
          resp.slice(0, 80));
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
    await Promise.all([refreshSystemStatus(), checkAdminState()]);
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
