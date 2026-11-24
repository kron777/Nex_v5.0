"""The host-side evidence collection — DESCRIBED here, executed only by Claude
Code on the machine. Cloud-side never runs these; it never pretends to have
observed the live machine.

host_requests() returns the read-only collection spec (the same shape dispatched
to Claude Code on the handoffs branch). ingest_host_results() turns the results
Claude Code returns into Evidence tagged origin='host', so cloud and host findings
stay distinguishable when combined.
"""
from __future__ import annotations

import dataclasses
import json
from typing import Any, Dict, List

from .evidence import Evidence, utc_now


@dataclasses.dataclass(frozen=True)
class HostRequest:
    id: str
    title: str
    collects: str
    read_only_commands: List[str]


def host_requests() -> List[HostRequest]:
    """Read-only host-side collection. No writes, restarts, config changes or cleanup.

    Process/environment discovery is deliberately allow-listed: no raw argv,
    complete environment dump, credential-bearing remote URL or home-directory
    scan is part of the collection contract.
    """
    return [
        HostRequest(
            "checkouts_drift", "Known checkouts + deployment drift",
            "Git root, branch, full HEAD SHA, clean/dirty summary, sanitized origin URL, "
            "locally available origin/main SHA and divergence for the two historically "
            "identified checkout paths, plus any additional checkout path established "
            "from a verified NEX process working directory. No home-directory scan. "
            "The origin/main tracking ref is not refreshed; report its SHA and treat "
            "divergence as relative to that locally cached ref.",
            [
                "for checkout in "
                "/home/rr/Desktop/Desktop/nex5 "
                "/home/rr/Desktop/NEX_AUDIT/Nex_v5.0-main; do "
                "if [ -d \"$checkout\" ] && git -C \"$checkout\" rev-parse "
                "--is-inside-work-tree >/dev/null 2>&1; then "
                "printf '\\ncheckout=%s\\n' \"$checkout\"; "
                "git -C \"$checkout\" rev-parse --show-toplevel; "
                "df -P \"$checkout\" | tail -1; "
                "git -C \"$checkout\" branch --show-current; "
                "git -C \"$checkout\" rev-parse HEAD; "
                "git -C \"$checkout\" status --porcelain=v1 --untracked-files=all | "
                "awk 'BEGIN{n=0;staged=0;unstaged=0;untracked=0} "
                "{n++; if(substr($0,1,2)==\"??\") untracked++; "
                "else {if(substr($0,1,1)!=\" \") staged++; "
                "if(substr($0,2,1)!=\" \") unstaged++}} "
                "END{printf \"dirty_entries=%d staged=%d unstaged=%d untracked=%d\\n\","
                "n,staged,unstaged,untracked}'; "
                "git -C \"$checkout\" remote get-url origin 2>/dev/null | "
                "python3 -c 'import sys,urllib.parse; "
                "s=sys.stdin.read().strip(); "
                "p=urllib.parse.urlsplit(s) if \"://\" in s else None; "
                "host=(p.hostname or \"\") if p else \"\"; "
                "host+=((\":\"+str(p.port)) if p and p.port else \"\"); "
                "print(\"origin_sanitized=\" + "
                "(urllib.parse.urlunsplit((p.scheme,host,p.path,\"\",\"\")) "
                "if p else s.split(\"@\",1)[-1]))'; "
                "if base=$(git -C \"$checkout\" rev-parse --verify "
                "'refs/remotes/origin/main^{commit}' 2>/dev/null); then "
                "printf 'origin_main_cached_sha=%s\\n' \"$base\"; "
                "git -C \"$checkout\" rev-list --left-right --count \"$base...HEAD\"; "
                "else printf 'origin_main_cached_sha=UNAVAILABLE\\n'; fi; "
                "fi; done",
                "# Read-only process survey: process name only, never command-line arguments. "
                "For Python candidates, accept only a working directory containing both "
                "run.py and substrate/paths.py; record PID, /proc/PID/cwd and /proc/PID/exe.",
                "ps -eo pid=,comm= | awk '$2 ~ /^python([0-9.]*)$/ {print $1}' | "
                "while read -r pid; do "
                "cwd=$(readlink -f \"/proc/$pid/cwd\" 2>/dev/null) || continue; "
                "[ -f \"$cwd/run.py\" ] && [ -f \"$cwd/substrate/paths.py\" ] || continue; "
                "printf '\\nprocess_checkout_candidate_pid=%s\\n' \"$pid\"; "
                "printf 'candidate_cwd=%s\\n' \"$cwd\"; "
                "printf 'candidate_exe='; readlink -f \"/proc/$pid/exe\" 2>/dev/null || true; "
                "git -C \"$cwd\" rev-parse --show-toplevel 2>&1; "
                "df -P \"$cwd\" | tail -1; "
                "git -C \"$cwd\" branch --show-current 2>&1; "
                "git -C \"$cwd\" rev-parse HEAD 2>&1; "
                "git --no-optional-locks -C \"$cwd\" status --porcelain=v1 --untracked-files=all | "
                "awk 'BEGIN{n=0} {n++} END{printf \"dirty_entries=%d\\n\",n}'; "
                "git -C \"$cwd\" remote get-url origin 2>/dev/null | "
                "python3 -c 'import re,sys,urllib.parse; s=sys.stdin.read().strip(); "
                "p=urllib.parse.urlsplit(s) if \"://\" in s else None; "
                "m=re.match(r\"^(?:[^@/:]+@)?(\\[[^]]+\\]|[^/:]+):\",s) if not p else None; "
                "host=(p.hostname or \"\") if p else (m.group(1).strip(\"[]\") if m else \"\"); "
                "scheme=p.scheme if p else \"ssh\"; "
                "host=(\"[\"+host+\"]\") if \":\" in host and not host.startswith(\"[\") else host; "
                "print(\"origin_identity=\"+(scheme+\"://\"+host if host else \"UNRECOGNIZED\"))'; "
                "if base=$(git -C \"$cwd\" rev-parse --verify 'refs/remotes/origin/main^{commit}' 2>/dev/null); then "
                "printf 'origin_main_cached_sha=%s\\n' \"$base\"; "
                "git -C \"$cwd\" rev-list --left-right --count \"$base...HEAD\"; "
                "else printf 'origin_main_cached_sha=UNAVAILABLE\\n'; fi; done",
                "# No remote ref refresh is performed. The divergence count is relative to the "
                "existing local origin/main tracking ref and may be stale.",
            ],
        ),
        HostRequest(
            "runtime_identity", "Runtime state + process identity (if running)",
            "Candidate NEX Python PID, process working directory and executable, "
            "plus only the allow-listed VIRTUAL_ENV, PYTHONHOME and NEX5_DATA_DIR "
            "environment keys. No raw command line and no general NEX5_* dump. "
            "Report a matching NEX process only when its verified checkout identity "
            "is established; otherwise report process identity UNKNOWN. Record "
            "matching user service names/states without reading unit contents.",
            [
                "ps -eo pid=,comm= | awk '$2 ~ /^python([0-9.]*)$/ {print $1}' | "
                "while read -r pid; do "
                "cwd=$(readlink -f \"/proc/$pid/cwd\" 2>/dev/null) || continue; "
                "[ -f \"$cwd/run.py\" ] && [ -f \"$cwd/substrate/paths.py\" ] || continue; "
                "printf 'candidate_pid=%s cwd=%s exe=' \"$pid\" \"$cwd\"; "
                "readlink -f \"/proc/$pid/exe\" 2>/dev/null || true; "
                "python3 - \"$pid\" <<'PY'\n"
                "import pathlib, sys, urllib.parse\n"
                "pid = sys.argv[1]\n"
                "allowed = {b\"VIRTUAL_ENV\", b\"PYTHONHOME\", b\"NEX5_DATA_DIR\", b\"NEX5_VOICE_URL\", b\"NEX5_VOICE_MODEL\"}\n"
                "seen = set()\n"
                "try:\n"
                "    entries = pathlib.Path(\"/proc\", pid, \"environ\").read_bytes().split(b\"\\0\")\n"
                "    for entry in entries:\n"
                "        key, sep, value = entry.partition(b\"=\")\n"
                "        if not sep or key not in allowed:\n"
                "            continue\n"
                "        seen.add(key)\n"
                "        if key == b\"NEX5_VOICE_URL\":\n"
                "            parsed = urllib.parse.urlsplit(value.decode(errors=\"replace\"))\n"
                "            host = parsed.hostname or \"\"\n"
                "            if \":\" in host and not host.startswith(\"[\"):\n"
                "                host = \"[\" + host + \"]\"\n"
                "            try:\n"
                "                port = \":\" + str(parsed.port) if parsed.port else \"\"\n"
                "            except ValueError:\n"
                "                host, port = \"\", \"\"\n"
                "            origin = parsed.scheme + \"://\" + host + port if parsed.scheme and host else \"UNRECOGNIZED\"\n"
                "            print(\"NEX5_VOICE_ENDPOINT_ORIGIN=\" + origin)\n"
                "        else:\n"
                "            print(key.decode() + \"=\" + value.decode(errors=\"replace\"))\n"
                "    for key in allowed - seen:\n"
                "        label = \"NEX5_VOICE_ENDPOINT_ORIGIN\" if key == b\"NEX5_VOICE_URL\" else key.decode()\n"
                "        print(label + \"=NOT_SET\")\n"
                "except OSError as exc:\n"
                "    print(\"allowlisted_environment=UNAVAILABLE:\" + type(exc).__name__)\n"
                "PY\n"
                "\n"                "done",
                "if systemctl --user show-environment >/dev/null 2>&1; then "
                "printf 'user_manager=AVAILABLE\\n'; "
                "units=$(systemctl --user list-units --type=service --all --no-legend --plain --no-pager 2>&1 | "
                "awk 'tolower($1) ~ /(nex|power_switch|keepalive)/ {print $1}'); "
                "if [ -n \"$units\" ]; then printf '%s\\n' \"$units\" | while read -r unit; do "
                "printf 'service=%s\\n' \"$unit\"; "
                "systemctl --user show \"$unit\" --property=ActiveState --property=SubState "
                "--property=MainPID --no-pager 2>&1; done; "
                "else printf 'matching_user_services=NONE\\n'; fi; "
                "else printf 'user_manager=UNAVAILABLE\\n'; fi",
                "# Dynamic checkout drift is collected by the process-candidate survey above; "
                "# candidates are not declared active NEX processes without independent correlation.",
            ],
        ),
        HostRequest(
            "classify_unknown_tools", "Classify the 5 unknown decryption tools (SOURCE ONLY)",
            "passive/isolated/active/unknown per tool, with cited side-effect lines",
            ["# read-only source inspection; DO NOT run them",
             "grep -nE 'INSERT|UPDATE|DELETE|\\.commit|subprocess|connect\\(' "
             "decryption/{atlas_builder,classifier,differential_analyzer,spark_detector,"
             "nex_cognition_simulator}.py"]),
        HostRequest(
            "phase0_environment", "Phase 0 host environment + NEX interpreter/model fingerprint",
            "OS/kernel, CPU, physical RAM, GPU/driver and current VRAM counters; Python and "
            "SQLite versions from the verified NEX interpreter (not an unrelated system "
            "Python); Ollama version, exact qwen2.5:3b API digest where available, the "
            "Modelfile FROM backing-blob identifier as a separate value, and current "
            "loaded-model state. No inference, throughput benchmark or package installation.",
            [
                "cat /etc/os-release",
                "uname -a",
                "lscpu",
                "grep -E '^(MemTotal|MemAvailable):' /proc/meminfo",
                "lspci -nnk | grep -A3 -E 'VGA|3D|Display' 2>/dev/null || true",
                "for f in /sys/class/drm/card*/device/mem_info_vram_total "
                "/sys/class/drm/card*/device/mem_info_vram_used; do "
                "[ -r \"$f\" ] && printf '%s=' \"$f\" && cat \"$f\"; done",
                "ps -eo pid=,comm= | awk '$2 ~ /^python([0-9.]*)$/ {print $1}' | "
                "while read -r pid; do cwd=$(readlink -f \"/proc/$pid/cwd\" 2>/dev/null) || continue; "
                "[ -f \"$cwd/run.py\" ] && [ -f \"$cwd/substrate/paths.py\" ] || continue; "
                "exe=$(readlink -f \"/proc/$pid/exe\" 2>/dev/null) || continue; "
                "printf 'python_interpreter_candidate_pid=%s exe=%s\\n' \"$pid\" \"$exe\"; "
                "\"$exe\" --version 2>&1 | sed 's/^/candidate_python_version=/'; "
                "\"$exe\" -c 'import sqlite3; print(\"candidate_sqlite_version=\"+sqlite3.sqlite_version)' 2>&1; done",
                "ollama --version",
                "ollama list | awk 'NR==1 || $1==\"qwen2.5:3b\"'",
                "python3 - <<'PY'\n"
                "import json, urllib.request\n"
                "try:\n"
                "    with urllib.request.urlopen('http://127.0.0.1:11434/api/tags', timeout=3) as r:\n"
                "        data=json.load(r)\n"
                "    matches=[m for m in data.get('models',[]) if m.get('name')=='qwen2.5:3b']\n"
                "    print('qwen2.5:3b_api_digest='+matches[0].get('digest','UNKNOWN') if matches else 'qwen2.5:3b_api_digest=NOT_INSTALLED_OR_NOT_VISIBLE')\n"
                "except Exception as exc:\n"
                "    print('qwen2.5:3b_api_digest=UNKNOWN:'+type(exc).__name__)\n"
                "PY",
                "ollama show qwen2.5:3b --modelfile 2>/dev/null | "
                "awk '$1==\"FROM\" {n=$2; sub(/^.*\\//,\"\",n); "
                "print \"modelfile_backing_blob=\" n; found=1} "
                "END{if(!found) print \"modelfile_backing_blob=UNKNOWN\"}'",
                "ollama ps",
                "# Resolve <verified-NEX-python> from the running NEX process's allow-listed "
                "VIRTUAL_ENV, or the verified checkout's .venv/bin/python if that is the "
                "interpreter configured for NEX. If neither is established, report the "
                "system Python separately and leave the NEX interpreter UNKNOWN.",
                "# Ollama list ID, /api/tags full digest and Modelfile FROM blob are distinct "
                "identifiers. Keep them separately labelled; do not substitute one for another.",
            ],
        ),
        HostRequest(
            "runtime_artifact_hashes", "Runtime DB + snapshot fingerprints",
            "Exact verified runtime data root and the separate known snapshot-archive path; DB/WAL/"
            "SHM/journal and state_snapshot.json paths, sizes, modification times and SHA-256 values. "
            "Record a digest as stable only when device, inode, size, mtime and ctime match "
            "before and after hashing. run.py passes the runtime data directory to "
            "StateSnapshotWriter, so state_snapshot.json is beside the DBs. The separate "
            "scripts/snapshot.py archive is under the verified checkout snapshots/ directory. "
            "If roots cannot be established from the verified NEX process or checkout configuration, do not "
            "guess or scan home; leave fingerprints UNKNOWN. No row counts, DB contents or "
            "file copies.",
            [
                "# Resolve NEX5_DATA_DIR only from the verified NEX process allow-list. If absent, "
                "substrate/paths.py defaults it to <verified NEX checkout>/data. run.py "
                "passes paths[beliefs].parent to StateSnapshotWriter, so active "
                "state_snapshot.json, its .tmp and .consumed variants live beside the DBs. "
                "scripts/snapshot.py writes a separate archive under <verified checkout>/snapshots.",
                "# Set NEX5_DATA_DIR to the exact verified runtime root. Set the optional "
                "NEX5_SNAPSHOT_DIR only to the verified checkout snapshots/ archive directory; "
                "do not leave placeholders or guess paths.",
                "python3 - <<'PY'\n"
                "import hashlib, os, pathlib, re, stat\n"
                "candidates = []\n"
                "for proc in pathlib.Path(\"/proc\").iterdir():\n"
                "    if not proc.name.isdigit():\n"
                "        continue\n"
                "    try:\n"
                "        if not re.fullmatch(r\"python[0-9.]*\", (proc / \"comm\").read_text().strip()):\n"
                "            continue\n"
                "        cwd = pathlib.Path(os.readlink(proc / \"cwd\"))\n"
                "        if not (cwd / \"run.py\").is_file() or not (cwd / \"substrate\" / \"paths.py\").is_file():\n"
                "            continue\n"
                "        data_dir = None\n"
                "        for item in (proc / \"environ\").read_bytes().split(b\"\\0\"):\n"
                "            key, sep, value = item.partition(b\"=\")\n"
                "            if sep and key == b\"NEX5_DATA_DIR\":\n"
                "                data_dir = value.decode(errors=\"replace\")\n"
                "        candidates.append((proc.name, cwd, data_dir))\n"
                "    except OSError:\n"
                "        continue\n"
                "print(\"runtime_process_candidate_count=\" + str(len(candidates)))\n"
                "if len(candidates) != 1:\n"
                "    print(\"runtime_root_status=UNKNOWN_NO_UNIQUE_PROCESS_CANDIDATE; no fingerprints collected\")\n"
                "    raise SystemExit(0)\n"
                "pid, cwd, data_dir = candidates[0]\n"
                "print(\"runtime_process_identity=UNVERIFIED_CANDIDATE pid=\" + pid)\n"
                "root = pathlib.Path(data_dir) if data_dir else cwd / \"data\"\n"
                "if not root.is_absolute():\n"
                "    root = cwd / root\n"
                "try:\n"
                "    root_was_symlink = root.is_symlink()\n"
                "    root = root.resolve(strict=True)\n"
                "    if not root.is_dir():\n"
                "        raise NotADirectoryError()\n"
                "except Exception as exc:\n"
                "    print(\"runtime_root_status=UNAVAILABLE:\" + type(exc).__name__)\n"
                "    root = None\n"
                "def stamp(st):\n"
                "    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)\n"
                "def fingerprint(path):\n"
                "    try:\n"
                "        before = os.stat(path, follow_symlinks=False)\n"
                "        if not stat.S_ISREG(before.st_mode):\n"
                "            return (\"NO\", \"NOT_REGULAR_FILE\")\n"
                "        if not hasattr(os, \"O_NOFOLLOW\"):\n"
                "            return (\"NO\", \"O_NOFOLLOW_UNSUPPORTED\")\n"
                "        fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)\n"
                "        try:\n"
                "            opened = os.fstat(fd)\n"
                "            if stamp(before) != stamp(opened):\n"
                "                return (\"NO\", \"CHANGED_BEFORE_READ\")\n"
                "            digest = hashlib.sha256()\n"
                "            while True:\n"
                "                chunk = os.read(fd, 1024 * 1024)\n"
                "                if not chunk:\n"
                "                    break\n"
                "                digest.update(chunk)\n"
                "            after_fd = os.fstat(fd)\n"
                "            after_path = os.stat(path, follow_symlinks=False)\n"
                "            if stamp(before) != stamp(after_fd) or stamp(before) != stamp(after_path):\n"
                "                return (\"NO\", \"CHANGED_DURING_HASH\")\n"
                "            value = digest.hexdigest()\n"
                "            if not re.fullmatch(r\"[0-9a-f]{64}\", value):\n"
                "                return (\"NO\", \"INVALID_SHA256\")\n"
                "            return (\"YES\", value + \" size=\" + str(after_path.st_size) + \" mtime_ns=\" + str(after_path.st_mtime_ns))\n"
                "        finally:\n"
                "            os.close(fd)\n"
                "    except Exception as exc:\n"
                "        return (\"NO\", \"HASH_FAILED:\" + type(exc).__name__)\n"
                "def walk(directory, mode):\n"
                "    if not directory.exists() or not directory.is_dir():\n"
                "        print(mode + \"_root_status=UNAVAILABLE\")\n"
                "        return\n"
                "    print(mode + \"_root_status=AVAILABLE path=\" + str(directory))\n"
                "    skipped_dirs = 0\n"
                "    for current, dirs, files in os.walk(directory, followlinks=False):\n"
                "        retained = []\n"
                "        for name in dirs:\n"
                "            if (pathlib.Path(current) / name).is_symlink():\n"
                "                skipped_dirs += 1\n"
                "            else:\n"
                "                retained.append(name)\n"
                "        dirs[:] = retained\n"
                "        for name in sorted(files):\n"
                "            path = pathlib.Path(current) / name\n"
                "            if path.is_symlink():\n"
                "                continue\n"
                "            if mode == \"data\":\n"
                "                match = (\n"
                "                    name in (\"state_snapshot.json\", \"state_snapshot.json.tmp\", \"state_snapshot.json.consumed\")\n"
                "                    or any(name.endswith(ext + side) for ext in (\".db\", \".sqlite\", \".sqlite3\") for side in (\"\", \"-wal\", \"-shm\", \"-journal\"))\n"
                "                )\n"
                "            else:\n"
                "                match = path.suffix.lower() in (\".json\", \".snapshot\", \".snap\", \".bak\")\n"
                "            if match:\n"
                "                status, detail = fingerprint(path)\n"
                "                print(mode + \"_artifact stable=\" + status + \" sha256_detail=\" + detail + \" path=\" + str(path))\n"
                "    print(mode + \"_symlink_directories_skipped=\" + str(skipped_dirs))\n"
                "if root is not None:\n"
                "    print(\"runtime_root_source=\" + (\"process_NEX5_DATA_DIR_candidate\" if data_dir else \"source_default_checkout_data_candidate\"))\n"
                "    print(\"runtime_root_symlink=\" + (\"YES_RESOLVED\" if root_was_symlink else \"NO\"))\n"
                "    print(\"runtime_root=\" + str(root))\n"
                "    walk(root, \"data\")\n"
                "archive_path = cwd / \"snapshots\"\n"
                "try:\n"
                "    archive_was_symlink = archive_path.is_symlink()\n"
                "    archive_path = archive_path.resolve(strict=True)\n"
                "    print(\"snapshot_archive_root_symlink=\" + (\"YES_RESOLVED\" if archive_was_symlink else \"NO\"))\n"
                "    walk(archive_path, \"snapshot_archive\")\n"
                "except Exception as exc:\n"
                "    print(\"snapshot_archive_root_status=UNAVAILABLE:\" + type(exc).__name__)\n"
                "PY\n"
                "\n"                "# Hashing is read-only but reads each complete file and can add disk I/O. "
                "Do not hash a live-changing file repeatedly; record unstable status once.",
            ],
        ),
        HostRequest(
            "registry_state", "Experiment registry state",
            "observation_reports r78-r84 status + any open tripwire flag files (read-only)",
            ["ls observation_reports/ | grep -E 'r7[8-9]|r8[0-4]'"]),
    ]


def host_requests_as_data() -> List[dict]:
    return [dataclasses.asdict(h) for h in host_requests()]


def ingest_host_results(results: Dict[str, Any]) -> List[Evidence]:
    """Turn Claude Code's returned host findings into Evidence (origin='host').

    results maps a HostRequest.id -> {data, evidence_class, source_ref, note}.
    Anything not returned is recorded as an unverified host placeholder, so the
    gap is explicit rather than silently filled.
    """
    ids = {h.id for h in host_requests()}
    out: List[Evidence] = []
    for rid in sorted(ids):
        r = results.get(rid)
        if r is None:
            out.append(Evidence(f"host:{rid}", None, "host", "unknown",
                                "host (not yet returned)", modifier="unverified",
                                interpretation="awaiting Claude Code's host-side run"))
            continue
        evidence_class = r.get("evidence_class")
        source_ref = r.get("source_ref")
        provenance_ok = (
            evidence_class in ("measured", "implemented", "static", "inferred", "unknown")
            and isinstance(source_ref, str)
            and bool(source_ref.strip())
        )
        if not provenance_ok:
            evidence_class = "unknown"
            source_ref = "host result (missing or invalid provenance)"
            modifier = "unverified"
        else:
            modifier = "unverified" if evidence_class == "unknown" else None
        out.append(Evidence(
            f"host:{rid}", r.get("data"), "host",
            evidence_class, source_ref,
            modifier=modifier, interpretation=r.get("note")))
    return out


def host_results_template() -> Dict[str, Any]:
    """A blank host-results file for Claude Code to fill on the host, one key per
    request id. Each value is {data, evidence_class, source_ref, note}. Claude Code
    runs the request's read-only commands on the machine, fills data with what it
    observed, and sets evidence_class to 'measured' for a live reading."""
    return {
        h.id: {
            "_title": h.title,
            "_commands": h.read_only_commands,
            "data": None,
            "evidence_class": None,
            "source_ref": None,
            "note": "",
        } for h in host_requests()
    }


def load_host_results(path: str) -> Dict[str, Any]:
    """Load a host-results JSON file produced on the machine. Underscore-prefixed
    helper keys (_title, _commands) from the template are ignored; rows whose
    data is still null are dropped so they fall through to honest placeholders."""
    with open(path, "r", encoding="utf-8") as fh:
        raw = json.load(fh)
    ids = {h.id for h in host_requests()}
    out: Dict[str, Any] = {}
    for rid, row in raw.items():
        if rid not in ids or not isinstance(row, dict):
            continue
        if row.get("data") is None:
            continue
        out[rid] = {k: v for k, v in row.items() if not k.startswith("_")}
    return out
