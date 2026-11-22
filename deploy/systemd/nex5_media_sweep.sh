#!/usr/bin/env bash
# NEX5 media sweep — relocate large media off the hot (system) disk to the
# 4 TB DATA drive's `storage` folder. DRY-RUN BY DEFAULT: it only prints what it
# would move until you pass NEX5_MEDIA_APPLY=1.
#
# It never touches NEX's code, databases, or the `storage` destination itself —
# only files under the configured source dirs matching the media extensions and
# size/age floors.
#
# Config (env):
#   NEX5_MEDIA_DEST      REQUIRED — the storage folder on the DATA drive,
#                        e.g. /mnt/DATA/storage  (find it: `findmnt -n -o TARGET
#                        -S LABEL=DATA` or `lsblk -o NAME,SIZE,LABEL,MOUNTPOINT`)
#   NEX5_MEDIA_SRC       colon-separated dirs to sweep (default "$HOME:/tmp")
#   NEX5_MEDIA_MIN_MB    only files at least this big       (default 50)
#   NEX5_MEDIA_AGE_DAYS  only files older than this          (default 0 = any)
#   NEX5_MEDIA_EXT       comma-separated extensions          (default common video/audio)
#   NEX5_MEDIA_APPLY     set to 1 to actually move           (default 0 = dry-run)
set -u

DEST="${NEX5_MEDIA_DEST:-}"
SRC="${NEX5_MEDIA_SRC:-${HOME}:/tmp}"
MIN_MB="${NEX5_MEDIA_MIN_MB:-50}"
AGE_DAYS="${NEX5_MEDIA_AGE_DAYS:-0}"
EXT="${NEX5_MEDIA_EXT:-mp4,mov,mkv,webm,avi,m4v,flv,wmv,mpg,mpeg,m2ts,ts,mp3,wav,flac,m4a}"
APPLY="${NEX5_MEDIA_APPLY:-0}"

if [ -z "${DEST}" ]; then
    echo "ERROR: set NEX5_MEDIA_DEST to the DATA-drive storage folder (e.g. /mnt/DATA/storage)" >&2
    exit 2
fi
if [ "${APPLY}" = "1" ] && [ ! -d "${DEST}" ]; then
    echo "ERROR: destination ${DEST} does not exist; create it or fix the path" >&2
    exit 2
fi

# build the find -name expression from the extension list
IFS=',' read -r -a exts <<< "${EXT}"
name_expr=()
for e in "${exts[@]}"; do
    [ -n "$e" ] || continue
    name_expr+=(-iname "*.${e}" -o)
done
unset 'name_expr[${#name_expr[@]}-1]'   # drop trailing -o

# age predicate only when a positive AGE_DAYS is set (0 = any age)
age_expr=()
if [ "${AGE_DAYS}" -gt 0 ] 2>/dev/null; then
    age_expr=(-mtime "+${AGE_DAYS}")
fi

moved=0; bytes=0
IFS=':' read -r -a srcs <<< "${SRC}"
for root in "${srcs[@]}"; do
    [ -d "$root" ] || continue
    # never sweep inside the destination, the NEX data dir, or hidden git state
    while IFS= read -r -d '' f; do
        case "$f" in
            "${DEST}"/*) continue ;;
            */.git/*|*/data/*.db|*/data/*.db-*) continue ;;
        esac
        sz=$(stat -c '%s' "$f" 2>/dev/null || echo 0)
        szmb=$(( sz / 1048576 ))
        bytes=$(( bytes + sz ))
        moved=$(( moved + 1 ))
        if [ "${APPLY}" = "1" ]; then
            base=$(basename "$f")
            target="${DEST}/${base}"
            # avoid clobber: suffix with an incrementing index
            i=1; while [ -e "${target}" ]; do target="${DEST}/${base%.*}.$i.${base##*.}"; i=$((i+1)); done
            if mv -n -- "$f" "${target}"; then
                echo "MOVED  ${szmb}MB  ${f} -> ${target}"
            else
                echo "FAILED        ${f}" >&2
            fi
        else
            echo "WOULD-MOVE  ${szmb}MB  ${f}  ->  ${DEST}/"
        fi
    done < <(find "$root" -xdev -type f \( "${name_expr[@]}" \) \
                   -size +"${MIN_MB}"M "${age_expr[@]}" -print0 2>/dev/null)
done

gib=$(awk -v b="$bytes" 'BEGIN{printf "%.2f", b/1073741824}')
if [ "${APPLY}" = "1" ]; then
    echo "--- swept ${moved} file(s), ${gib} GiB -> ${DEST}"
else
    echo "--- DRY-RUN: ${moved} file(s), ${gib} GiB would move -> ${DEST}  (set NEX5_MEDIA_APPLY=1 to apply)"
fi
exit 0
