"""Typed registry and validator for NEX5_* environment flags (H8).

NEX's behaviour is gated by ~130 NEX5_* environment flags, read ad hoc via
os.environ.get(...) at scattered call sites. This module is the single place
that knows the full set. It does NOT replace those reads -- that migration is
separate and risky -- but it gives two things the sprawl lacked:

  * validate(): at startup, surface a mistyped flag (e.g. NEX5_COMPASSOIN=1)
    that would otherwise be silently ignored, and a value that cannot be
    parsed as its flag's type. Warn-only by default; strict in CI.
  * typed accessors (get_bool/get_int/get_float/get_str) for new code, so new
    flags do not add yet another bespoke os.environ.get parse.

KNOWN_FLAGS maps each flag to its value kind, inferred from how the codebase
reads it today:
  bool  -- compared against "1"
  int   -- parsed with int(...)
  float -- parsed with float(...)
  str   -- anything else (free-form; not value-checked)

An unknown flag is a typo to surface, not a reason to refuse to boot, so
validate() only logs by default. Pass strict=True, or set NEX5_CONFIG_STRICT=1
(itself a registered flag), to raise instead.
"""
from __future__ import annotations

import functools
import logging
import os
from typing import Optional

THEORY_X_STAGE = None

logger = logging.getLogger("nex5.config")

# name -> kind. Generated from a full grep of NEX5_* usage; keep in sync when
# a flag is added (validate() will flag an unregistered one as "unknown").
KNOWN_FLAGS: dict[str, str] = {
    "NEX5_ABSTAIN_CLOSE": "bool",
    "NEX5_ADMIN_HASH_FILE": "str",
    "NEX5_AFFECT_CARRY": "bool",
    "NEX5_AFFINITY_PROVENANCE": "str",  # off|shadow|on (affinity_loop D-A)
    "NEX5_AFFLICTIONS": "bool",
    "NEX5_ALOBHA": "bool",
    "NEX5_AMOHA": "bool",
    "NEX5_ANTILOOP": "bool",
    "NEX5_APPROACH": "bool",
    "NEX5_APRAMADA": "bool",
    "NEX5_ASSOC_N": "int",
    "NEX5_ASSOC_POOL": "int",
    "NEX5_ASSOC_RECALL": "bool",
    "NEX5_ATTRIB_CRYSTALLIZE": "bool",
    "NEX5_BACKUP_DIR": "str",
    "NEX5_BESTOFCLUSTER": "bool",
    "NEX5_BRANCH_TEMP": "float",
    "NEX5_BRIDGE": "bool",
    "NEX5_CARRYOVER": "bool",
    "NEX5_CHAT_ANTIECHO": "bool",
    "NEX5_CHAT_MEMORY": "bool",
    "NEX5_CHAT_WORKSPACE": "str",
    "NEX5_CHAT_WORKSPACE_BUDGET": "int",
    "NEX5_COMMITMENTS": "bool",
    "NEX5_COMMITMENT_VALENCE": "bool",
    "NEX5_COMMIT_CLOSE": "bool",
    "NEX5_COMPASS": "bool",
    "NEX5_COMPASSION": "bool",
    "NEX5_COMPASSION_V2": "bool",
    "NEX5_COMPASS_TRIM": "bool",
    "NEX5_CONFIG_STRICT": "bool",
    "NEX5_CONTINUITY_N": "str",
    "NEX5_CONVICTION": "str",
    "NEX5_CONVICTION_ORDER": "str",
    "NEX5_CONV_DB": "str",
    "NEX5_CURIOSITY": "bool",
    "NEX5_DATA_DIR": "str",
    "NEX5_DELIVER_N": "int",
    "NEX5_DRIFT_SCAN_N": "int",
    "NEX5_DRIVE_CONTENT": "bool",
    "NEX5_DYNAMIC_DB": "str",
    "NEX5_EDGE_WEIGHTED_FOUNTAIN": "bool",
    "NEX5_EQUANIMITY": "bool",
    "NEX5_EWF_W_EDGE": "str",
    "NEX5_EWF_W_RECENCY": "str",
    "NEX5_EWF_W_TIER": "str",
    "NEX5_EXPECT_LEARN": "bool",
    "NEX5_EXPECT_MOOD": "bool",
    "NEX5_FIRE_LANG_GUARD": "bool",
    "NEX5_FOCUS_PING_GLOBAL_COOLDOWN": "str",
    "NEX5_FOCUS_ROTATE": "bool",
    "NEX5_FOUNTAIN_DEDUP": "bool",
    "NEX5_FOUNTAIN_READINESS_MOD_OFF": "bool",
    "NEX5_FOUNTAIN_STATUS_URL": "str",
    "NEX5_FRAME_DEDUP": "bool",
    "NEX5_GENIUS_GRADE_OFF": "str",
    "NEX5_GENIUS_PROMPT_OFF": "str",
    "NEX5_GLOBAL_WORKSPACE": "str",
    "NEX5_GOVERNOR_OFF": "str",
    "NEX5_GUI_HOST": "str",
    "NEX5_GUI_PORT": "int",
    "NEX5_GW_SURPRISE_NONEMPTY": "bool",
    "NEX5_HOST": "str",
    "NEX5_HOT_OBSERVER": "bool",
    "NEX5_INTAKE_RESONANCE_OFF": "bool",
    "NEX5_INTAKE_TIGHT_CORE": "bool",
    "NEX5_L4_STAKES": "bool",
    "NEX5_L4_TEETH": "str",
    "NEX5_METACOG_VOICE": "bool",
    "NEX5_MOMENTUM": "str",
    "NEX5_MOOD": "bool",
    "NEX5_NO_PARROT": "str",
    "NEX5_OPERATOR_ANCHOR": "bool",
    "NEX5_OPERATOR_DOC": "str",
    "NEX5_OPERATOR_MODEL": "bool",
    "NEX5_OWNED_BELIEF": "bool",
    "NEX5_OWNED_BELIEF_EVERY_S": "str",
    "NEX5_OWNED_BELIEF_HORIZON_S": "str",
    "NEX5_OWNED_BELIEF_MIN_OBS": "str",
    "NEX5_OWN_CONTENT_RENDER": "bool",
    "NEX5_PARK_CAP": "int",
    "NEX5_PERSONA_INTERVAL": "int",
    "NEX5_PERSONA_LANG_GUARD": "bool",
    "NEX5_PERSONA_READ_N": "int",
    "NEX5_PERSONA_RESPONDER": "str",
    "NEX5_PHRASING_ROTATE": "bool",
    "NEX5_PORT": "int",
    "NEX5_PRASRABDHI": "bool",
    "NEX5_PROBE_SNAPSHOT_WINDOW_SEC": "int",
    "NEX5_PROBLEM_SELF_GATE": "bool",
    "NEX5_PROVENANCE": "bool",
    "NEX5_QUALITY_SYNTH": "bool",
    "NEX5_QUIET_HOURS": "str",
    "NEX5_RECONCILE": "bool",
    "NEX5_RECONCILER": "bool",
    "NEX5_RECONCILE_PXB": "str",
    "NEX5_RECONCILE_WB": "bool",
    "NEX5_RETRIEVAL_DEBOILER": "bool",
    "NEX5_RETRIEVAL_TEETH": "bool",
    "NEX5_RUT_EDGE": "bool",
    "NEX5_RUT_MIRROR_OFF": "str",
    "NEX5_SCORE_F2_V2": "bool",
    "NEX5_SELFPRED_HORIZON": "int",
    "NEX5_SELFPRED_THRESHOLD": "float",
    "NEX5_SELF_LAYER_N": "str",
    "NEX5_SELF_MAINTAIN_SHADOW": "bool",
    "NEX5_SELF_NARRATIVE": "bool",
    "NEX5_SELF_PRED": "bool",
    "NEX5_SELF_PRED_INTERVAL": "int",
    "NEX5_SELF_PRESENT": "bool",
    "NEX5_SENSE_OVERWHELM_N": "str",
    "NEX5_SIG_QUALITY": "bool",
    "NEX5_SOCIAL_DEPTH": "bool",
    "NEX5_SOCIAL_N": "str",
    "NEX5_SOURCE_KIND": "bool",
    "NEX5_SPEECH_ENABLED": "str",
    "NEX5_SPEECH_MIN_GAP": "float",
    "NEX5_SPEECH_PROB": "float",
    "NEX5_SPEECH_QUIET_DAMPING": "float",
    "NEX5_SPEECH_VOICE": "str",
    "NEX5_SRADDHA": "bool",
    "NEX5_STAKES": "bool",
    "NEX5_STAKES_DEEP": "bool",
    "NEX5_SUBSTRATE_EMIT": "bool",
    "NEX5_SURPRISE_WEIGHT": "str",
    "NEX5_SYNTH_EMIT": "str",
    "NEX5_SYNTH_FRESH": "bool",
    "NEX5_SYNTH_FRESH_SIBLING": "bool",
    "NEX5_SYNTH_KEEP": "bool",
    "NEX5_THROWNET": "bool",
    "NEX5_TIER_CLIMB": "bool",
    "NEX5_TZ": "str",
    "NEX5_VALENCE_DRIVE": "bool",
    "NEX5_VIRYA": "bool",
    "NEX5_VOICE_MODEL": "str",
    "NEX5_VOICE_URL": "str",
    "NEX5_WARRANT": "str",
    "NEX5_WARRANT_RECORD": "bool",
    "NEX5_WIDE_FOCUS": "bool",
    "NEX5_WIDE_MODES": "str",
    "NEX5_WORLD_CONSOLIDATE": "str",
    "NEX5_WORLD_PRED": "bool",
    "NEX5_WORLD_PRED_ASSET": "str",
    "NEX5_WORLD_PRED_HORIZON": "str",
    "NEX5_WORLD_PRED_INTERVAL": "str",
}

_TRUE = {"1", "true", "yes", "on"}


class ConfigError(ValueError):
    """Raised by validate(strict=True) when the environment has problems."""


def _env(env: Optional[dict]) -> dict:
    return os.environ if env is None else env


def is_known(name: str) -> bool:
    return name in KNOWN_FLAGS


def unknown_flags(env: Optional[dict] = None) -> list[str]:
    """NEX5_* vars present in the environment but not registered -- almost
    always a typo that is silently doing nothing."""
    e = _env(env)
    return sorted(k for k in e if k.startswith("NEX5_") and k not in KNOWN_FLAGS)


def _value_problem(name: str, value: str) -> Optional[str]:
    kind = KNOWN_FLAGS.get(name)
    if kind == "int":
        try:
            int(value)
        except (TypeError, ValueError):
            return f"{name}={value!r} is not an int"
    elif kind == "float":
        try:
            float(value)
        except (TypeError, ValueError):
            return f"{name}={value!r} is not a float"
    return None


def invalid_values(env: Optional[dict] = None) -> list[str]:
    """Registered flags whose value cannot be parsed as the flag's kind."""
    e = _env(env)
    out = []
    for k, v in e.items():
        if k in KNOWN_FLAGS:
            p = _value_problem(k, v)
            if p:
                out.append(p)
    return sorted(out)


def validate(env: Optional[dict] = None, *, strict: Optional[bool] = None,
             log: bool = True) -> list[str]:
    """Return a list of problem strings (unknown flags + unparsable values).

    Warn-only by default. Raises ConfigError when strict (or, when strict is
    None, when NEX5_CONFIG_STRICT=1 is set in the environment).
    """
    e = _env(env)
    problems: list[str] = []
    unk = unknown_flags(e)
    if unk:
        problems.append(
            "unknown NEX5_* flags (typo? silently ignored): " + ", ".join(unk)
        )
    problems.extend(invalid_values(e))
    if strict is None:
        strict = e.get("NEX5_CONFIG_STRICT") == "1"
    if problems and log:
        for p in problems:
            logger.warning("config: %s", p)
    if problems and strict:
        raise ConfigError("; ".join(problems))
    return problems


# -- typed accessors for new code (existing call sites are unchanged) --------
# get_bool follows the house convention: a flag is on iff its value is "1"
# (the broader truthy set is accepted too, so new flags are forgiving).

def get_bool(name: str, default: bool = False, env: Optional[dict] = None) -> bool:
    v = _env(env).get(name)
    return default if v is None else v.strip().lower() in _TRUE


def get_int(name: str, default: int, env: Optional[dict] = None) -> int:
    v = _env(env).get(name)
    if v is None:
        return default
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def get_float(name: str, default: float, env: Optional[dict] = None) -> float:
    v = _env(env).get(name)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def get_str(name: str, default: str = "", env: Optional[dict] = None) -> str:
    return _env(env).get(name, default)


# -- logging setup (D-C PR 1): one authority for the running process ----------
# The app logs through 8 named namespaces with NO root-level logging, so root
# stays at INFO -- a stricter root would silently drop seven of them from the
# soak log. Only known-noisy third-party loggers are quieted, and ONLY via
# setLevel: never propagate=False, which would stop their WARNING+ records
# reaching errors.py's health counter and make the metric read falsely clean.

_LOG_FORMAT = "%(asctime)s %(name)s %(levelname)s %(message)s"

# App logger namespaces (kept at INFO via root). Used by the test, not to set
# levels -- they inherit root, so a new namespace is INFO by default too.
APP_LOG_NAMESPACES = ("theory_x", "nex5", "substrate", "stage6_fountain",
                      "stage1_sense", "server", "seed", "gui")

NOISY_THIRD_PARTY = ("werkzeug", "urllib3", "httpx", "httpcore",
                     "sentence_transformers", "transformers",
                     "huggingface_hub", "filelock", "asyncio", "matplotlib")

_log_configured = False


# ── NEX's clock ──────────────────────────────────────────────────────────────
# One zone for everything that shapes HER sense of time: scheduled daily
# activities, quarter-day identity/witness/pattern ticks, the time she reads in
# her prompt, her temporal sense, hour-of-day features. Before this, five
# modules hardcoded Europe/Amsterdam, the decoder used a fixed "+2 (May, CEST)"
# offset, and the rest followed the machine's zone -- three clocks at once.
# Operator log-line timestamps are not her clock and are left alone.
DEFAULT_TZ = "Africa/Johannesburg"   # the owner's zone (SAST, UTC+2, no DST)


@functools.lru_cache(maxsize=8)
def _zone(name: str):
    from zoneinfo import ZoneInfo
    try:
        return ZoneInfo(name)
    except Exception:
        logger.warning("NEX5_TZ=%r is not a valid IANA zone; using %s",
                       name, DEFAULT_TZ)
        return ZoneInfo(DEFAULT_TZ)


def local_tz():
    """NEX's timezone: NEX5_TZ (an IANA name), default Africa/Johannesburg.
    Resolved once per distinct value."""
    return _zone(os.environ.get("NEX5_TZ") or DEFAULT_TZ)


def local_now():
    """Aware datetime in NEX's timezone."""
    import datetime
    return datetime.datetime.now(local_tz())


def local_dt(ts: float):
    """Aware datetime in NEX's timezone for a unix timestamp."""
    import datetime
    return datetime.datetime.fromtimestamp(ts, local_tz())


def local_utc_offset_seconds(ts: Optional[float] = None) -> int:
    """NEX's zone's UTC offset at ts (default now), for SQL that buckets unix
    timestamps by local hour/day: strftime(..., ts + ?, 'unixepoch') instead of
    SQLite's 'localtime', which follows the machine's zone. One offset for the
    whole query is exact for a zone without DST (SAST); with DST it can shift
    rows within an hour of a transition."""
    import time as _time
    off = local_dt(_time.time() if ts is None else ts).utcoffset()
    return int(off.total_seconds()) if off is not None else 0


def setup_logging(level: int = logging.INFO) -> None:
    """Configure process logging once. Idempotent. Root at `level` (INFO);
    third-party noise quieted to WARNING; errors.py's central handler installed."""
    global _log_configured
    if _log_configured:
        return
    root = logging.getLogger()
    root.setLevel(level)
    if not any(isinstance(h, logging.StreamHandler) for h in root.handlers):
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(_LOG_FORMAT))
        root.addHandler(h)
    for name in NOISY_THIRD_PARTY:
        logging.getLogger(name).setLevel(logging.WARNING)
    try:
        import errors
        errors.install_handler(root)
    except Exception:
        pass
    _log_configured = True
