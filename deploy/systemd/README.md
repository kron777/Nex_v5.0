# systemd units (reference copies)

These are **versioned reference copies**. The **active** units live in
`~/.config/systemd/user/` — that's what systemd actually runs.

To (re)install:
```bash
cp deploy/systemd/nex5-db-reaper.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now nex5-db-reaper.timer
systemctl --user list-timers 'nex5-db-reaper*'
```

- `nex5-db-reaper.service` — oneshot; runs `nex_db_reaper.py` (live-safe batched
  30-day prune; no VACUUM). See `../../DB_AUDIT.md`.
- `nex5-db-reaper.timer` — nightly ~04:00, Persistent (catches up if the box was off).

## Disk-space alarm (read-only; alerts, never deletes)

```bash
cp deploy/systemd/nex5-disk-alarm.{service,timer} ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now nex5-disk-alarm.timer
systemctl --user list-timers 'nex5-disk-alarm*'
# on-demand check (prints OK/WARNING + the biggest dirs when low):
deploy/systemd/nex5_disk_alarm.sh; echo "exit=$?"
systemctl --user status nex5-disk-alarm    # a failed unit == disk is low
```

- `nex5_disk_alarm.sh` — df/du observer of the filesystems holding `$HOME` and
  `/tmp`; floors default 3 GiB / 8% free, override via `NEX5_DISK_MIN_FREE_GIB` /
  `NEX5_DISK_MIN_FREE_PCT` / `NEX5_DISK_WATCH`. Writes `~/.config/nex5/disk_alarm.state`.
- `nex5-disk-alarm.service` / `.timer` — oneshot, every 15 min.

## journald cap (needs root; stops logs filling the disk)

```bash
sudo install -D -m 0644 deploy/systemd/journald-nex-cap.conf \
     /etc/systemd/journald.conf.d/00-nex-cap.conf
sudo systemctl restart systemd-journald
journalctl --disk-usage
```

- `journald-nex-cap.conf` — `SystemMaxUse=500M`, `SystemKeepFree=1G`,
  `RuntimeMaxUse=200M`, `MaxRetentionSec=2week`. Reversible: delete the drop-in +
  restart journald.
