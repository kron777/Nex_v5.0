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
  30-day prune; no VACUUM). See that script's own module docstring for the WHY
  and the live-safety guarantees (`DB_AUDIT.md`, referenced there and in this
  unit's old `Documentation=` line, does not exist anywhere in the repo --
  fixed 2026-11-08 to point here instead).
- `nex5-db-reaper.timer` — nightly ~04:00, Persistent (catches up if the box was off).
