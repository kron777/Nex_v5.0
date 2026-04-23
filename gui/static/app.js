// NEX 5.0 cockpit — vanilla JS. Phase 3: dynamic + bonsai + crystallization panels.

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

// ---- Phase 7 — fountain ----------------------------------------------------

async function refreshFountain() {
  const data = await j("/api/fountain/status").catch(() => null);
  if (!data || data.error) return;

  const el = document.getElementById("fountain-last-thought");
  if (data.last_thought) {
    el.textContent = data.last_thought;
    el.classList.remove("muted");
  }

  document.getElementById("fountain-fire-count").textContent =
    data.total_fires ? `(${data.total_fires} fires)` : "";
  document.getElementById("fountain-last-fire").textContent =
    data.last_fire_ts ? fmtTs(data.last_fire_ts) : "never";
  document.getElementById("fountain-readiness").textContent =
    data.readiness_score != null ? data.readiness_score.toFixed(2) : "—";
}

// ---- Phase 6 — system status / self-location -------------------------------

async function refreshSystemStatus() {
  const data = await j("/api/system/status").catch(() => null);
  if (!data) return;
  const el = document.getElementById("boot-status");
  if (!el) return;
  const parts = [
    ["scheduler",  data.scheduler],
    ["dynamic",    data.dynamic],
    ["world",      data.world_model],
    ["membrane",   data.membrane],
    ["self-loc",   data.self_location_committed],
  ];
  el.innerHTML = parts
    .map(([k, v]) => `<span class="${v ? "state-on" : "state-off"}">${k} ${v ? "✓" : "✗"}</span>`)
    .join(" | ");
}

// ---- Phase 5 — membrane / inside-outside -----------------------------------

async function refreshMembrane() {
  const [snapData, recentData] = await Promise.all([
    j("/api/membrane/snapshot").catch(() => null),
    j("/api/sense/recent?limit=20").catch(() => ({ events: [] })),
  ]);

  // Inside column
  const inside = document.getElementById("membrane-inside");
  if (snapData && !snapData.error) {
    const prop = snapData.proprioception || {};
    const temp = snapData.temporal || {};
    const intro = snapData.interoception || {};
    const attn = snapData.attention || {};
    const cpu = prop.cpu_percent != null ? `CPU ${prop.cpu_percent.toFixed(0)}%` : "—";
    const mem = prop.mem_percent != null ? `mem ${prop.mem_percent.toFixed(0)}%` : "—";
    const iso = temp.iso_local ? temp.iso_local.split("T")[1]?.slice(0,5) : "—";
    const hot = attn.hottest_branch ? `${attn.hottest_branch} (${(attn.hottest_focus||0).toFixed(2)})` : "—";
    inside.innerHTML = `
      <div class="membrane-row"><span class="membrane-label">Body</span>${escapeHtml(cpu)}, ${escapeHtml(mem)}</div>
      <div class="membrane-row"><span class="membrane-label">Time</span>${escapeHtml(iso)}</div>
      <div class="membrane-row"><span class="membrane-label">Beliefs</span>${intro.belief_count ?? 0} (${intro.locked_count ?? 0} locked)</div>
      <div class="membrane-row"><span class="membrane-label">Hot branch</span>${escapeHtml(hot)}</div>
      <div class="membrane-row"><span class="membrane-label">Active</span>${attn.active_branch_count ?? 0} branches</div>
    `;
  } else {
    inside.innerHTML = '<div class="muted">membrane not initialised</div>';
  }

  // Outside column — last 3 external events
  const outside = document.getElementById("membrane-outside");
  const externals = (recentData.events || [])
    .filter(ev => !ev.stream.startsWith("internal."))
    .slice(0, 3);
  if (externals.length === 0) {
    outside.innerHTML = '<div class="ev muted">no external events yet</div>';
  } else {
    outside.innerHTML = externals.map(ev => {
      let preview = "";
      try {
        const p = JSON.parse(ev.payload);
        preview = p.title || p.symbol || "";
      } catch (_) {}
      return `<div class="ev"><span class="ts">${fmtTs(ev.timestamp)}</span><span class="stream">${escapeHtml(ev.stream)}</span>${escapeHtml(String(preview).slice(0, 60))}</div>`;
    }).join("");
  }
}

// ---- Phase 4 — world model / belief stats ----------------------------------

async function refreshBeliefStats() {
  const data = await j("/api/beliefs/stats");
  if (data.error) return;
  const total = data.total || 0;
  document.getElementById("belief-total").textContent = `(${total} total)`;
  document.getElementById("belief-24h").textContent = data.added_last_24h ?? "—";
  const dist = data.tier_distribution || {};
  const container = document.getElementById("belief-tier-bars");
  const maxCount = Math.max(1, ...Object.values(dist));
  container.innerHTML = Object.entries(dist).map(([tier, cnt]) => {
    const pct = Math.round((cnt / maxCount) * 100);
    return `<div class="tier-bar-row"><span class="tier-label">T${tier}</span>`
      + `<div class="tier-bar-outer"><div class="tier-bar-inner" style="width:${pct}%"></div></div>`
      + `<span class="tier-count">${cnt}</span></div>`;
  }).join("");
}

// ---- Phase 3 — dynamic / bonsai / crystallization --------------------------

const HIGH_FOCUS = new Set(["e", "f", "g"]);

async function refreshDynamic() {
  const data = await j("/api/dynamic/status");
  if (data.error) return;

  document.getElementById("bonsai-aperture").textContent = data.aperture != null ? data.aperture.toFixed(3) : "—";
  document.getElementById("bonsai-consolidation").textContent = data.consolidation_active ? "active" : "idle";
  document.getElementById("bonsai-pipeline-runs").textContent = data.pipeline_runs ?? "—";
  document.getElementById("bonsai-summary").textContent =
    `(${data.active_branch_count}/${data.total_branches} active, focus: ${data.aggregate_focus}, texture: ${data.aggregate_texture})`;

  const tbody = document.querySelector("#bonsai-table tbody");
  const branches = (data.branches || []).slice().sort((a, b) => b.focus_num - a.focus_num);
  tbody.innerHTML = branches.map(b => {
    const highFocus = HIGH_FOCUS.has(b.focus_increment);
    const cls = highFocus ? ' class="focus-high"' : '';
    const lastAtt = b.last_attended_at ? fmtTs(b.last_attended_at) : "—";
    return `<tr${cls}>
      <td>${escapeHtml(b.branch_id)}${b.is_seed ? " <span class='muted'>seed</span>" : ""}</td>
      <td>${escapeHtml(b.focus_increment)} <span class="muted">(${b.focus_num.toFixed(3)})</span></td>
      <td>${escapeHtml(b.texture_increment)}</td>
      <td>${b.curiosity_weight}</td>
      <td class="muted">${lastAtt}</td>
    </tr>`;
  }).join("");
}

async function refreshCrystallized() {
  const data = await j("/api/dynamic/crystallized");
  const events = (data.events || []).slice(0, 10);
  const el = document.getElementById("crystallization-list");
  if (!events.length) { el.innerHTML = '<div class="ev muted">no crystallizations yet</div>'; return; }
  el.innerHTML = events.map(ev =>
    `<div class="ev"><span class="ts">${fmtTs(ev.ts)}</span><span class="stream">${escapeHtml(ev.branch_id)}</span>${escapeHtml((ev.content || "").slice(0, 80))}</div>`
  ).join("");
}

async function refreshBeliefs() {
  const data = await j("/api/beliefs/recent");
  const beliefs = (data.beliefs || []).slice(0, 10);
  const el = document.getElementById("beliefs-list");
  if (!beliefs.length) { el.innerHTML = '<div class="ev muted">no beliefs yet</div>'; return; }
  el.innerHTML = beliefs.map(b =>
    `<div class="ev"><span class="tier-badge tier-${b.tier}">T${b.tier}</span><span class="ts">${fmtTs(b.created_at)}</span>${escapeHtml((b.content || "").slice(0, 100))}<span class="muted"> [${escapeHtml(b.source || "")}]</span></div>`
  ).join("");
}

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

async function pollDynamic() {
  try {
    await Promise.all([
      refreshDynamic(), refreshCrystallized(), refreshBeliefs(),
      refreshBeliefStats(), refreshMembrane(),
    ]);
  } catch (e) { console.warn(e); }
}

poll();
pollSenseEvents();
pollDynamic();
refreshSystemStatus();
refreshFountain();
setInterval(poll,                POLL_MS);
setInterval(pollSenseEvents,     SENSE_MS);
setInterval(pollDynamic,         SENSE_MS);
setInterval(refreshSystemStatus, SENSE_MS);
setInterval(refreshFountain,     10000);
