#!/usr/bin/env bash
# NEX5 disk-space alarm — read-only. ALERTS, never deletes.
#
# Watches the filesystem(s) holding NEX's home checkout and its /tmp logs, and
# raises an alarm (non-zero exit + WARNING to stderr -> journald when run as a
# systemd service) when free space falls below a threshold. On alarm it also
# prints the largest directories under the watched roots so the offender (e.g.
# stray video files) is easy to locate — but it touches nothing.
#
# Thresholds (env, with safe defaults):
#   NEX5_DISK_MIN_FREE_GIB   absolute free-space floor, GiB   (default 3)
#   NEX5_DISK_MIN_FREE_PCT   percent-free floor               (default 8)
#   NEX5_DISK_WATCH          colon-separated paths to watch   (default "$HOME:/tmp")
#   NEX5_DISK_TOPN           how many big dirs to list on alarm (default 12)
#
# Exit: 0 = all watched filesystems healthy; 1 = at least one below threshold;
#       2 = usage error. Never fails NEX; it is an observer.
set -u

MIN_FREE_GIB="${NEX5_DISK_MIN_FREE_GIB:-3}"
MIN_FREE_PCT="${NEX5_DISK_MIN_FREE_PCT:-8}"
WATCH="${NEX5_DISK_WATCH:-${HOME}:/tmp}"
TOPN="${NEX5_DISK_TOPN:-12}"
STATE_DIR="${XDG_CONFIG_HOME:-${HOME}/.config}/nex5"
STATE_FILE="${STATE_DIR}/disk_alarm.state"

ts() { date '+%F %T'; }

# Resolve each watched path to its filesystem mountpoint, de-duplicated, so the
# same device is not alarmed twice.
declare -A seen_fs=()
alarm=0
report=""

IFS=':' read -r -a paths <<< "${WATCH}"
for p in "${paths[@]}"; do
    [ -e "$p" ] || continue
    # mountpoint + available KiB + used% for the fs holding $p
    read -r fs avail_kib usep mnt < <(df -P -k "$p" 2>/dev/null | awk 'NR==2 {print $1, $4, $5, $6}')
    [ -n "${fs:-}" ] || continue
    [ -n "${seen_fs[$fs]:-}" ] && continue
    seen_fs[$fs]=1

    avail_gib=$(awk -v k="$avail_kib" 'BEGIN{printf "%.1f", k/1048576}')
    used_pct=${usep%\%}
    free_pct=$((100 - used_pct))

    low=0
    awk -v a="$avail_gib" -v m="$MIN_FREE_GIB" 'BEGIN{exit !(a+0 < m+0)}' && low=1
    [ "$free_pct" -lt "$MIN_FREE_PCT" ] && low=1

    line="fs=${fs} mount=${mnt} free=${avail_gib}GiB free_pct=${free_pct}% (floors: ${MIN_FREE_GIB}GiB / ${MIN_FREE_PCT}%)"
    if [ "$low" -eq 1 ]; then
        alarm=1
        echo "$(ts) WARNING: NEX5 disk LOW — ${line}" >&2
        report="${report}${line}\n"
        # locate the big consumers under this path (read-only; bounded depth)
        echo "$(ts)   top ${TOPN} dirs under ${mnt}:" >&2
        du -x -h -d 2 "$mnt" 2>/dev/null | sort -rh | head -n "$TOPN" | sed 's/^/        /' >&2
    else
        echo "$(ts) OK: NEX5 disk — ${line}" >&2
    fi
done

# Persist the latest reading (marker for the GUI / a human / the next run).
mkdir -p "${STATE_DIR}" 2>/dev/null && {
    {
        echo "checked_at=$(ts)"
        echo "alarm=${alarm}"
        printf '%b' "${report:-all watched filesystems healthy\n}"
    } > "${STATE_FILE}" 2>/dev/null
}

exit "${alarm}"
