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

## Host checkout path and user services

The reference units below are pinned to the verified checkout on the current
host: `/mnt/games/storage/Desktop/Desktop/nex5`. If the checkout moves, update every unit path before
installing. The active units live in `~/.config/systemd/user/`.

The four long-running/maintenance units are:
- `nex-vitals.service` — oneshot vitals snapshot.
- `nex5-db-reaper.service` — oneshot retention reaper.
- `nex5-keepalive.service` — supervisor; retain default
  `KillMode=control-group` for graceful shutdown.
- `nex5-power-switch.service` — standalone sidecar; do not combine its cgroup
  with the keepalive supervisor.

Install the four reference files only after reviewing the paths and preserving
any host-specific local changes:

```bash
install -m 0644 deploy/systemd/nex-vitals.service ~/.config/systemd/user/
install -m 0644 deploy/systemd/nex5-db-reaper.service ~/.config/systemd/user/
install -m 0644 deploy/systemd/nex5-keepalive.service ~/.config/systemd/user/
install -m 0644 deploy/systemd/nex5-power-switch.service ~/.config/systemd/user/
systemd-analyze --user verify ~/.config/systemd/user/nex-vitals.service ~/.config/systemd/user/nex5-db-reaper.service ~/.config/systemd/user/nex5-keepalive.service ~/.config/systemd/user/nex5-power-switch.service
systemctl --user daemon-reload
```

This installation does not start or restart any service. Enablement and service
activation are separate operator decisions.

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
