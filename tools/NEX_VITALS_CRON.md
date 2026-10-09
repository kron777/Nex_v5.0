# NEX vitals — nightly snapshot (systemd user timer)

Makes `tools/nex_vitals.py` run itself once a night so the vitals series accrues
without anyone babysitting a session. READ-ONLY instrument; the only write is the
opt-in `--log` append (one JSON line to `logs/vitals_log.jsonl`). It never touches
a NEX database and does not depend on NEX being awake.

## Install (on the live box, one time)

```sh
cp tools/nex-vitals.service tools/nex-vitals.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now nex-vitals.timer
```

## Verify / operate

```sh
systemctl --user list-timers nex-vitals.timer      # next fire time
systemctl --user start nex-vitals.service          # run one snapshot now (manual)
journalctl --user -u nex-vitals.service -n 30       # last run's output
tail -n 1 logs/vitals_log.jsonl | python3 -m json.tool   # newest baseline row
```

## Notes
- `ExecStart` hardcodes the deploy path `/home/rr/Desktop/Desktop/nex5` and its
  `.venv` (matches the rest of this deployment's tooling). Edit both unit files if
  the checkout moves.
- The timer reads whatever the live tree is; it records the live arm-ledger each
  night, so flag changes (an arm, a disarm) show up in the series automatically.
- Once there are a few nights of rows, the tool's 2-sigma flags become live
  (they bootstrap from the log's own history), and ARGUE-register / APERTURE can
  be watched as trends instead of single reads.
