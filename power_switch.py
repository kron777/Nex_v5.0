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
HOST = "127.0.0.1"
PORT = 8766


def state() -> str:
    return "off" if os.path.exists(STANDBY) else "on"


def _read_pid() -> int | None:
    try:
        with open(PIDFILE) as f:
            pid = int(f.read().strip())
        os.kill(pid, 0)          # exists?
        return pid
    except (OSError, ValueError):
        return None


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
    return {"state": "off", "term": term}


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
    def _cors(self):
        # loopback-only tool; let the cockpit HUD (8765) post here too
        self.send_header("Access-Control-Allow-Origin", "*")
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
    print(f"[power_switch] listening on http://{HOST}:{PORT}  state={state()}", flush=True)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
