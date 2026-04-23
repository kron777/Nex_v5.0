// NEX 5.0 — HUD app.js

// ── Helpers ──────────────────────────────────────────────────────────────────

async function apiFetch(url) {
  const r = await fetch(url);
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
      metaEl.textContent = `[${d.register}${d.voice_ok ? "" : " · voice offline"}]`;
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
  try {
    const r = await fetch("/api/strikes/fire", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ strike_type: type }),
    });
    const record = await r.json();
    status.textContent = `done (id=${record.id})`;
    openModal(record);
  } catch (e) {
    status.textContent = `failed: ${e}`;
  }
});

// ── AGI Watch ─────────────────────────────────────────────────────────────────

const _AGI_SELF_RE = /\b(i want|i am|i notice|i feel|i think|i wonder|i realize|i find|i see|i know|i have|i need|my )\b/i;

let agiSignals       = [];      // { type, ts, excerpt }
let agiLastFtnTs     = 0;       // last fountain event ts checked
let agiLastBeliefTs  = 0;       // last belief ts checked
let agiLastStrikeId  = 0;       // last strike id checked
let agiFtnTimestamps = [];      // all fountain fire timestamps (for ignition pattern)
let agiIgnitionFired = false;   // prevent re-firing ignition until reset
let agiCollapseTimer = null;
let agiUserExpanded  = false;   // manual toggle state

function _agiTypeClass(type) {
  return `agi-type-${type.replace(/[^A-Z_]/g, "")}`;
}

function _agiRenderLog() {
  const log = document.getElementById("agi-log");
  if (!log) return;
  log.innerHTML = agiSignals.slice(0, 60).map(s =>
    `<div class="agi-log-row">`
    + `<span class="agi-log-type ${_agiTypeClass(s.type)}">${s.type}</span>`
    + `<span class="agi-log-ts">${fmtTs(s.ts)}</span>`
    + `<span class="agi-log-txt">"${esc(s.excerpt.slice(0, 90))}"</span>`
    + `</div>`
  ).join("");
  log.scrollTop = 0;
}

function _agiShowSignal(type, ts, excerpt) {
  const panel  = document.getElementById("agi-watch");
  const msg    = document.getElementById("agi-strip-msg");
  const count  = document.getElementById("agi-sig-count");
  const status = document.getElementById("agi-status");
  if (!panel || !msg) return;

  agiSignals.unshift({ type, ts, excerpt });
  _agiRenderLog();

  count.textContent = `signals: ${agiSignals.length}`;
  status.textContent = "⚡";
  msg.innerHTML = `<span class="${_agiTypeClass(type)}">${type}</span>`
    + `<span class="agi-strip-ts">${fmtTs(ts)}</span>`
    + `<span class="agi-strip-txt">"${esc(excerpt.slice(0, 60))}"</span>`;

  if (!agiUserExpanded) {
    panel.classList.add("expanded");
    if (agiCollapseTimer) clearTimeout(agiCollapseTimer);
    agiCollapseTimer = setTimeout(() => {
      if (!agiUserExpanded) panel.classList.remove("expanded");
      agiCollapseTimer = null;
    }, 9000);
  }
}

document.getElementById("agi-watch")?.addEventListener("click", () => {
  const panel = document.getElementById("agi-watch");
  agiUserExpanded = !agiUserExpanded;
  if (agiUserExpanded) {
    panel.classList.add("expanded");
    if (agiCollapseTimer) { clearTimeout(agiCollapseTimer); agiCollapseTimer = null; }
  } else {
    panel.classList.remove("expanded");
  }
});

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
    ]);
  } catch (_) {}
}

async function pollSlow() {
  try {
    await Promise.all([refreshSystemStatus(), checkAdminState()]);
  } catch (_) {}
}

// Initial load
pollFast();
pollMedium();
pollSlow();
pollAgi();

// Intervals
setInterval(pollFast,   2000);
setInterval(pollMedium, 5000);
setInterval(pollSlow,   10000);
setInterval(pollAgi,    30000);
