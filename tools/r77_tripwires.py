#!/usr/bin/env python3
"""r77_tripwires.py — periodic REVERT-TRIPWIRE watch for r77 (chat attention
arbiter live measurement; observation_reports/r77_PREREGISTRATION.md §5).

Reimplements NO measurement. It runs the project's own four read-only
harnesses as subprocesses and reads their own verdicts/printed numbers,
exactly as a human running them by hand would:

  1. Cadence           check_cadence.py --baseline r77_baselines/cadence.json
                        --band 0.20   (exit code is the verdict)
  2. Template          check_template_repetition.py --baseline
                        r77_baselines/template.json --tolerance 0.25
                        (exit code is the verdict; covers BOTH dup-rate and
                        largest_cluster_fraction, matching the pre-reg's
                        "dup rate or cluster fraction up > +25%")
  3. On-subject/maxDF*  check_tripwires.py (its OWN exit code is always 0 --
                        it only ever flags via printed "** BREACH **" /
                        "UNDER 0.65" markers, so those markers are the only
                        machine-readable signal it offers; read verbatim)
  4. Register collapse  check_session_consistency.py, bare reading. The
                        pre-reg's bar is an ABSOLUTE 0.70 share, not the
                        script's own baseline-relative --tolerance, so this
                        reads the printed largest-share value directly
                        rather than trusting that script's --baseline exit
                        code (which would trip on self-repetition drift too
                        -- not one of r77's four defined tripwires -- and at
                        a relative bound, not the absolute one the pre-reg
                        fixed).

NEVER reverts the NEX5_CHAT_WORKSPACE flag. On any breach: prints a loud
banner, writes/refreshes a persistent flag file (~/.nex/R77_TRIPWIRE_BREACH
-- stays until someone removes it, so a breach can't quietly age out between
runs), fires a best-effort desktop notification, and exits 1 (so a breach
also shows as a failed unit under `systemctl --user list-units --failed`,
same idiom nex_keepalive.sh already uses for its own giveup state).

Usage:
  .venv/bin/python3 tools/r77_tripwires.py              # one check, stdout only
  .venv/bin/python3 tools/r77_tripwires.py --log         # also append one JSON
                                                          # line to logs/r77_tripwire_log.jsonl
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASELINES = ROOT / "observation_reports" / "r77_baselines"
NEX_DIR = Path(os.path.expanduser("~/.nex"))
BREACH_FLAG = NEX_DIR / "R77_TRIPWIRE_BREACH"
DEFAULT_LOG = ROOT / "logs" / "r77_tripwire_log.jsonl"
PYTHON = sys.executable


def _run(args: list[str]) -> tuple[int, str, str]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT)
    p = subprocess.run([PYTHON, *args], cwd=str(ROOT), env=env,
                        capture_output=True, text=True, timeout=120)
    return p.returncode, p.stdout, p.stderr


def check_cadence() -> dict:
    rc, out, err = _run(["tools/check_cadence.py",
                          "--baseline", str(BASELINES / "cadence.json"),
                          "--band", "0.20"])
    breach = rc == 1
    return {"name": "cadence", "breach": breach, "error": rc not in (0, 1),
            "detail": "active fires/day moved outside ±20% of the 690.5/day baseline" if breach else "",
            "stdout": out, "stderr": err}


def check_template() -> dict:
    rc, out, err = _run(["tools/check_template_repetition.py",
                          "--baseline", str(BASELINES / "template.json"),
                          "--tolerance", "0.25"])
    breach = rc == 1
    return {"name": "template", "breach": breach, "error": rc not in (0, 1),
            "detail": "near-dup rate or largest-cluster-fraction up >25% vs baseline" if breach else "",
            "stdout": out, "stderr": err}


def check_on_subject_and_maxdf(window: int = 400) -> dict:
    rc, out, err = _run(["tools/check_tripwires.py", str(window)])
    maxdf_breach = "** BREACH **" in out
    on_subject_breach = "UNDER 0.65" in out
    detail = "; ".join(filter(None, [
        "maxDF* breach>=25%" if maxdf_breach else "",
        "EXPLAIN p_on_subject<0.65" if on_subject_breach else "",
    ]))
    return {"name": "on_subject_maxdf", "breach": maxdf_breach or on_subject_breach,
            "maxdf_breach": maxdf_breach, "on_subject_breach": on_subject_breach,
            "detail": detail, "error": rc != 0, "stdout": out, "stderr": err}


_REGISTER_RX = re.compile(r"largest-share=([0-9.]+)")
_REGISTER_BAR = 0.70


def check_register_collapse() -> dict:
    rc, out, err = _run(["tools/check_session_consistency.py"])
    m = _REGISTER_RX.search(out)
    share = float(m.group(1)) if m else None
    breach = (share is not None) and (share > _REGISTER_BAR)
    return {"name": "register_collapse", "breach": breach,
            "largest_register_share": share, "bar": _REGISTER_BAR,
            "detail": f"largest_register_share={share} > {_REGISTER_BAR}" if breach else "",
            "error": rc != 0 or share is None, "stdout": out, "stderr": err}


def _notify(summary: str, body: str) -> None:
    try:
        subprocess.run(["notify-send", "--urgency=critical", summary, body],
                        timeout=5, env=os.environ)
    except Exception:
        pass  # best-effort only; never fail the check over a missing notifier


def _write_breach_flag(when_utc: str, breaches: list[dict]) -> None:
    NEX_DIR.mkdir(parents=True, exist_ok=True)
    lines = [f"r77 TRIPWIRE BREACH at {when_utc}", ""]
    for b in breaches:
        lines.append(f"- {b['name']}: {b.get('detail', 'breach')}")
    lines.append("")
    lines.append("NEX5_CHAT_WORKSPACE was NOT auto-reverted (by design -- see "
                 "r77_tripwires.py docstring). Decide and act by hand:")
    lines.append("  revert: remove NEX5_CHAT_WORKSPACE=1 from nex_keepalive.sh's "
                 "launch_nex(), then `systemctl --user restart nex5-keepalive.service`")
    lines.append(f"Clear this file once reviewed: rm {BREACH_FLAG}")
    BREACH_FLAG.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="r77 revert-tripwire watch (read-only).")
    ap.add_argument("--window", type=int, default=400,
                     help="on-subject/maxDF* window, passed to check_tripwires.py (default 400).")
    ap.add_argument("--log", nargs="?", const=str(DEFAULT_LOG), default=None,
                     metavar="PATH",
                     help=f"append one JSON line to PATH (default {DEFAULT_LOG}). "
                          "Opt-in; every run, breach or not.")
    args = ap.parse_args(argv)

    now = time.time()
    when_utc = time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime(now))

    cadence = check_cadence()
    template = check_template()
    osmd = check_on_subject_and_maxdf(args.window)
    register = check_register_collapse()
    checks = [cadence, template, osmd, register]

    print("=" * 72)
    print(f"R77 TRIPWIRE WATCH  {when_utc}")
    print("=" * 72)

    breaches = []
    for c in checks:
        if c.get("error"):
            print(f"[{c['name']}] COULD NOT EVALUATE — see stderr below")
            if c.get("stderr"):
                print(c["stderr"].strip())
            continue
        status = "** BREACH **" if c["breach"] else "ok"
        print(f"[{c['name']}] {status}")
        if c["name"] == "register_collapse":
            print(f"  largest_register_share={c['largest_register_share']}  bar>{c['bar']}")
        if c["breach"]:
            breaches.append(c)

    print("-" * 72)
    if breaches:
        print(f"**** {len(breaches)} TRIPWIRE(S) BREACHED **** — NEX5_CHAT_WORKSPACE NOT reverted automatically.")
        for b in breaches:
            print(f"  - {b['name']}: {b['detail']}")
        _write_breach_flag(when_utc, breaches)
        _notify("r77 TRIPWIRE BREACH",
                "; ".join(f"{b['name']}: {b['detail']}" for b in breaches))
    else:
        print("All four r77 tripwires clear.")
    print("=" * 72)

    if args.log:
        row = {
            "ts": now, "when_utc": when_utc,
            "breach": bool(breaches),
            "breaches": [{"name": b["name"], "detail": b["detail"]} for b in breaches],
            "cadence_breach": cadence.get("breach"),
            "template_breach": template.get("breach"),
            "maxdf_breach": osmd.get("maxdf_breach"),
            "on_subject_breach": osmd.get("on_subject_breach"),
            "largest_register_share": register.get("largest_register_share"),
        }
        log_path = Path(args.log)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
        print(f"[logged -> {log_path}]")

    return 1 if breaches else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
