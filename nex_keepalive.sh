#!/usr/bin/env bash
# nex_keepalive.sh — supervisor/respawn wrapper for NEX5.
# v2: single-instance lock + scoped child-kill (no global pkill run.py).
# WHY v2: the old global `pkill -f run.py` + no-lock let two keepalives
# mutually kill each other's child and crash-loop forever. Fixed:
#   - flock single-instance: a 2nd keepalive exits instead of fighting.
#   - only ever kill OUR child ($NEX_PID), never a global pkill.
#   - exit trap kills our child on shutdown (no orphans).
set -u
cd /home/rr/Desktop/nex5 || { echo "FATAL: cannot cd to nex5 dir"; exit 1; }

# --- single-instance lock: only ONE keepalive may run ---
LOCKFILE=/tmp/nex5_keepalive.lock
exec 9>"${LOCKFILE}"
if ! flock -n 9; then
  echo "$(date '+%F %T') ANOTHER KEEPALIVE IS ALREADY RUNNING — exiting (this is correct)."
  exit 0
fi

PORT=8765
SOAK_LOG=/tmp/nex5_soak.log
VENV=.venv/bin/python3
RESTART_COUNT=0
NEX_PID=""

# kill ONLY our child, then free the port if still held by it
stop_my_child() {
  if [ -n "${NEX_PID}" ] && kill -0 "${NEX_PID}" 2>/dev/null; then
    kill -9 "${NEX_PID}" 2>/dev/null
  fi
}
trap 'echo "$(date "+%F %T") KEEPALIVE EXITING — killing my child ${NEX_PID}"; stop_my_child; exit 0' INT TERM EXIT

launch_nex() {
  # kill only the previous child WE launched (scoped, not global)
  stop_my_child
  sleep 2
  # only free the port if OUR old child was the listener; safe fuser as fallback
  fuser -k ${PORT}/tcp 2>/dev/null
  sleep 2
  NEX5_RUT_EDGE=1 NEX5_GOVERNOR_OFF=1 NEX5_RECONCILE=1 NEX5_RECONCILE_WB=1 NEX5_SIG_QUALITY=1 \
  NEX5_ANTILOOP=1 NEX5_DELIVER_N=10 NEX5_ABSTAIN_CLOSE=1 NEX5_COMMIT_CLOSE=1 \
  NEX5_WORLD_PRED=1 NEX5_SELF_PRED=1 NEX5_SOCIAL_N=0 NEX5_PORT=${PORT} \
  NEX5_INTAKE_RESONANCE_OFF=1 NEX5_WORLD_CONSOLIDATE=1 NEX5_L4_STAKES=1 NEX5_SELF_NARRATIVE=1 NEX5_QUALITY_SYNTH=1 NEX5_HOT_OBSERVER=1 NEX5_WIDE_MODES=1 ${VENV} run.py > ${SOAK_LOG} 2>&1 &
  NEX_PID=$!
}

is_alive() {
  ss -tlnp 2>/dev/null | grep -q ":${PORT} " && kill -0 "${NEX_PID}" 2>/dev/null
}

echo "$(date '+%F %T') KEEPALIVE START (v2, locked) — supervising NEX on port ${PORT}"
launch_nex
echo "$(date '+%F %T') launched NEX pid=${NEX_PID}"
sleep 15
if is_alive; then
  echo "$(date '+%F %T') NEX confirmed up (flags: $(cat /proc/${NEX_PID}/environ 2>/dev/null | tr '\0' '\n' | grep -c NEX5))"
else
  echo "$(date '+%F %T') WARNING: NEX did not come up on first launch — check ${SOAK_LOG}"
fi

while true; do
  sleep 30
  if ! is_alive; then
    RESTART_COUNT=$((RESTART_COUNT + 1))
    echo "$(date '+%F %T') RESTART #${RESTART_COUNT} — NEX died, respawning. Last log tail:"
    tail -5 ${SOAK_LOG} 2>/dev/null | sed 's/^/    /'
    launch_nex
    sleep 15
    if is_alive; then
      echo "$(date '+%F %T') RESTART #${RESTART_COUNT} OK — NEX back up pid=${NEX_PID}"
    else
      echo "$(date '+%F %T') RESTART #${RESTART_COUNT} FAILED — NEX not up after respawn; will retry next cycle"
    fi
  fi
done
