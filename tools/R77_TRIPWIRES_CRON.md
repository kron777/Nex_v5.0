# r77 tripwire watch — periodic systemd user timer

Runs `tools/r77_tripwires.py` every 6 hours for the duration of the r77 live
measurement window (chat attention arbiter, `observation_reports/
r77_PREREGISTRATION.md`), so a breach of one of the four pre-registered
revert tripwires doesn't sit unnoticed for days between manual checks.

READ-ONLY watch. It reuses the project's own four check scripts
(`check_cadence.py`, `check_template_repetition.py`, `check_tripwires.py`,
`check_session_consistency.py`) as subprocesses and reads their own
verdicts/printed numbers — no detection logic is reimplemented. It never
touches `nex_keepalive.sh` and never reverts `NEX5_CHAT_WORKSPACE`.

## Install (on the live box, one time)

```sh
cp tools/r77-tripwires.service tools/r77-tripwires.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now r77-tripwires.timer
```

## Verify / operate

```sh
systemctl --user list-timers r77-tripwires.timer        # next fire time
systemctl --user start r77-tripwires.service             # run one check now (manual)
journalctl --user -u r77-tripwires.service -n 40          # last run's output
systemctl --user list-units --failed                      # a breach shows up here too
tail -n 1 logs/r77_tripwire_log.jsonl | python3 -m json.tool   # newest reading
cat ~/.nex/R77_TRIPWIRE_BREACH                             # present only on an unreviewed breach
```

## How a breach actually surfaces

1. **Desktop notification** (`notify-send --urgency=critical`) — best-effort;
   shows up on the desktop session the timer runs under.
2. **`~/.nex/R77_TRIPWIRE_BREACH`** — a plain-text file written/refreshed on
   every breach, naming which tripwire(s) fired and the manual revert
   command. It is NOT auto-cleared, so it stays visible across runs until
   someone reviews it and removes it by hand — a breach can't quietly expire.
3. **The systemd unit goes `failed`** (the script exits 1 on breach) —
   visible in `systemctl --user list-units --failed` and in
   `systemctl --user list-timers` (next run still fires on schedule
   regardless; oneshot failure doesn't disable the timer).
4. **`logs/r77_tripwire_log.jsonl`** — one JSON line every run (breach or
   not), so the series across the 14-day window is reconstructable
   afterward, same convention as `logs/vitals_log.jsonl`.

## What it does NOT do

- **Does not auto-revert `NEX5_CHAT_WORKSPACE`.** That was an explicit call
  (Jon, 2026-11-07): loud-and-visible only, auto-revert needs its own
  go-ahead first. The breach-flag file states the manual revert command.
- Does not write to any NEX database. The only writes are the opt-in `--log`
  append, the breach flag file, and (best-effort) the desktop notification.

## Notes

- `ExecStart` hardcodes the deploy path `/home/rr/Desktop/Desktop/nex5` and
  its `.venv`, matching the rest of this deployment's tooling.
- Scoped to the r77 window — disable once r77 resolves:
  `systemctl --user disable --now r77-tripwires.timer`.
- The register-collapse check reads `check_session_consistency.py`'s bare
  printed `largest-share=` value and compares it to the pre-reg's absolute
  0.70 bar directly, rather than trusting that script's own `--baseline`
  exit code — that code's relative `--tolerance` would trip on
  self-repetition drift too (not one of r77's four tripwires) and at a
  different (relative, not absolute) bound.
