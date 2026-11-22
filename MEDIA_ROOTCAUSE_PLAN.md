# Media-file disk fill — root-cause options (short; pick one)

**Finding (grounded in the repo).** NEX's own code produces **no** video/media
files — a full search found no `.mp4/.mov/.webm/ffmpeg/yt-dlp/video-dir/TTS-audio`
writer anywhere in `theory_x/`, `speech/`, `voice/`, or the root scripts. So the
"big videos" that filled the system disk are **host-side, external to NEX**
(downloads, recordings, etc. sharing the same drive). There is nothing to fix in
NEX's code for the videos themselves — the fix is *where they land and how they
clear*.

**Secondary, NEX-side contributor (worth fixing too):** `nex_keepalive.sh` appends
run output **forever** to `/tmp/nex5_soak.log` and `/tmp/nex5_power.log`
(`>> ${SOAK_LOG} 2>&1`), with no rotation. Over a long soak these grow large on
whatever filesystem holds `/tmp`. (The journald cap covers systemd logs; these two
files are separate.)

**Known destination:** you said the 4 TB DATA drive has a `storage` folder where
most of this already gets moved. The options below target that.

First, find the drive + folder (so paths are exact):
```bash
lsblk -o NAME,SIZE,LABEL,FSTYPE,MOUNTPOINT          # locate the 4 TB DATA drive
findmnt -n -o TARGET -S LABEL=DATA 2>/dev/null       # its mountpoint, if labelled DATA
ls -d /mnt/*/storage /media/*/*/storage /run/media/*/*/storage 2>/dev/null  # find 'storage'
# then locate the biggest files on the HOT (system) disk:
du -x -h -d3 "$HOME" /tmp 2>/dev/null | sort -rh | head -30
```

## Option A — manual (what's been happening)
Locate big files with the `du` above and `mv` them to `…/DATA/storage` by hand.
- **Pro:** zero new machinery, full control. **Con:** recurs; needs you each time.

## Option B — automated sweep to DATA/storage  ·  *recommended, ready now*
`deploy/systemd/nex5_media_sweep.sh` — moves large media off the hot disk to the
storage folder. **Dry-run by default** (prints what it would move); applies only
with `NEX5_MEDIA_APPLY=1`. Never touches NEX code, DBs, or the destination.
```bash
# 1) see what it would move (safe):
NEX5_MEDIA_DEST=/mnt/DATA/storage deploy/systemd/nex5_media_sweep.sh
# 2) apply once you're happy:
NEX5_MEDIA_APPLY=1 NEX5_MEDIA_DEST=/mnt/DATA/storage deploy/systemd/nex5_media_sweep.sh
# 3) (optional) run it nightly — pair with a tiny user service/timer like the reaper's.
```
Tunables: `NEX5_MEDIA_SRC` (dirs, default `$HOME:/tmp`), `NEX5_MEDIA_MIN_MB`
(default 50), `NEX5_MEDIA_AGE_DAYS` (default 0 = any), `NEX5_MEDIA_EXT`.
- **Pro:** repeatable, reviewable, safe-by-default. **Con:** moves *after* files land.

## Option C — redirect at the source  ·  *most permanent, needs the producer path*
If the videos always land in one known directory, make that directory *be* on the
DATA drive so they never hit the system disk:
```bash
mv ~/<that-dir> /mnt/DATA/storage/<that-dir> && ln -s /mnt/DATA/storage/<that-dir> ~/<that-dir>
```
- **Pro:** nothing to sweep; fixes it at the root. **Con:** only works once we know
  which app writes the videos and where (tell me the dir and I'll confirm the move).

## Also do regardless (secondary NEX-side fix)
Cap the keepalive logs so `/tmp/nex5_*.log` can't grow without bound — either
truncate on each (re)launch, or add a `logrotate` rule. Say the word and I'll wire
the smaller of the two into `nex_keepalive.sh` as a separate, reviewed change.

**My recommendation:** B now (fast, safe, reversible) to free space and stop the
recurrence; move to C for the one directory that produces the bulk, once you tell
me which it is. I **cannot** run any of this from the cloud session — these are
host commands for you (or for an attached-machine session).
