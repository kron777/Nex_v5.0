#!/usr/bin/env bash
# nex_keepalive.sh — supervisor/respawn wrapper for NEX5.
# v2: single-instance lock + scoped child-kill (no global pkill run.py).
# WHY v2: the old global `pkill -f run.py` + no-lock let two keepalives
# mutually kill each other's child and crash-loop forever. Fixed:
#   - flock single-instance: a 2nd keepalive exits instead of fighting.
#   - only ever kill OUR child ($NEX_PID), never a global pkill.
#   - exit trap stops our child on shutdown (no orphans), gracefully (v3:
#     SIGTERM first, so a deliberate stop/restart is recorded as clean
#     downtime rather than reading as a crash -- see theory_x/memory/downtime.py).
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
VENV=.venv/bin/python3
RESTART_COUNT=0
NEX_PID=""

# --- power switch: STANDBY is the single source of truth ---
# present = OFF (NEX asleep, GPU free) | absent = ON. Both this supervisor
# and power_switch.py obey it. We NEVER respawn while STANDBY exists.
NEX_DIR=/home/rr/.nex
STANDBY="${NEX_DIR}/STANDBY"
PIDFILE="${NEX_DIR}/nex.pid"     # NEX pid, for the switch to SIGTERM
IDENTITY_FILE="${NEX_DIR}/nex.pid.identity"   # "pid:starttime:boot_id" for the SAME launch as PIDFILE
POWER_PORT=8766
POWER_PID=""
mkdir -p "${NEX_DIR}"
# both moved off /tmp: systemd-tmpfiles can clear /tmp across a reboot, which
# would destroy the one artifact (the boot-sequence log) a reboot test most
# needs. Same reasoning now applies to POWER_LOG as already applied to
# SOAK_LOG; both just append, same as before the move -- no rotation here,
# matching this script's existing convention for its other runtime logs.
SOAK_LOG="${NEX_DIR}/nex5_soak.log"
POWER_LOG="${NEX_DIR}/nex5_power.log"

# --- crash-loop detection (two independent triggers; see notes below) ---
FAST_RESTART_WINDOW_SEC=300    # a launch that dies before surviving this long counts as "fast"
FAST_RESTART_LIMIT=3           # this many fast deaths IN A ROW -> give up
FAST_RESTART_STREAK=0
LAST_LAUNCH_TS=0
DEATH_LOG="${NEX_DIR}/death_log"        # file-backed: survives the supervisor itself restarting
DEATH_RATE_WINDOW_SEC=86400
DEATH_RATE_LIMIT=6             # this many deaths in a rolling 24h -> give up, even if each
                                #   individual uptime looked healthy (the churn case).
                                #   Set well above FAST_RESTART_LIMIT: with both at the
                                #   same value, every fast death is also a death inside
                                #   the 24h window, so the rate counter always reaches its
                                #   limit no later than the streak does and the streak
                                #   branch can never be the one that trips (verified live,
                                #   2026-10-31 — fast_streak sat at 2/3 when rate hit 3/3).
                                #   6 gives the streak real headroom for a genuine fast
                                #   boot loop while keeping the 24h net for chronic,
                                #   spaced-out churn.
FAILED_MARKER="${NEX_DIR}/KEEPALIVE_FAILED"
GIVEUP_EXIT_CODE=3             # reserved for "giveup, marker written" ONLY —
                                #   not 1, which set -e / missing venv / a lost
                                #   flock race would also return, and which
                                #   would then get stuck `failed` with no
                                #   marker to explain why. Paired with
                                #   RestartPreventExitStatus=3 in the unit, so
                                #   `failed` means exactly this and nothing else.
KEEPALIVE_EXIT_CODE=0          # trap exits with this; only giveup sets it to GIVEUP_EXIT_CODE
POWER_SWITCH_OWNER_LOGGED=0    # one-shot flag for ensure_power_switch()'s owner log line

# Field 22 of /proc/<pid>/stat -- starttime in clock ticks since boot.
# comm (field 2) is parenthesised and may itself contain ')' or spaces, so
# this splits on the LAST ') ' rather than on whitespace; field 22 is then
# the 20th token of what follows it (see power_switch.py's _proc_starttime
# for the Python twin of this parse -- both must agree on the same pid).
proc_starttime() {
  local pid="$1" stat rest
  stat=$(cat "/proc/${pid}/stat" 2>/dev/null) || return 1
  rest="${stat##*") "}"
  set -- ${rest}
  [ "$#" -ge 20 ] || return 1
  echo "${20}"
}

boot_id() {
  cat /proc/sys/kernel/random/boot_id 2>/dev/null
}

# Companion to PIDFILE so power_switch.py (a separate, longer-lived process)
# can tell "this pid number" apart from "this specific NEX instance" --
# without it, a stale pidfile surviving a reboot or a recycled pid would
# read as "alive" to a bare existence check. No identity file written means
# no identity to trust; power_switch.py already fails open to "not running".
write_pid_identity() {
  local pid="$1" st bid
  st=$(proc_starttime "${pid}") && bid=$(boot_id) && [ -n "${bid}" ] \
    && echo "${pid}:${st}:${bid}" > "${IDENTITY_FILE}" \
    || rm -f "${IDENTITY_FILE}"
}

# kill ONLY our child, then free the port if still held by it
stop_my_child() {
  if [ -n "${NEX_PID}" ] && kill -0 "${NEX_PID}" 2>/dev/null; then
    kill -9 "${NEX_PID}" 2>/dev/null
  fi
}

# Graceful stop, SIGTERM first so run.py's handler stamps a clean-shutdown
# marker (theory_x/memory/downtime.py) and flushes dbs/GPU, escalating to
# SIGKILL ONLY if she refuses. Never a plain -9 here -- that is what would
# lose a mid-write AND leave the next boot's downtime record reading this
# as an unexplained crash instead of the deliberate stop it was. $1 is a
# label for the log lines only (STANDBY, or whoever else is calling this).
graceful_stop_child() {
  local label="${1:-STANDBY}"
  if [ -z "${NEX_PID}" ] || ! kill -0 "${NEX_PID}" 2>/dev/null; then
    NEX_PID=""; rm -f "${PIDFILE}" "${IDENTITY_FILE}"; return
  fi
  echo "$(date '+%F %T') ${label}: SIGTERM -> NEX pid=${NEX_PID} (graceful; flush dbs, release GPU)"
  kill -TERM "${NEX_PID}" 2>/dev/null
  for _i in $(seq 1 30); do            # wait up to ~15s
    kill -0 "${NEX_PID}" 2>/dev/null || break
    sleep 0.5
  done
  if kill -0 "${NEX_PID}" 2>/dev/null; then
    echo "$(date '+%F %T') ${label}: NEX ignored SIGTERM after 15s -> SIGKILL"
    kill -9 "${NEX_PID}" 2>/dev/null
  fi
  fuser -k ${PORT}/tcp 2>/dev/null
  NEX_PID=""
  rm -f "${PIDFILE}" "${IDENTITY_FILE}"
  echo "$(date '+%F %T') ${label}: NEX down, GPU/VRAM released"
}

# keep the always-on power control plane up (GPU-free; survives standby).
ensure_power_switch() {
  if ss -tlnp 2>/dev/null | grep -q ":${POWER_PORT} "; then
    if [ -z "${POWER_PID}" ] && [ "${POWER_SWITCH_OWNER_LOGGED}" -eq 0 ]; then
      echo "$(date '+%F %T') power switch already up on :${POWER_PORT} — owned externally (nex5-power-switch.service, presumably). Not starting our own."
      POWER_SWITCH_OWNER_LOGGED=1
    fi
    return
  fi
  ${VENV} power_switch.py >> ${POWER_LOG} 2>&1 &
  POWER_PID=$!
  POWER_SWITCH_OWNER_LOGGED=1
  echo "$(date '+%F %T') power switch up -> http://127.0.0.1:${POWER_PORT} pid=${POWER_PID} — started BY THIS SCRIPT. nex5-power-switch.service doesn't seem to own :${POWER_PORT} — check it's enabled."
}

# POWER_LOG is normally written by nex5-power-switch.service's own
# StandardOutput=append: redirect -- a long-lived, Restart=always process
# that outlives this script and is never rotated, so it grows unbounded.
# copytruncate (not mv/rename): rewriting the same inode in place means
# an existing O_APPEND writer (ours or the service's) just recalculates
# its offset to the new EOF on its next write -- no lost lines, no fd
# left pointing at a renamed-away file.
POWER_LOG_MAX_BYTES=262144   # 256KB
trim_power_log() {
  [ -f "${POWER_LOG}" ] || return
  local _sz
  _sz=$(stat -c%s "${POWER_LOG}" 2>/dev/null || echo 0)
  if [ "${_sz}" -gt "${POWER_LOG_MAX_BYTES}" ]; then
    tail -n 1000 "${POWER_LOG}" > "${POWER_LOG}.tmp" 2>/dev/null \
      && cat "${POWER_LOG}.tmp" > "${POWER_LOG}" \
      && rm -f "${POWER_LOG}.tmp"
  fi
}
trap 'trap - INT TERM EXIT; echo "$(date "+%F %T") KEEPALIVE EXITING (code ${KEEPALIVE_EXIT_CODE}) — stopping child ${NEX_PID} gracefully (SIGTERM first, so this reads as a clean stop, not a crash); power switch is now its own systemd unit and is left running"; graceful_stop_child "SUPERVISOR EXIT"; exit ${KEEPALIVE_EXIT_CODE}' INT TERM EXIT

launch_nex() {
  # 2026-11-07: NEX5_CHAT_WORKSPACE=1 armed for r77 (chat attention arbiter
  # live measurement, observation_reports/r77_PREREGISTRATION.md). Budget
  # left at its code default (1400 chars) -- the pre-reg doesn't call for
  # overriding it. OFF-condition baselines frozen 2026-10-26 in
  # r77_baselines/. Window = >=200 chat turns or 14 days, first to trigger.
  # Any r77 tripwire firing (cadence, template, on-subject, register
  # collapse -- see pre-reg SS5) means: pull this flag back out, don't just
  # leave it and move on.
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
  NEX5_RUT_EDGE=1 NEX5_GOVERNOR_OFF=1 NEX5_RECONCILE=1 NEX5_RECONCILE_WB=1 NEX5_SIG_QUALITY=1 NEX5_PROBLEM_SELF_GATE=1 \
  NEX5_ANTILOOP=1 NEX5_DELIVER_N=10 NEX5_ABSTAIN_CLOSE=1 NEX5_COMMIT_CLOSE=1 \
  NEX5_WORLD_PRED=1 NEX5_SELF_PRED=1 NEX5_SOCIAL_N=1 NEX5_PORT=${PORT} \
  NEX5_INTAKE_RESONANCE_OFF=1 NEX5_WORLD_CONSOLIDATE=1 NEX5_L4_STAKES=1 NEX5_SELF_NARRATIVE=1 NEX5_QUALITY_SYNTH=1 NEX5_HOT_OBSERVER=1 NEX5_MOMENTUM=1 NEX5_PERSONA_RESPONDER=1 NEX5_GLOBAL_WORKSPACE=1 NEX5_SURPRISE_WEIGHT=1 NEX5_WIDE_MODES=1 NEX5_METACOG_VOICE=1 NEX5_CARRYOVER=1 NEX5_TIER_CLIMB=1 NEX5_MOOD=1 NEX5_ATTRIB_CRYSTALLIZE=1 NEX5_BRANCH_TEMP=0.35 NEX5_ASSOC_RECALL=1 NEX5_STAKES_DEEP=1 NEX5_DRIVE_CONTENT=1 NEX5_SOCIAL_DEPTH=1 NEX5_PERSONA_LANG_GUARD=1 NEX5_OPERATOR_MODEL=1 NEX5_CHAT_MEMORY=1 NEX5_CHAT_WORKSPACE=1 NEX5_COMPASS=1 NEX5_BESTOFCLUSTER=1 MOLTBOOK_DRY_RUN=1 NEX5_FOUNTAIN_DEDUP=1 NEX5_COMPASS_TRIM=1 NEX5_EQUANIMITY=1 NEX5_APRAMADA=1 NEX5_AFFECT_CARRY=1 NEX5_SCORE_F2_V2=1 NEX5_FOCUS_ROTATE=1 NEX5_FRAME_DEDUP=0 NEX5_FRAME_GATE=0 NEX5_OPERATOR_ANCHOR=1 NEX5_CHAT_ANTIECHO=1 NEX5_PROVENANCE=1 NEX5_WARRANT_RECORD=1 NEX5_SYNTH_FRESH=1 NEX5_SYNTH_FRESH_SIBLING=1 NEX5_SELF_MAINTAIN_SHADOW=1 NEX5_GW_SURPRISE_NONEMPTY=1 NEX5_AFFINITY_PROVENANCE=on NEX5_INTAKE_T6_RESERVE=50 NEX5_IDENTITY_BLOCK=1 NEX5_SOURCE_KIND=1 NEX5_OWNED_BELIEF=1 NEX5_RECONCILER=1 NEX5_COMMITMENTS=1 NEX5_COMMITMENT_VALENCE=1 NEX5_EXPECT_LEARN=1 ${VENV} run.py >> ${SOAK_LOG} 2>&1 &
  NEX_PID=$!
  LAST_LAUNCH_TS=$(date +%s)
  echo "${NEX_PID}" > "${PIDFILE}"
  write_pid_identity "${NEX_PID}"
}

is_alive() {
  ss -tlnp 2>/dev/null | grep -q ":${PORT} " && kill -0 "${NEX_PID}" 2>/dev/null
}

echo "$(date '+%F %T') KEEPALIVE START (v3, power-switch aware) — supervising NEX on port ${PORT}"
ensure_power_switch

# Honour STANDBY at boot: if she was put to sleep, do NOT launch her -- the
# power pill on :${POWER_PORT} is what brings her back.
if [ -e "${FAILED_MARKER}" ]; then
  echo "$(date '+%F %T') KEEPALIVE_FAILED present at startup — refusing to launch NEX and exiting (power switch is a separate unit; unaffected). Clear with: rm ${FAILED_MARKER}, then: systemctl --user start nex5-keepalive"
  KEEPALIVE_EXIT_CODE=${GIVEUP_EXIT_CODE}
  exit ${GIVEUP_EXIT_CODE}
elif [ -e "${STANDBY}" ]; then
  echo "$(date '+%F %T') STANDBY present at boot — NOT launching NEX (OFF). Wake her from the power pill on :${POWER_PORT}."
  rm -f "${PIDFILE}" "${IDENTITY_FILE}"
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
  trim_power_log               # bound POWER_LOG's size regardless of who's writing it

  if [ -e "${STANDBY}" ]; then
    # OFF: make sure she is down, and do NOT respawn.
    if [ -n "${NEX_PID}" ] && kill -0 "${NEX_PID}" 2>/dev/null; then
      graceful_stop_child
    elif [ -n "${NEX_PID}" ]; then
      # Already dead -- e.g. power_switch.py SIGTERM'd her directly,
      # bypassing us entirely. Still clear our bookkeeping instead of
      # leaving a stale pid+identity file on disk for however long
      # STANDBY persists (found live 2026-10-31: sat stale ~2.5h).
      NEX_PID=""; rm -f "${PIDFILE}" "${IDENTITY_FILE}"
    fi
    sleep 5
    continue
  fi

  # ON: respawn if she has died (or was just woken).
  if ! is_alive; then
    RESTART_COUNT=$((RESTART_COUNT + 1))

    # Only count this as a DEATH if NEX_PID still holds a pid — i.e. she was
    # believed alive and now isn't. A fresh boot or a wake from STANDBY both
    # leave NEX_PID empty (its init value, or graceful_stop_child() having
    # just cleared it), so that case launches normally below WITHOUT being
    # counted here. Without this guard, every ordinary power-pill OFF/ON
    # cycle writes a death_log entry indistinguishable from a real crash,
    # and 3 legitimate cycles would trigger a false giveup.
    if [ -n "${NEX_PID}" ]; then
      NOW_TS=$(date +%s)
      _alive_for=$(( NOW_TS - LAST_LAUNCH_TS ))

      # death-rate trigger: append + prune to a rolling 24h window, file-backed
      # so it survives this supervisor script itself being restarted (unlike
      # RESTART_COUNT, which is a plain shell var and resets to 0 every time).
      echo "${NOW_TS}" >> "${DEATH_LOG}"
      awk -v cutoff="$(( NOW_TS - DEATH_RATE_WINDOW_SEC ))" '$1>=cutoff' "${DEATH_LOG}" > "${DEATH_LOG}.tmp" 2>/dev/null && mv "${DEATH_LOG}.tmp" "${DEATH_LOG}"
      _death_rate_count=$(wc -l < "${DEATH_LOG}" 2>/dev/null || echo 0)

      # fast-crash-loop trigger: N deaths in a row, each before surviving
      # FAST_RESTART_WINDOW_SEC. LAST_LAUNCH_TS=0 on the very first iteration
      # guards against a false positive on cold start.
      if [ "${LAST_LAUNCH_TS}" -gt 0 ] && [ "${_alive_for}" -lt "${FAST_RESTART_WINDOW_SEC}" ]; then
        FAST_RESTART_STREAK=$((FAST_RESTART_STREAK + 1))
      else
        FAST_RESTART_STREAK=0   # she ran for a real while — not part of a crash loop
      fi

      if [ "${FAST_RESTART_STREAK}" -ge "${FAST_RESTART_LIMIT}" ] || [ "${_death_rate_count}" -ge "${DEATH_RATE_LIMIT}" ]; then
        {
          echo "$(date '+%F %T') KEEPALIVE GIVING UP — fast_streak=${FAST_RESTART_STREAK} (limit ${FAST_RESTART_LIMIT}) death_rate_24h=${_death_rate_count} (limit ${DEATH_RATE_LIMIT})"
          echo "last ${SOAK_LOG} tail:"
          tail -20 "${SOAK_LOG}" 2>/dev/null
        } > "${FAILED_MARKER}" 2>&1
        KEEPALIVE_EXIT_CODE=${GIVEUP_EXIT_CODE}
        echo "$(date '+%F %T') FAILED marker written to ${FAILED_MARKER} — exiting ${GIVEUP_EXIT_CODE} so systemd shows failed (and stays failed — RestartPreventExitStatus=3). Power switch unaffected (separate unit)."
        exit ${GIVEUP_EXIT_CODE}
      fi
    else
      FAST_RESTART_STREAK=0
      echo "$(date '+%F %T') NEX not up (fresh boot or wake from STANDBY, NEX_PID was empty) — launching, not counted as a death."
    fi

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
