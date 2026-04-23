// NEX 5.0 cockpit — minimal vanilla JS. Polls stat endpoints on an interval;
// handles admin login and chat column.

const POLL_MS = 2000;

async function j(url, opts) {
  const r = await fetch(url, opts);
  if (!r.ok && r.status !== 401) throw new Error(`${url} → ${r.status}`);
  return r.json();
}

function fmtTs(sec) {
  return new Date(sec * 1000).toLocaleTimeString();
}

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
    .slice()
    .reverse()
    .map(
      (e) =>
        `<div class="ev"><span class="ts">${fmtTs(e.timestamp)}</span><span class="lvl ${e.level}">${e.level}</span><span class="src">${e.source}</span>${escapeHtml(e.message)}${
          e.traceback ? `<pre>${escapeHtml(e.traceback)}</pre>` : ""
        }</div>`
    )
    .join("");
}

async function refreshAdmin() {
  const s = await j("/api/admin/status");
  const el = document.getElementById("admin-status");
  if (!s.configured) {
    el.textContent = "admin: not configured";
  } else if (s.authenticated) {
    el.textContent = "admin: authenticated";
  } else {
    el.textContent = "admin: locked";
  }
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

async function poll() {
  try {
    await Promise.all([refreshDbStats(), refreshQueues(), refreshErrors(), refreshAdmin()]);
  } catch (e) {
    console.warn(e);
  }
}

// Admin form
document.getElementById("admin-form").addEventListener("submit", async (ev) => {
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
  } catch (e) {
    fb.textContent = String(e);
  }
});

document.getElementById("admin-logout").addEventListener("click", async () => {
  await fetch("/api/admin/logout", { method: "POST" });
  document.getElementById("admin-feedback").textContent = "logged out";
  refreshAdmin();
});

// Chat form
document.getElementById("chat-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const input = document.getElementById("chat-input");
  const reg = document.getElementById("chat-register").value;
  const prompt = input.value.trim();
  if (!prompt) return;
  input.value = "";
  const log = document.getElementById("chat-log");
  log.insertAdjacentHTML(
    "beforeend",
    `<div class="u">&gt; ${escapeHtml(prompt)}</div>`
  );
  try {
    const r = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prompt, register: reg || undefined }),
    });
    const data = await r.json();
    log.insertAdjacentHTML(
      "beforeend",
      `<div class="n">${escapeHtml(data.text)}<span class="meta">[${data.register}${
        data.voice_ok ? "" : " • voice offline"
      }]</span></div>`
    );
    log.scrollTop = log.scrollHeight;
  } catch (e) {
    log.insertAdjacentHTML(
      "beforeend",
      `<div class="n">chat failed: ${escapeHtml(String(e))}</div>`
    );
  }
});

poll();
setInterval(poll, POLL_MS);
