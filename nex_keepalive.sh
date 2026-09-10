#!/usr/bin/env bash
# nex_keepalive.sh — supervisor/respawn wrapper for NEX5.
# v2: single-instance lock + scoped child-kill (no global pkill run.py).
# WHY v2: the old global `pkill -f run.py` + no-lock let two keepalives
# mutually kill each other's child and crash-loop forever. Fixed:
#   - flock single-instance: a 2nd keepalive exits instead of fighting.
#   - only ever kill OUR child ($NEX_PID), never a global pkill.
#   - exit trap kills our child on shutdown (no orphans).
set -u
cd /home/rr/Desktop/Desktop/nex5 || { echo "FATAL: cannot cd to nex5 dir"; exit 1; }

# --- single-instance lock: only ONE keepalive may run ---
LOCKFILE=/tmp/nex5_keepalive.lock
exec 9>"${LOCKFILE}"
# Retry-with-backoff before giving up (session 47 item-3-incident fix).
# `systemctl restart` stops the old instance then starts the new one, but
# the old instance's flock isn't guaranteed released by the instant a
# fresh `flock -n` first runs against it -- session 47 hit exactly this
# race during a restart and it resolved the wrong way: the old instance
# was genuinely dead, the new one's first (and only) attempt lost the
# race anyway and self-aborted, leaving NEX down for ~48s. A handful of
# retries over a few seconds absorbs that handoff window. A GENUINE second
# instance is unaffected by this change: its lock is actually held, not
# about to free up, so every retry fails identically and the loop still
# falls through to the same exit.
LOCK_ACQUIRED=0
for attempt in $(seq 1 10); do
  if flock -n 9; then
    LOCK_ACQUIRED=1
    break
  fi
  sleep 1
done
if [ "${LOCK_ACQUIRED}" -ne 1 ]; then
  echo "$(date '+%F %T') ANOTHER KEEPALIVE IS ALREADY RUNNING — exiting (this is correct)."
  exit 0
fi

PORT=8765
SOAK_LOG=/tmp/nex5_soak.log
VENV=.venv/bin/python3
RESTART_COUNT=0
NEX_PID=""

# --- power switch: STANDBY is the single source of truth ---
# present = OFF (NEX asleep, GPU free) | absent = ON. Both this supervisor
# and power_switch.py obey it. We NEVER respawn while STANDBY exists.
NEX_DIR=/home/rr/.nex
STANDBY="${NEX_DIR}/STANDBY"
PIDFILE="${NEX_DIR}/nex.pid"     # NEX pid, for the switch to SIGTERM
POWER_PORT=8766
POWER_LOG=/tmp/nex5_power.log
POWER_PID=""
mkdir -p "${NEX_DIR}"

# kill ONLY our child, then free the port if still held by it
stop_my_child() {
  if [ -n "${NEX_PID}" ] && kill -0 "${NEX_PID}" 2>/dev/null; then
    kill -9 "${NEX_PID}" 2>/dev/null
  fi
}

# graceful stop for STANDBY: SIGTERM so run.py's trap flushes the dbs and
# releases the GPU, then escalate to SIGKILL ONLY if she refuses. Never a
# plain -9 here -- that is what would lose a mid-write.
graceful_stop_child() {
  if [ -z "${NEX_PID}" ] || ! kill -0 "${NEX_PID}" 2>/dev/null; then
    NEX_PID=""; rm -f "${PIDFILE}"; return
  fi
  echo "$(date '+%F %T') STANDBY: SIGTERM -> NEX pid=${NEX_PID} (graceful; flush dbs, release GPU)"
  kill -TERM "${NEX_PID}" 2>/dev/null
  for _i in $(seq 1 30); do            # wait up to ~15s
    kill -0 "${NEX_PID}" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 "${NEX_PID}" 2>/dev/null; then
    echo "$(date '+%F %T') STANDBY: NEX ignored SIGTERM after 15s -> SIGKILL"
    kill -9 "${NEX_PID}" 2>/dev/null
  fi
  fuser -k ${PORT}/tcp 2>/dev/null
  NEX_PID=""
  rm -f "${PIDFILE}"
  echo "$(date '+%F %T') STANDBY: NEX down, GPU/VRAM released"
}

# keep the always-on power control plane up (GPU-free; survives standby).
ensure_power_switch() {
  if ss -tlnp 2>/dev/null | grep -q ":${POWER_PORT} "; then return; fi
  ${VENV} power_switch.py >> ${POWER_LOG} 2>&1 &
  POWER_PID=$!
  echo "$(date '+%F %T') power switch up -> http://127.0.0.1:${POWER_PORT} pid=${POWER_PID}"
}
trap 'echo "$(date "+%F %T") KEEPALIVE EXITING — killing child ${NEX_PID} + power switch ${POWER_PID}"; stop_my_child; [ -n "${POWER_PID}" ] && kill "${POWER_PID}" 2>/dev/null; exit 0' INT TERM EXIT

launch_nex() {
  # kill only the previous child WE launched (scoped, not global)
  stop_my_child
  sleep 2
  # only free the port if OUR old child was the listener; safe fuser as fallback
  fuser -k ${PORT}/tcp 2>/dev/null
  sleep 2
  # 2026-07-26: NEX5_SPEECH_ENABLED=false removed. It went in 2026-07-24
  # as a stopgap for a libtorch_cpu.so SIGILL crash-loop, but was never
  # actually the fix -- the trap moved to embeddings.py's sentence-
  # transformer load and crashed 9 more times before a clean respawn
  # (see journal/CARRY_OVER.md, 2026-07-24). Flag was left in after the
  # crash stopped recurring on its own. Zero recurrences confirmed since
  # 2026-07-24 19:00 across 34 restarts. Re-enabled; if the trap is live
  # again this flag goes back with a real reason next to it.
  NEX5_RUT_EDGE=1 NEX5_GOVERNOR_OFF=1 NEX5_RECONCILE=1 NEX5_RECONCILE_WB=1 NEX5_SIG_QUALITY=1 \
  NEX5_ANTILOOP=1 NEX5_DELIVER_N=10 NEX5_ABSTAIN_CLOSE=1 NEX5_COMMIT_CLOSE=1 \
  NEX5_WORLD_PRED=1 NEX5_SELF_PRED=1 NEX5_SOCIAL_N=0 NEX5_PORT=${PORT} \
  NEX5_INTAKE_RESONANCE_OFF=1 NEX5_WORLD_CONSOLIDATE=1 NEX5_L4_STAKES=1 NEX5_SELF_NARRATIVE=1 NEX5_QUALITY_SYNTH=1 NEX5_HOT_OBSERVER=1 NEX5_MOMENTUM=1 NEX5_PERSONA_RESPONDER=1 NEX5_GLOBAL_WORKSPACE=1 NEX5_SURPRISE_WEIGHT=1 NEX5_WIDE_MODES=1 NEX5_METACOG_VOICE=1 NEX5_CARRYOVER=1 NEX5_TIER_CLIMB=1 NEX5_MOOD=1 NEX5_CURIOSITY=1 ${VENV} run.py >> ${SOAK_LOG} 2>&1 &
  NEX_PID=$!
  echo "${NEX_PID}" > "${PIDFILE}"
}

is_alive() {
  ss -tlnp 2>/dev/null | grep -q ":${PORT} " && kill -0 "${NEX_PID}" 2>/dev/null
}

echo "$(date '+%F %T') KEEPALIVE START (v3, power-switch aware) — supervising NEX on port ${PORT}"
ensure_power_switch

# Honour STANDBY at boot: if she was put to sleep, do NOT launch her -- the
# power pill on :${POWER_PORT} is what brings her back.
if [ -e "${STANDBY}" ]; then
  echo "$(date '+%F %T') STANDBY present at boot — NOT launching NEX (OFF). Wake her from the power pill on :${POWER_PORT}."
  rm -f "${PIDFILE}"
else
  launch_nex
  echo "$(date '+%F %T') launched NEX pid=${NEX_PID}"

  # restart history: journalctl --user is retention-bounded, so this append
  # preserves it on disk. It goes to an UNTRACKED runtime log, NOT the tracked
  # DEPLOY_LEDGER.tsv -- an automatic keepalive_start on every launch was
  # dirtying the ledger's git working tree on each restart. Real deploy events
  # (code_live_restart, read_only diagnostics, code_activated) are still added
  # to DEPLOY_LEDGER.tsv by hand; this auto row is runtime noise, kept separate.
  # Same TSV columns, so the two can be concatenated if a full timeline is ever
  # wanted. Never affect the launch.
  {
    printf '%s\t%s\t%s\t%s\t%s\n' \
      "$(date -u '+%Y-%m-%dT%H:%M:%S%z')" "keepalive_start" \
      "$(git -C /home/rr/Desktop/Desktop/nex5 rev-parse --short HEAD 2>/dev/null || echo '')" \
      "${NEX_PID}" "auto" \
      >> /home/rr/Desktop/Desktop/nex5/journal/keepalive_runtime.tsv
  } 2>/dev/null || true

  sleep 45
  if is_alive; then
    echo "$(date '+%F %T') NEX confirmed up (flags: $(cat /proc/${NEX_PID}/environ 2>/dev/null | tr '\0' '\n' | grep -c NEX5))"
  else
    echo "$(date '+%F %T') WARNING: NEX did not come up on first launch — check ${SOAK_LOG}"
  fi
fi

# Supervision loop. Polls every 5s so an ON toggle wakes her promptly and an
# OFF toggle is enforced fast. The loop is the second half of the single
# source of truth: STANDBY present => ensure stopped, never respawn.
while true; do
  ensure_power_switch          # power plane stays up regardless of NEX state

  if [ -e "${STANDBY}" ]; then
    # OFF: make sure she is down, and do NOT respawn.
    if [ -n "${NEX_PID}" ] && kill -0 "${NEX_PID}" 2>/dev/null; then
      graceful_stop_child
    fi
    sleep 5
    continue
  fi

  # ON: respawn if she has died (or was just woken).
  if ! is_alive; then
    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "$(date '+%F %T') RESTART #${RESTART_COUNT} — NEX not up, launching. Last log tail:"
    tail -5 ${SOAK_LOG} 2>/dev/null | sed 's/^/    /'
    launch_nex
    sleep 15
    if [ -e "${STANDBY}" ]; then
      # STANDBY requested during our respawn wait — stand back down immediately.
      echo "$(date '+%F %T') STANDBY appeared during respawn — standing down."
      graceful_stop_child
    elif is_alive; then
      echo "$(date '+%F %T') RESTART #${RESTART_COUNT} OK — NEX back up pid=${NEX_PID}"
    else
      echo "$(date '+%F %T') RESTART #${RESTART_COUNT} FAILED — not up after respawn; retry next cycle"
    fi
  fi
  sleep 5
done
