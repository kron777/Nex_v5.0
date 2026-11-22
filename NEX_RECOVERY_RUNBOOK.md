# NEX recovery runbook — bring her back up (host-side)

Priority #1. Ordered steps to run **on the host** (`rr@…`, NEX at
`/home/rr/Desktop/Desktop/nex5`). **I cannot run these from the cloud session** —
no machine is attached (`list_computer_folders` is empty). Run them yourself, or
attach the machine (desktop app → Settings → Claude Code → Remote Control) and I'll
drive them. Report any step's output back and I'll adjust.

> Order matters: free space → stop the recurrence → restore the checkout → start →
> confirm live. Confirming live is the **last** step, not the first (nothing to
> confirm until she's restored and started).

### 0. Snapshot the situation (read-only)
```bash
df -h; journalctl --disk-usage
du -x -h -d3 "$HOME" /tmp 2>/dev/null | sort -rh | head -30
```

### 1. Free space now (per MEDIA_ROOTCAUSE_PLAN.md)
Move the big media to the DATA drive's `storage` (Option B dry-run, then apply):
```bash
NEX5_MEDIA_DEST=/mnt/DATA/storage /home/rr/Desktop/Desktop/nex5/deploy/systemd/nex5_media_sweep.sh
NEX5_MEDIA_APPLY=1 NEX5_MEDIA_DEST=/mnt/DATA/storage /home/rr/Desktop/Desktop/nex5/deploy/systemd/nex5_media_sweep.sh
# truncate the unbounded keepalive logs (safe; they only hold stdout/stderr):
: > /tmp/nex5_soak.log; : > /tmp/nex5_power.log
```
*(If the checkout is gone and the script with it, run step 3 first, then return here.)*

### 2. Apply the approved guards (stop the recurrence)
```bash
# journald cap (root):
sudo install -D -m 0644 /home/rr/Desktop/Desktop/nex5/deploy/systemd/journald-nex-cap.conf \
     /etc/systemd/journald.conf.d/00-nex-cap.conf
sudo systemctl restart systemd-journald && journalctl --disk-usage
# disk alarm (user systemd):
cp /home/rr/Desktop/Desktop/nex5/deploy/systemd/nex5-disk-alarm.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload && systemctl --user enable --now nex5-disk-alarm.timer
/home/rr/Desktop/Desktop/nex5/deploy/systemd/nex5_disk_alarm.sh; echo "alarm exit=$?"
```

### 3. Restore the deleted home checkout  ·  *the last structural step*
```bash
cd /home/rr/Desktop/Desktop
git clone https://github.com/kron777/Nex_v5.0 nex5    # or restore from your backup
cd nex5
git checkout <branch>        # the branch the host should run (confirm with Jon)
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
```
**Data:** the live SQLite DBs live in `data/` (git-ignored) and are **not** in the
clone. Restore `data/*.db` from your latest backup (`nex_db_backup.py` output) into
the new checkout, or she starts with empty substrate. Confirm which before starting.

### 4. Start her
```bash
cd /home/rr/Desktop/Desktop/nex5
./nex_keepalive.sh            # launches run.py (+ power_switch.py) per the env in the script
```

### 5. Confirm live  ·  *process + HTTP 200*
```bash
pgrep -af "run.py" ; pgrep -af power_switch.py          # process up?
PORT=${NEX5_PORT:-<the port keepalive used>}
curl -s -o /dev/null -w 'HTTP %{http_code}\n' "http://localhost:${PORT}/"   # expect 200
tail -20 /tmp/nex5_soak.log                              # last lines of her boot
```
She is **up** when a `run.py` process is live **and** the GUI returns **HTTP 200**.

---

**Status from the cloud session:** I cannot perform steps 1–5 (no host access) and
I will not claim she is live — that confirmation can only come from the host. I
*have* produced and tested (in-container) every script referenced here; they're in
`deploy/systemd/`. Everything else (PRs #45–48, Phase 0, Gate 0) stays parked per
your direction until she's confirmed live.
