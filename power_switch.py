#!/usr/bin/env python3
"""power_switch.py — NEX power control plane (always-on, GPU-free).

WHY this exists as a separate process:
    The HUD (gui/server.py) is served *inside* run.py — the same process that
    holds the RX6600's VRAM. Putting NEX to sleep means SIGTERM-ing run.py,
    which also kills the HUD. So the wake control cannot live on port 8765;
    it would die with her and could never bring her back. This tiny stdlib
    HTTP server stays up across standby, on its own port, holding no GPU.

Single source of truth: ~/.nex/STANDBY
    present  -> OFF (NEX should be asleep)
    absent   -> ON  (NEX should be running)
Both this switch and nex_keepalive.sh obey that file. This process never
respawns NEX; it only sets the sentinel and (on OFF) SIGTERMs the running
process. The supervisor enforces the sentinel from then on.

Endpoints (127.0.0.1:8766):
    GET  /          -> minimal page with the red/green pill
    GET  /power     -> {"state": "on"|"off"}
    POST /power     -> body {"action":"on"|"off"} (or omitted = toggle)
                       OFF: create STANDBY, then graceful SIGTERM the NEX pid
                       ON : delete STANDBY  (supervisor relaunches)
                       -> {"state": <new>}
"""
from __future__ import annotations

import json
import os
import signal
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOME = os.path.expanduser("~")
NEX_DIR = os.path.join(HOME, ".nex")
STANDBY = os.path.join(NEX_DIR, "STANDBY")
PIDFILE = os.path.join(NEX_DIR, "nex.pid")   # written by nex_keepalive.sh
# companion to PIDFILE: "pid:starttime:boot_id" for the SAME launch, also
# written by nex_keepalive.sh. PIDFILE itself stays a bare int (tools/
# nex_vitals.py reads it directly), so the identity triple lives alongside
# it rather than replacing it.
IDENTITY_FILE = os.path.join(NEX_DIR, "nex.pid.identity")
HOST = "127.0.0.1"
PORT = 8766

# This control plane can SIGTERM NEX, so a cross-site POST or a DNS-rebound
# page must never reach do_POST. We bind loopback AND verify Host (defeats DNS
# rebinding, where the attacker's page resolves its own name to 127.0.0.1) and
# Origin (defeats the "any page you visit" CSRF), and scope CORS to the real
# callers instead of the former wildcard. The HUD runs on 8765 by default but
# honours NEX5_GUI_PORT, so we mirror that here.
_HUD_PORT = os.environ.get("NEX5_GUI_PORT", "8765")
ALLOWED_ORIGINS = frozenset(
    f"http://{h}:{p}"
    for h in ("127.0.0.1", "localhost")
    for p in (str(PORT), _HUD_PORT)
)
ALLOWED_HOSTS = frozenset(f"{h}:{PORT}" for h in ("127.0.0.1", "localhost"))


def state() -> str:
    """"on" whenever the sentinel says ON. When it says OFF, this still
    checks the verified pid rather than trusting the sentinel alone: a
    just-signalled NEX can take a few seconds to actually exit, and during
    that window the sentinel is already written. Reporting a bare "off"
    then would be a lie the HUD pill repeats on every 2s poll, not just in
    the one POST response that triggered it -- "stopping" falls through
    the frontend's on/off switch to its existing neutral "wait" pill, no
    JS change needed."""
    if os.path.exists(STANDBY):
        return "off" if _read_pid() is None else "stopping"
    return "on"


def _boot_id() -> str | None:
    try:
        with open("/proc/sys/kernel/random/boot_id") as f:
            return f.read().strip()
    except OSError:
        return None


def _proc_starttime(pid: int) -> int | None:
    """Field 22 of /proc/<pid>/stat -- starttime in clock ticks since boot.
    comm (field 2) is parenthesised and may itself contain ')' or spaces, so
    this splits on the LAST ') ' rather than whitespace; field 22 is then
    token 20 (index 19) of what follows it."""
    try:
        with open(f"/proc/{pid}/stat") as f:
            raw = f.read()
        rest = raw.rsplit(") ", 1)[1]
        return int(rest.split()[19])
    except (OSError, IndexError, ValueError):
        return None


def _read_identity() -> tuple[int, int, str] | None:
    try:
        with open(IDENTITY_FILE) as f:
            pid_s, starttime_s, boot_id = f.read().strip().split(":", 2)
        return int(pid_s), int(starttime_s), boot_id
    except (OSError, ValueError):
        return None


def _read_pid() -> int | None:
    """The live NEX pid, verified against the (pid, starttime, boot_id)
    nex_keepalive.sh recorded at launch -- not just "does this pid exist".
    A bare existence check also "succeeds" on a stale pidfile whenever that
    pid number gets reused by an unrelated process (pids recycle) or by a
    NEW NEX launch after a reboot; starttime pins it to one process
    instance, boot_id catches the reboot case specifically. Any mismatch,
    missing field, or unreadable file is treated as "not running" -- fail
    open toward treating her as dead (supervisor relaunches) rather than
    toward silently acting on the wrong process.
    """
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
    except (OSError, ValueError):
        return None
    if pid <= 1:
        # 0 is this process's own pgid as a kill() target, -1 is "every
        # process we're allowed to signal", 1 is init. A corrupt or
        # adversarial pidfile could contain any of these; nothing
        # downstream should ever reach os.kill with one. Belt-and-braces
        # alongside the identity match below, which in practice already
        # excludes them (no real launch's $! is ever <= 1).
        return None

    identity = _read_identity()
    if identity is None or identity[0] != pid:
        return None
    _, rec_starttime, rec_boot_id = identity

    if not os.path.isdir(f"/proc/{pid}"):
        return None
    try:
        if os.stat(f"/proc/{pid}").st_uid != os.getuid():
            return None
    except OSError:
        return None

    if _proc_starttime(pid) != rec_starttime:
        return None
    if _boot_id() != rec_boot_id:
        return None

    return pid


def _sigterm_nex() -> dict:
    """Graceful SIGTERM to the NEX process; never SIGKILL from here.
    The supervisor owns escalation. We just ask her to stand down."""
    pid = _read_pid()
    if pid is None:
        return {"signalled": False, "reason": "no live nex pid"}
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        return {"signalled": False, "reason": str(e)}
    # brief confirmation window (her trap flushes dbs + releases GPU)
    for _ in range(20):
        try:
            os.kill(pid, 0)
        except OSError:
            return {"signalled": True, "pid": pid, "exited": True}
        time.sleep(0.5)
    return {"signalled": True, "pid": pid, "exited": False}


def go_off() -> dict:
    os.makedirs(NEX_DIR, exist_ok=True)
    with open(STANDBY, "w") as f:
        f.write(f"off since {time.strftime('%F %T')}\n")
    term = _sigterm_nex()
    # Not a hardcoded "off": if term["exited"] is False she's still
    # finishing her shutdown (or ignored the signal and needs the
    # supervisor's SIGKILL escalation), and state() will correctly say
    # "stopping" until a verified-dead read confirms otherwise.
    return {"state": state(), "term": term}


def go_on() -> dict:
    try:
        os.remove(STANDBY)
    except FileNotFoundError:
        pass
    return {"state": "on"}


PAGE = """<!doctype html><html><head><meta charset="utf-8">
<title>NEX power</title><meta name="viewport" content="width=device-width,initial-scale=1">
<style>
 :root{color-scheme:dark}
 body{margin:0;background:#0b0d10;color:#c8ccd2;font:15px/1.5 system-ui,sans-serif;
   display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;gap:22px}
 h1{font-size:13px;letter-spacing:.28em;color:#6b7280;font-weight:600;margin:0}
 .pill{--c:#555;cursor:pointer;user-select:none;border:none;border-radius:999px;
   padding:16px 40px;min-width:180px;font:700 22px/1 system-ui,sans-serif;letter-spacing:.14em;
   color:#fff;background:var(--c);box-shadow:0 0 0 1px #0006,0 0 26px -6px var(--c);
   transition:background .18s,box-shadow .18s;outline:none}
 .pill:active{transform:translateY(1px)}
 .pill.on{--c:#1f9d55}
 .pill.off{--c:#c0392b}
 .pill.wait{--c:#7a5c12;letter-spacing:.05em}
 .sub{font-size:12px;color:#5b6270}
</style></head><body>
 <h1>N E X&nbsp;&nbsp;P O W E R</h1>
 <button id="pill" class="pill wait" disabled>…</button>
 <div class="sub" id="sub">reading state…</div>
<script>
const API="";  // same origin (control server)
const pill=document.getElementById('pill'), sub=document.getElementById('sub');
let cur=null, busy=false;
function paint(s){
  cur=s;
  pill.classList.remove('on','off','wait');
  if(s==='on'){pill.classList.add('on');pill.textContent='ON';sub.textContent='NEX is awake — CPU/RAM in use';}
  else if(s==='off'){pill.classList.add('off');pill.textContent='OFF';sub.textContent='NEX asleep — CPU/RAM free';}
  else{pill.classList.add('wait');pill.textContent='…';}
  pill.disabled=false;
}
async function poll(){
  if(busy)return;
  try{const r=await fetch(API+'/power');const j=await r.json();paint(j.state);}catch(e){sub.textContent='switch unreachable';}
}
pill.onclick=async()=>{
  if(busy||!cur)return;
  busy=true;pill.disabled=true;
  const target=cur==='on'?'off':'on';
  pill.classList.remove('on','off');pill.classList.add('wait');
  pill.textContent=target==='off'?'sleeping…':'waking…';
  sub.textContent=target==='off'?'flushing dbs, releasing GPU…':'supervisor relaunching…';
  try{
    const r=await fetch(API+'/power',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({action:target})});
    const j=await r.json();paint(j.state);
  }catch(e){sub.textContent='request failed';}
  busy=false;
  // give the supervisor a moment, then resync
  setTimeout(poll,1500);
};
poll();setInterval(poll,2000);
</script></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _origin(self) -> str | None:
        return self.headers.get("Origin")

    def _host_ok(self) -> bool:
        # Host is attacker-controlled under DNS rebinding; pin it to loopback.
        return (self.headers.get("Host") or "") in ALLOWED_HOSTS

    def _deny(self, why: str):
        # Security-relevant: record rejected control attempts (this process was
        # silent before). stdout is captured by the supervisor's power log.
        print(
            f"[power_switch] 403 {why} "
            f"host={self.headers.get('Host')!r} origin={self.headers.get('Origin')!r} "
            f"from={self.client_address[0]}",
            flush=True,
        )
        self._json({"error": "forbidden"}, 403)

    def _cors(self):
        # Reflect only a known loopback origin (the HUD, or our own page).
        # No wildcard: a page you merely visit must not be able to drive this
        # switch, and the reflected value never widens beyond the allowlist.
        origin = self._origin()
        if origin in ALLOWED_ORIGINS:
            self.send_header("Access-Control-Allow-Origin", origin)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self._cors()
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        if self.path.rstrip("/") in ("", "/index.html") or self.path == "/":
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self._cors()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        elif self.path.split("?")[0] == "/power":
            self._json({"state": state()})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path.split("?")[0] != "/power":
            self._json({"error": "not found"}, 404)
            return
        # This POST can put NEX to sleep: shut out CSRF and DNS rebinding before
        # we act. A missing Origin is allowed (local CLI tools like curl send
        # none); a *present* but unlisted Origin is a cross-site caller.
        if not self._host_ok():
            self._deny("bad host")
            return
        origin = self._origin()
        if origin is not None and origin not in ALLOWED_ORIGINS:
            self._deny("bad origin")
            return
        length = int(self.headers.get("Content-Length") or 0)
        raw = self.rfile.read(length) if length else b""
        action = None
        if raw:
            try:
                action = (json.loads(raw) or {}).get("action")
            except ValueError:
                action = None
        if action not in ("on", "off"):
            action = "on" if state() == "off" else "off"   # toggle
        result = go_off() if action == "off" else go_on()
        self._json(result)

    def log_message(self, fmt, *args):   # quiet; supervisor log is the record
        pass


def main():
    os.makedirs(NEX_DIR, exist_ok=True)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[power_switch] start boot_id={_boot_id()}", flush=True)
    print(f"[power_switch] listening on http://{HOST}:{PORT}  state={state()}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
