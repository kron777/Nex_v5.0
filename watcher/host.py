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

from .evidence import Evidence


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
            "Git root, branch, full HEAD SHA, clean/dirty summary, redacted origin scheme/host, "
            "locally available origin/main SHA and divergence for the two historically "
            "identified checkout paths, plus any additional checkout path established "
            "from Python process-working-directory candidates. Candidates require independent PID/service correlation. No home scan. "
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
                "git --no-optional-locks -C \"$checkout\" status --porcelain=v1 --untracked-files=all | "
                "awk 'BEGIN{n=0;staged=0;unstaged=0;untracked=0} "
                "{n++; if(substr($0,1,2)==\"??\") untracked++; "
                "else {if(substr($0,1,1)!=\" \") staged++; "
                "if(substr($0,2,1)!=\" \") unstaged++}} "
                "END{printf \"dirty_entries=%d staged=%d unstaged=%d untracked=%d\\n\","
                "n,staged,unstaged,untracked}'; "
                "git -C \"$checkout\" remote get-url origin 2>/dev/null | "
                "python3 -c 'import re,sys,urllib.parse; s=sys.stdin.read().strip(); "
                "p=urllib.parse.urlsplit(s) if \"://\" in s else None; "
                "m=re.match(r\"^(?:[^@/:]+@)?(\\[[^]]+\\]|[^/:]+):\",s) if not p else None; "
                "host=(p.hostname or \"\") if p else (m.group(1).strip(\"[]\") if m else \"\"); "
                "scheme=p.scheme if p else \"ssh\"; "
                "host=(\"[\"+host+\"]\") if \":\" in host and not host.startswith(\"[\") else host; "
                "print(\"origin_identity=\"+(scheme+\"://\"+host if host else \"UNRECOGNIZED\"))'; "
                "if base=$(git -C \"$checkout\" rev-parse --verify "
                "'refs/remotes/origin/main^{commit}' 2>/dev/null); then "
                "printf 'origin_main_cached_sha=%s\\n' \"$base\"; "
                "git -C \"$checkout\" rev-list --left-right --count \"$base...HEAD\"; "
                "else printf 'origin_main_cached_sha=UNAVAILABLE\\n'; fi; "
                "fi; done",
                "# Read-only process survey: process name only, never command-line arguments. "
                "For Python candidates, accept only a working directory containing both "
                "run.py and substrate/paths.py; record PID, /proc/PID/cwd and /proc/PID/exe.",
                "ps -eo pid=,comm= | awk -v collector_pid=\"$NEX_WATCHER_COLLECTOR_PID\" '$1 != collector_pid && $2 ~ /^python([0-9.]*)$/ {print $1}' | "
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
            "Python process candidates with repository markers, PID, working directory and executable; "
            "plus allow-listed VIRTUAL_ENV, PYTHONHOME, NEX5_DATA_DIR, NEX5_VOICE_URL and NEX5_VOICE_MODEL "
            "environment metadata. Voice URL is redacted to origin only. No raw command line or broad environment dump. "
            "Candidates are not verified NEX processes until independently correlated with the service PID. "
            "Record matching service state and MainPID values, or explicit manager unavailability. "
            "Do not read service unit contents or raw process arguments. Absolute paths can reveal usernames/data layout; redact before third-party sharing.",
            [
                "pids=$(ps -eo pid=,comm= | awk -v collector_pid=\"$NEX_WATCHER_COLLECTOR_PID\" '$1 != collector_pid && $2 ~ /^python([0-9.]*)$/ {print $1}'); "
                "candidate_count=0; "
                "for pid in $pids; do "
                "cwd=$(readlink -f \"/proc/$pid/cwd\" 2>/dev/null) || continue; "
                "[ -f \"$cwd/run.py\" ] && [ -f \"$cwd/substrate/paths.py\" ] || continue; "
                "candidate_count=$((candidate_count+1)); "
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
                "done; "
                "[ \"$candidate_count\" -gt 0 ] || printf 'process_candidates=NONE_AFTER_FILTER\\n'",
                "if systemctl --user show-environment >/dev/null 2>&1; then "
                "printf 'user_manager=AVAILABLE\\n'; "
                "set -o pipefail; if units=$(systemctl --user list-units --type=service --all --no-legend --plain --no-pager 2>&1 | "
                "awk 'tolower($1) ~ /(nex|power_switch|keepalive)/ {print $1}'); then "
                "if [ -n \"$units\" ]; then printf '%s\\n' \"$units\" | while read -r unit; do "
                "printf 'service=%s\\n' \"$unit\"; "
                "systemctl --user show \"$unit\" --property=ActiveState --property=SubState "
                "--property=MainPID --no-pager 2>&1; done; "
                "else printf 'matching_user_services=NONE\\n'; fi; "
                "else printf 'user_unit_list=UNAVAILABLE\\n'; fi; "
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
            "OS/kernel, CPU, physical RAM, GPU driver modules/versions, per-device VRAM counters and cgroup memory; candidate Python and "
            "SQLite versions from a process executable candidate or, when no candidate is running, the keepalive source-defined "
            "runtime .venv Python/SQLite candidate; installed Ollama CLI version independent of NEX process state; selected model API digest where available, or a clearly labelled source-default Qwen candidate, the "
            "Modelfile FROM backing-blob identifier as a separate value, and current "
            "loaded-model state. No inference, throughput benchmark or package installation.",
            [
                "cat /etc/os-release",
                "uname -a",
                "lscpu",
                "grep -E '^(MemTotal|MemAvailable):' /proc/meminfo",
                "lspci -nnk | grep -A3 -E 'VGA|3D|Display' 2>/dev/null || true",
                "for module in amdgpu nvidia i915 xe; do if [ -d \"/sys/module/$module\" ]; then "
                "printf 'gpu_driver_module=%s version=' \"$module\"; "
                "if [ -r \"/sys/module/$module/version\" ]; then cat \"/sys/module/$module/version\"; "
                "else printf 'NOT_EXPOSED\\n'; fi; fi; done",
                "seen=0; for device in /sys/class/drm/card[0-9]*/device; do "
                "[ -e \"$device\" ] || continue; seen=1; "
                "for metric in total used; do f=\"$device/mem_info_vram_$metric\"; "
                "if [ -r \"$f\" ]; then printf '%s=' \"$f\"; cat \"$f\"; "
                "else printf '%s=UNKNOWN\\n' \"$f\"; fi; done; done; "
                "[ \"$seen\" -eq 1 ] || printf 'VRAM_COUNTERS=UNKNOWN_NOT_EXPOSED\\n'",
                "for f in /sys/fs/cgroup/memory.max /sys/fs/cgroup/memory.current "
                "/sys/fs/cgroup/memory/memory.limit_in_bytes; do "
                "if [ -r \"$f\" ]; then printf '%s=' \"$f\"; cat \"$f\"; fi; done",
                "pids=$(ps -eo pid=,comm= | awk -v collector_pid=\"$NEX_WATCHER_COLLECTOR_PID\" '$1 != collector_pid && $2 ~ /^python([0-9.]*)$/ {print $1}'); "
                "candidate_count=0; "
                "for pid in $pids; do cwd=$(readlink -f \"/proc/$pid/cwd\" 2>/dev/null) || continue; "
                "[ -f \"$cwd/run.py\" ] && [ -f \"$cwd/substrate/paths.py\" ] || continue; "
                "exe=$(readlink -f \"/proc/$pid/exe\" 2>/dev/null) || continue; "
                "candidate_count=$((candidate_count+1)); "
                "printf 'python_interpreter_candidate_pid=%s exe=%s\\n' \"$pid\" \"$exe\"; "
                "\"$exe\" --version 2>&1 | sed 's/^/candidate_python_version=/'; "
                "\"$exe\" -c 'import sqlite3; print(\"candidate_sqlite_version=\"+sqlite3.sqlite_version)' 2>&1; done; "
                "if [ \"$candidate_count\" -eq 0 ]; then "
                "candidate_exe=/home/rr/Desktop/Desktop/nex5/.venv/bin/python3; "
                "if [ -x \"$candidate_exe\" ]; then "
                "printf 'python_interpreter_candidate_source=keepalive_venv_default_not_live_process\\n'; "
                "printf 'python_interpreter_candidate_exe=%s\\n' \"$candidate_exe\"; "
                "\"$candidate_exe\" --version 2>&1 | sed 's/^/candidate_python_version=/'; "
                "\"$candidate_exe\" -c 'import sqlite3; print(\"candidate_sqlite_version=\"+sqlite3.sqlite_version)' 2>&1; "
                "else printf 'python_interpreter_candidate=UNKNOWN_NO_PROCESS_OR_KEEPALIVE_VENV\\n'; fi; fi",
                "python3 - <<'PY'\n"
                "import ipaddress, json, os, pathlib, re, subprocess, urllib.parse, urllib.request\n"
                "\n"
                "candidates = []\n"
                "for proc in pathlib.Path(\"/proc\").iterdir():\n"
                "    if not proc.name.isdigit():\n"
                "        continue\n"
                "    if proc.name in {str(os.getpid()), os.environ.get(\"NEX_WATCHER_COLLECTOR_PID\", \"\")}:\n"
                "        continue\n"
                "    try:\n"
                "        if not re.fullmatch(r\"python[0-9.]*\", (proc / \"comm\").read_text().strip()):\n"
                "            continue\n"
                "        cwd = pathlib.Path(os.readlink(proc / \"cwd\"))\n"
                "        if not (cwd / \"run.py\").is_file() or not (cwd / \"substrate\" / \"paths.py\").is_file():\n"
                "            continue\n"
                "        env = {}\n"
                "        for item in (proc / \"environ\").read_bytes().split(b\"\\0\"):\n"
                "            key, sep, value = item.partition(b\"=\")\n"
                "            if sep and key in (b\"NEX5_VOICE_URL\", b\"NEX5_VOICE_MODEL\"):\n"
                "                env[key.decode()] = value.decode(errors=\"replace\")\n"
                "        candidates.append((proc.name, cwd, env))\n"
                "    except OSError:\n"
                "        continue\n"
                "\n"
                "print(\"python_process_candidates=\" + str(len(candidates)))\n"
                "\n"
                "# This reports the installed local CLI version and does not require a running NEX process.\n"
                "try:\n"
                "    version_result = subprocess.run(\n"
                "        [\"ollama\", \"--version\"], capture_output=True, text=True, timeout=5, check=False\n"
                "    )\n"
                "    print(\"ollama_version=\" + (version_result.stdout.strip() or version_result.stderr.strip() or \"UNKNOWN\"))\n"
                "except Exception as exc:\n"
                "    print(\"ollama_version_status=UNKNOWN:\" + type(exc).__name__)\n"
                "\n"
                "if len(candidates) == 1:\n"
                "    pid, cwd, env = candidates[0]\n"
                "    raw_url = env.get(\"NEX5_VOICE_URL\", \"http://localhost:11434/v1/chat/completions\")\n"
                "    model = env.get(\"NEX5_VOICE_MODEL\", \"qwen2.5:3b\")\n"
                "    model_is_runtime_candidate = True\n"
                "    model_selection_source = \"process_environment\" if \"NEX5_VOICE_MODEL\" in env else \"run.py_default\"\n"
                "    url_selection_source = \"process_environment\" if \"NEX5_VOICE_URL\" in env else \"run.py_default\"\n"
                "    print(\"voice_config_source=single_process_candidate_not_yet_verified\")\n"
                "else:\n"
                "    print(\"voice_endpoint_identity=UNKNOWN_NO_UNIQUE_PROCESS_CANDIDATE\")\n"
                "    pid, cwd, env = None, None, {}\n"
                "    # run.py and voice/llm.py source defaults; this is not proof of deployed selection.\n"
                "    raw_url = \"http://127.0.0.1:11434/v1/chat/completions\"\n"
                "    model = \"qwen2.5:3b\"\n"
                "    model_is_runtime_candidate = False\n"
                "    model_selection_source = \"source_default_not_runtime_selected\"\n"
                "    url_selection_source = \"source_default_loopback_not_runtime_verified\"\n"
                "    print(\"voice_config_source=source_default_only_no_unique_process_candidate\")\n"
                "\n"
                "parsed = urllib.parse.urlsplit(raw_url)\n"
                "host = parsed.hostname or \"\"\n"
                "try:\n"
                "    port = parsed.port\n"
                "except ValueError:\n"
                "    port, host = None, \"\"\n"
                "try:\n"
                "    loopback = ipaddress.ip_address(host).is_loopback\n"
                "except ValueError:\n"
                "    loopback = host.lower() == \"localhost\"\n"
                "safe_host = (\"[\" + host + \"]\") if \":\" in host and not host.startswith(\"[\") else host\n"
                "safe_port = port if port is not None else (80 if parsed.scheme == \"http\" else 443 if parsed.scheme == \"https\" else None)\n"
                "origin = parsed.scheme + \"://\" + safe_host + (\":\" + str(safe_port) if safe_port else \"\") if parsed.scheme and host else \"UNRECOGNIZED\"\n"
                "print(\"voice_endpoint_origin=\" + origin)\n"
                "print(\"voice_model_tag=\" + model)\n"
                "print(\"voice_url_source=\" + url_selection_source)\n"
                "print(\"voice_model_source=\" + model_selection_source)\n"
                "print(\"ollama_model_inventory_source=\" + (\n"
                "    model_selection_source if model_is_runtime_candidate else \"source_default_candidate_not_runtime_selected\"\n"
                "))\n"
                "\n"
                "known_path = parsed.path.rstrip(\"/\").endswith(\"/v1/chat/completions\")\n"
                "if not loopback or not safe_port or not known_path or parsed.username or parsed.password or parsed.query or parsed.fragment:\n"
                "    digest_label = \"configured_model_api_digest\" if model_is_runtime_candidate else \"source_default_model_api_digest\"\n"
                "    print(digest_label + \"=UNKNOWN_ENDPOINT_NOT_SAFE_TO_QUERY\")\n"
                "    raise SystemExit(0)\n"
                "\n"
                "ollama_host = parsed.scheme + \"://\" + safe_host + (\":\" + str(safe_port) if safe_port else \"\")\n"
                "try:\n"
                "    with urllib.request.urlopen(ollama_host + \"/api/tags\", timeout=3) as response:\n"
                "        tags = json.load(response)\n"
                "    models = [item for item in tags.get(\"models\", []) if item.get(\"name\") == model]\n"
                "    digest_label = \"configured_model_api_digest\" if model_is_runtime_candidate else \"source_default_model_api_digest\"\n"
                "    print(digest_label + \"=\" + (models[0].get(\"digest\", \"UNKNOWN\") if models else \"NOT_INSTALLED_OR_NOT_VISIBLE\"))\n"
                "except Exception as exc:\n"
                "    digest_label = \"configured_model_api_digest\" if model_is_runtime_candidate else \"source_default_model_api_digest\"\n"
                "    print(digest_label + \"=UNKNOWN:\" + type(exc).__name__)\n"
                "\n"
                "cli_env = dict(os.environ)\n"
                "cli_env[\"OLLAMA_HOST\"] = ollama_host\n"
                "for label, args in (\n"
                "    (\"ollama_list\", [\"ollama\", \"list\"]),\n"
                "    (\"modelfile\", [\"ollama\", \"show\", model, \"--modelfile\"]),\n"
                "    (\"ollama_ps\", [\"ollama\", \"ps\"]),\n"
                "):\n"
                "    try:\n"
                "        result = subprocess.run(args, capture_output=True, text=True, timeout=5, env=cli_env, check=False)\n"
                "        if label == \"modelfile\":\n"
                "            blob = next((\n"
                "                line.strip().split(None, 1)[1].rsplit(\"/\", 1)[-1]\n"
                "                for line in result.stdout.splitlines() if line.strip().startswith(\"FROM \")\n"
                "            ), None)\n"
                "            print(\"modelfile_backing_blob=\" + (blob or \"UNKNOWN\"))\n"
                "        elif label == \"ollama_list\":\n"
                "            rows = [\n"
                "                line for line in result.stdout.splitlines()\n"
                "                if line.split() and line.split()[0] == model\n"
                "            ]\n"
                "            print(\"ollama_list_model_entry=\" + (rows[0] if rows else \"NOT_FOUND\"))\n"
                "        elif label == \"ollama_ps\":\n"
                "            print(\"ollama_ps_status=\" + (\"OK\" if result.returncode == 0 else \"UNAVAILABLE\"))\n"
                "            if result.stdout.strip():\n"
                "                print(result.stdout.strip())\n"
                "    except Exception as exc:\n"
                "        print(label + \"_status=UNKNOWN:\" + type(exc).__name__)\n"
                "PY\n"
                "\n"                "# Candidate interpreter versions are unverified until the process PID is independently correlated. "
                "VIRTUAL_ENV, or the verified checkout's .venv/bin/python if that is the "
                "interpreter configured for NEX. If neither is established, report the "
                "system Python separately and leave the NEX interpreter UNKNOWN.",
                "# Ollama list ID, /api/tags full digest and Modelfile FROM blob are distinct "
                "identifiers. Keep them separately labelled; do not substitute one for another.",
            ],
        ),
        HostRequest(
            "runtime_artifact_hashes", "Runtime DB + snapshot fingerprints",
            "Candidate-derived runtime data root and candidate checkout snapshot archive; DB/WAL/"
            "SHM/journal and state_snapshot.json paths, sizes, modification times and SHA-256 values. "
            "Accept a digest only when device, inode, size, mtime_ns and ctime_ns match "
            "before opening, after opening and after hashing; failed hashes are unstable. run.py passes the runtime data directory to "
            "StateSnapshotWriter, so state_snapshot.json is beside the DBs. The separate "
            "scripts/snapshot.py archive is under the candidate checkout snapshots/ directory. "
            "With one process candidate, use its NEX5_DATA_DIR or checkout default, labelled unverified until service/PID correlation. "
            "With zero or multiple process candidates, fingerprint only the two historically named checkout defaults, explicitly "
            "labelled as candidate roots with active-root identity UNKNOWN. No home scan, SQL/row counts or file copies. "
            "No SQL queries or row counts and no file copies. Nested symlinks are skipped and counted; traversal errors mark the inventory INCOMPLETE.",
            [
                "# Runtime artifact roots use a unique process candidate when available. "
                "Without one, only the two historically named checkout defaults are fingerprinted, "
                "and are labelled as candidates rather than active runtime roots. No home scan.",
                "python3 - <<'PY'\n"
                "import hashlib, os, pathlib, re, stat\n"
                "\n"
                "def choose_artifact_roots(candidates, known_checkouts):\n"
                "    if len(candidates) == 1:\n"
                "        pid, cwd, data_dir = candidates[0]\n"
                "        root = pathlib.Path(data_dir) if data_dir else cwd / \"data\"\n"
                "        if not root.is_absolute():\n"
                "            root = cwd / root\n"
                "        source = (\n"
                "            \"process_NEX5_DATA_DIR_candidate_active_root_unverified\"\n"
                "            if data_dir else\n"
                "            \"process_checkout_default_data_candidate_active_root_unverified\"\n"
                "        )\n"
                "        return [(\"data\", root, source, pid, cwd / \"snapshots\")]\n"
                "\n"
                "    roots = []\n"
                "    for index, checkout in enumerate(known_checkouts, 1):\n"
                "        if (checkout / \"run.py\").is_file() and (checkout / \"substrate\" / \"paths.py\").is_file():\n"
                "            roots.append((\n"
                "                f\"known_checkout_{index}_data\",\n"
                "                checkout / \"data\",\n"
                "                \"known_checkout_default_candidate_active_root_unknown\",\n"
                "                None,\n"
                "                checkout / \"snapshots\",\n"
                "            ))\n"
                "    return roots\n"
                "\n"
                "candidates = []\n"
                "for proc in pathlib.Path(\"/proc\").iterdir():\n"
                "    if not proc.name.isdigit():\n"
                "        continue\n"
                "    if proc.name in {str(os.getpid()), os.environ.get(\"NEX_WATCHER_COLLECTOR_PID\", \"\")}:\n"
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
                "\n"
                "print(\"runtime_process_candidate_count=\" + str(len(candidates)))\n"
                "known_checkouts = [\n"
                "    pathlib.Path(\"/home/rr/Desktop/Desktop/nex5\"),\n"
                "    pathlib.Path(\"/home/rr/Desktop/NEX_AUDIT/Nex_v5.0-main\"),\n"
                "]\n"
                "targets = choose_artifact_roots(candidates, known_checkouts)\n"
                "if len(candidates) != 1:\n"
                "    print(\"runtime_root_status=UNKNOWN_NO_UNIQUE_PROCESS_CANDIDATE; only named historical checkout defaults may be fingerprinted\")\n"
                "if not targets:\n"
                "    print(\"runtime_root_status=UNKNOWN_NO_PROCESS_OR_NAMED_CHECKOUT_CANDIDATE; no fingerprints collected\")\n"
                "\n"
                "def stamp(st):\n"
                "    return (st.st_dev, st.st_ino, st.st_size, st.st_mtime_ns, st.st_ctime_ns)\n"
                "\n"
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
                "            return (\n"
                "                \"YES\",\n"
                "                value + \" device=\" + str(after_path.st_dev)\n"
                "                + \" inode=\" + str(after_path.st_ino)\n"
                "                + \" size=\" + str(after_path.st_size)\n"
                "                + \" mtime_ns=\" + str(after_path.st_mtime_ns)\n"
                "                + \" ctime_ns=\" + str(after_path.st_ctime_ns),\n"
                "            )\n"
                "        finally:\n"
                "            os.close(fd)\n"
                "    except Exception as exc:\n"
                "        return (\"NO\", \"HASH_FAILED:\" + type(exc).__name__)\n"
                "\n"
                "def walk(directory, mode):\n"
                "    if not directory.exists() or not directory.is_dir():\n"
                "        print(mode + \"_root_status=UNAVAILABLE\")\n"
                "        return\n"
                "    print(mode + \"_root_status=AVAILABLE path=\" + str(directory))\n"
                "    skipped_dirs = 0\n"
                "    skipped_files = 0\n"
                "    matched = 0\n"
                "    stable = 0\n"
                "    unstable = 0\n"
                "    walk_errors = 0\n"
                "\n"
                "    def onerror(exc):\n"
                "        nonlocal walk_errors\n"
                "        walk_errors += 1\n"
                "        error_path = getattr(exc, \"filename\", None)\n"
                "        print(\n"
                "            mode + \"_walk_error=YES path=\"\n"
                "            + (str(error_path) if error_path else \"UNKNOWN\")\n"
                "            + \" error=\" + type(exc).__name__\n"
                "        )\n"
                "\n"
                "    for current, dirs, files in os.walk(directory, followlinks=False, onerror=onerror):\n"
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
                "                skipped_files += 1\n"
                "                continue\n"
                "            if mode == \"data\" or mode.endswith(\"_data\"):\n"
                "                match = (\n"
                "                    name in (\"state_snapshot.json\", \"state_snapshot.json.tmp\", \"state_snapshot.json.consumed\")\n"
                "                    or any(name.endswith(ext + side)\n"
                "                           for ext in (\".db\", \".sqlite\", \".sqlite3\")\n"
                "                           for side in (\"\", \"-wal\", \"-shm\", \"-journal\"))\n"
                "                )\n"
                "            else:\n"
                "                match = path.suffix.lower() in (\".json\", \".snapshot\", \".snap\", \".bak\")\n"
                "            if match:\n"
                "                matched += 1\n"
                "                status, detail = fingerprint(path)\n"
                "                if status == \"YES\":\n"
                "                    stable += 1\n"
                "                else:\n"
                "                    unstable += 1\n"
                "                print(\n"
                "                    mode + \"_artifact stable=\" + status\n"
                "                    + \" sha256_detail=\" + detail + \" path=\" + str(path)\n"
                "                )\n"
                "    print(mode + \"_artifact_match_count=\" + str(matched))\n"
                "    print(mode + \"_artifact_stable_count=\" + str(stable))\n"
                "    print(mode + \"_artifact_unstable_count=\" + str(unstable))\n"
                "    print(mode + \"_symlink_directories_skipped=\" + str(skipped_dirs))\n"
                "    print(mode + \"_symlink_files_skipped=\" + str(skipped_files))\n"
                "    print(mode + \"_walk_error_count=\" + str(walk_errors))\n"
                "    if walk_errors:\n"
                "        walk_status = \"INCOMPLETE\"\n"
                "    elif skipped_dirs or skipped_files:\n"
                "        walk_status = \"COMPLETE_WITH_SKIPS\"\n"
                "    elif matched == 0:\n"
                "        walk_status = \"COMPLETE_EMPTY\"\n"
                "    else:\n"
                "        walk_status = \"COMPLETE\"\n"
                "    print(mode + \"_walk_status=\" + walk_status)\n"
                "\n"
                "def scan_artifact_roots(target_roots):\n"
                "    for mode, candidate_root, root_source, candidate_pid, candidate_archive in target_roots:\n"
                "        if candidate_pid is not None:\n"
                "            print(\"runtime_process_identity=UNVERIFIED_CANDIDATE pid=\" + candidate_pid)\n"
                "        else:\n"
                "            print(\"runtime_process_identity=UNKNOWN; no unique process candidate\")\n"
                "        print(mode + \"_root_source=\" + root_source)\n"
                "        try:\n"
                "            root_was_symlink = candidate_root.is_symlink()\n"
                "            root = candidate_root.resolve(strict=True)\n"
                "            if not root.is_dir():\n"
                "                raise NotADirectoryError()\n"
                "        except Exception as exc:\n"
                "            print(mode + \"_root_status=UNAVAILABLE:\" + type(exc).__name__)\n"
                "            root = None\n"
                "        if root is not None:\n"
                "            print(mode + \"_root_symlink=\" + (\"YES_RESOLVED\" if root_was_symlink else \"NO\"))\n"
                "            print(mode + \"_root=\" + str(root))\n"
                "            walk(root, mode)\n"
                "        try:\n"
                "            archive_was_symlink = candidate_archive.is_symlink()\n"
                "            archive_path = candidate_archive.resolve(strict=True)\n"
                "            print(mode + \"_snapshot_archive_root_symlink=\" + (\"YES_RESOLVED\" if archive_was_symlink else \"NO\"))\n"
                "            walk(archive_path, mode + \"_snapshot_archive\")\n"
                "        except Exception as exc:\n"
                "            print(mode + \"_snapshot_archive_root_status=UNAVAILABLE:\" + type(exc).__name__)\n"
                "\n"
                "scan_artifact_roots(targets)\n"
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
    leaves provenance blank until the host runner supplies an explicit class and
    source reference. Missing or invalid provenance is downgraded to unknown/unverified."""
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
