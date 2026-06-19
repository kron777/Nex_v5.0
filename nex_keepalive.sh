#!/usr/bin/env bash
# nex_keepalive.sh — supervisor/respawn wrapper for NEX5.
#
# WHY: NEX has been killed by the host environment (sleep/OOM/external) twice,
# losing multi-hour soaks each time. A bare background process stays dead until
# manually restarted. This wrapper detects death and respawns NEX immediately
# with her exact 14-flag settings, logging each (re)start. Environment-kills now
# cost seconds of downtime, not hours of lost experiment time.
#
# USAGE (from nex5 root):
#   chmod +x nex_keepalive.sh
#   nohup ./nex_keepalive.sh > /tmp/nex_keepalive.log 2>&1 &
#   # to stop the whole thing (wrapper + NEX):
#   #   pkill -f nex_keepalive.sh ; pkill -f run.py
#
# Check status:
#   tail -f /tmp/nex_keepalive.log     # see restarts as they happen
#   grep RESTART /tmp/nex_keepalive.log # count how often she's been reaped

set -u
cd /home/rr/Desktop/nex5 || { echo "FATAL: cannot cd to nex5 dir"; exit 1; }

PORT=8765
SOAK_LOG=/tmp/nex5_soak.log
VENV=.venv/bin/python3
RESTART_COUNT=0

# NEX's correct 14-flag settings — single source of truth.
launch_nex() {
  pkill -f "run.py" 2>/dev/null
  sleep 3
  fuser -k ${PORT}/tcp 2>/dev/null
  sleep 3
  NEX5_RUT_EDGE=1 NEX5_GOVERNOR_OFF=1 NEX5_RECONCILE=1 NEX5_RECONCILE_WB=1 NEX5_SIG_QUALITY=1 \
  NEX5_ANTILOOP=1 NEX5_DELIVER_N=10 NEX5_ABSTAIN_CLOSE=1 NEX5_COMMIT_CLOSE=1 \
  NEX5_WORLD_PRED=1 NEX5_SELF_PRED=1 NEX5_SOCIAL_N=0 NEX5_PORT=${PORT} \
  NEX5_INTAKE_RESONANCE_OFF=1 ${VENV} run.py > ${SOAK_LOG} 2>&1 &
  NEX_PID=$!
}

is_alive() {
  # alive if the port is listening AND the pid we launched still exists
  ss -tlnp 2>/dev/null | grep -q ":${PORT} " && kill -0 "${NEX_PID}" 2>/dev/null
}

echo "$(date '+%F %T') KEEPALIVE START — supervising NEX on port ${PORT}"
launch_nex
echo "$(date '+%F %T') launched NEX pid=${NEX_PID}"
sleep 15
if is_alive; then
  echo "$(date '+%F %T') NEX confirmed up (flags: $(cat /proc/${NEX_PID}/environ 2>/dev/null | tr '\0' '\n' | grep -c NEX5))"
else
  echo "$(date '+%F %T') WARNING: NEX did not come up on first launch — check ${SOAK_LOG}"
fi

# Supervision loop: check every 30s, respawn on death.
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
