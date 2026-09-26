#!/usr/bin/env bash
# game-mode: free the GPU for gaming by pausing NEX + ollama, and log GPU
# telemetry for crash diagnosis. Installed as ~/bin/game-mode (symlink).
#
#   game-mode on      STANDBY -> NEX down -> stop ollama -> start titan_watch logger
#   game-mode off     stop logger -> start ollama -> rm STANDBY -> NEX back up
#   game-mode [status]
#
# Why: every amdgpu reset on this box (2026-09-25/26) was a game gfx ring
# timeout while ollama's ROCm runner was resident; the reset could not suspend
# it and escalated to a full MODE1 reset (VRAM lost, session killed).
#
# Uses sudo for systemctl stop/start ollama — you'll be asked for your
# password ONCE, up front, before anything is changed. Every step is checked;
# a failure prints what happened and exits non-zero. Re-running is safe.
set -u

NEX_DIR=${GM_NEX_DIR:-/home/rr/.nex}
STANDBY="${NEX_DIR}/STANDBY"
NEX_PORT=${GM_NEX_PORT:-8765}
OLLAMA_URL=${GM_OLLAMA_URL:-http://127.0.0.1:11434/api/version}
WATCH="${HOME}/bin/titan_watch.sh"
WATCH_LOG=${GM_WATCH_LOG:-"${HOME}/titan_crash_watch.log"}
KFD=${GM_KFD:-/sys/class/kfd/kfd/proc}   # GM_* overrides exist for the offline test only

die() { echo "game-mode: FAILED: $*" >&2; exit 1; }
say() { echo "game-mode: $*"; }

nex_pid()      { local p; p=$(ss -ltnpH "sport = :${NEX_PORT}" 2>/dev/null | grep -oP 'pid=\K[0-9]+' | head -1); [ -n "$p" ] && echo "$p"; }
nex_http()     { curl -s -o /dev/null -m 3 -w '%{http_code}' "http://127.0.0.1:${NEX_PORT}/" 2>/dev/null; }
nex_quiet()    { nex_pid >/dev/null; }
ollama_up()    { curl -s -m 2 "${OLLAMA_URL}" >/dev/null 2>&1; }
ollama_on_gpu() {   # any ollama process holding a KFD (ROCm compute) context
  local p
  for p in $(ls "${KFD}" 2>/dev/null); do
    [ "$(cat /proc/${p}/comm 2>/dev/null)" = ollama ] && return 0
  done
  return 1
}
watch_running() { pgrep -f "titan_watch.sh" >/dev/null; }
wait_for() {        # wait_for <secs> <cmd...>  — poll 1s until cmd succeeds
  local n=$1; shift
  for _ in $(seq "$n"); do "$@" && return 0; sleep 1; done
  return 1
}
not() { ! "$@"; }

status() {
  echo "STANDBY:  $([ -e "${STANDBY}" ] && echo present '(NEX paused)' || echo absent)"
  echo "NEX:      pid=$(nex_pid || true) http=$(nex_http || true)"
  echo "ollama:   service=$(systemctl is-active ollama 2>/dev/null) api=$(ollama_up && echo up || echo down) on_gpu=$(ollama_on_gpu && echo yes || echo no)"
  echo "logger:   $(watch_running && echo running || echo stopped) -> ${WATCH_LOG}"
  echo "vram:     $(( $(cat /sys/class/drm/card*/device/mem_info_vram_used 2>/dev/null | head -1 || echo 0) / 1048576 )) MiB used"
}

on() {
  [ -x "${WATCH}" ] || die "logger ${WATCH} missing"
  say "sudo is needed to stop ollama (password prompt is expected)."
  sudo -v || die "sudo not granted; nothing changed"

  touch "${STANDBY}" || die "could not create ${STANDBY}"
  say "STANDBY set; waiting for NEX to exit (keepalive SIGTERMs it, up to ~25s)..."
  if ! wait_for 40 not nex_quiet; then
    rm -f "${STANDBY}"
    die "NEX still holds :${NEX_PORT} after 40s; STANDBY removed (NEX stays up)"
  fi

  if systemctl is-active --quiet ollama; then
    sudo systemctl stop ollama || { rm -f "${STANDBY}"; die "systemctl stop ollama failed; STANDBY removed so NEX comes back"; }
  fi
  if ! wait_for 15 not ollama_on_gpu; then
    sudo systemctl start ollama; rm -f "${STANDBY}"
    die "ollama still resident on the GPU; restarted ollama + removed STANDBY (rolled back)"
  fi

  if ! watch_running; then
    echo "# ===== GAME MODE ON $(date -Is) =====" >> "${WATCH_LOG}"
    nohup "${WATCH}" "${WATCH_LOG}" >/dev/null 2>&1 &
    sleep 1.5
    watch_running || die "logger failed to start (NEX + ollama remain paused; run 'game-mode off' to restore)"
  fi
  status
  echo "GAME MODE ON: NEX paused, GPU free"
}

off() {
  say "sudo is needed to start ollama (password prompt is expected)."
  sudo -v || die "sudo not granted; nothing changed"

  if watch_running; then
    pkill -f titan_watch.sh
    echo "# ===== GAME MODE OFF $(date -Is) =====" >> "${WATCH_LOG}"
  fi

  if ! systemctl is-active --quiet ollama; then
    sudo systemctl start ollama || die "systemctl start ollama failed; STANDBY left in place (NEX stays paused)"
  fi
  wait_for 30 ollama_up || die "ollama not answering ${OLLAMA_URL} after 30s; STANDBY left in place"

  rm -f "${STANDBY}" || die "could not remove ${STANDBY}"
  say "STANDBY removed; waiting for keepalive to relaunch NEX (up to 120s)..."
  wait_for 120 bash -c "[ \"\$(curl -s -o /dev/null -m 3 -w '%{http_code}' http://127.0.0.1:${NEX_PORT}/)\" = 200 ]" \
    || die "NEX not HTTP 200 on :${NEX_PORT} after 120s (check /tmp/nex5_soak.log)"
  local pid; pid=$(nex_pid)
  tr '\0' '\n' < "/proc/${pid}/environ" 2>/dev/null | grep -qx 'NEX5_SYNTH_FRESH=1' \
    || die "NEX up (pid ${pid}) but NEX5_SYNTH_FRESH=1 not in its environment"
  status
  echo "GAME MODE OFF: NEX + ollama back up"
}

case "${1:-status}" in
  on) on ;;
  off) off ;;
  status) status ;;
  *) echo "usage: game-mode [on|off|status]" >&2; exit 2 ;;
esac
