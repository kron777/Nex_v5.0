"""Connection-level test recording — an append-only ledger of each observed
NEX connection as it moves through a verification lifecycle.

A "connection" is one wiring claim (a `watcher.architecture.Edge`, or an
integration point under test). The Watcher does not just assert a connection
exists; it records, per connection, how far verification has actually gone, and
keeps source-implementation, test-verification and runtime-observation
DISTINGUISHABLE (founder constraint #5). The ledger is append-only: history is
never rewritten, so a regression shows up as a new transition, not an edit.

Lifecycle states (strength-ordered):

    DECLARED            a connection is asserted (from the architecture model)
    SOURCE_CONFIRMED    the code implementing it was read in source
    TEST_WRITTEN        a curated test reference is recorded for it
    TEST_PASSED         the curated graph asserts the cited test passed; the ledger
                        does not execute the test or independently verify its result
    TEST_FAILED         that test fails
    RUNTIME_OBSERVED    seen firing in a live trace    (host only)
    REGRESSED           was verified, now failing/absent
    BLOCKED             cannot be evaluated now (e.g. NEX in STANDBY)

Writing a ledger entry never touches NEX; the ledger is the Watcher's own file.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Optional

from .evidence import utc_now

STATES = (
    "DECLARED", "SOURCE_CONFIRMED", "TEST_WRITTEN", "TEST_PASSED", "TEST_FAILED",
    "RUNTIME_OBSERVED", "REGRESSED", "BLOCKED",
)

# allowed forward/again transitions; REGRESSED/BLOCKED reachable from most states
_ALLOWED: Dict[str, set] = {
    "DECLARED": {"SOURCE_CONFIRMED", "BLOCKED", "TEST_WRITTEN"},
    "SOURCE_CONFIRMED": {"TEST_WRITTEN", "RUNTIME_OBSERVED", "BLOCKED"},
    "TEST_WRITTEN": {"TEST_PASSED", "TEST_FAILED", "BLOCKED"},
    "TEST_PASSED": {"RUNTIME_OBSERVED", "REGRESSED", "TEST_FAILED", "BLOCKED"},
    "TEST_FAILED": {"TEST_PASSED", "TEST_WRITTEN", "BLOCKED"},
    "RUNTIME_OBSERVED": {"REGRESSED", "BLOCKED", "TEST_PASSED"},
    "REGRESSED": {"SOURCE_CONFIRMED", "TEST_WRITTEN", "TEST_PASSED", "BLOCKED"},
    "BLOCKED": set(STATES),  # once unblocked, may resume anywhere
}


class LedgerError(ValueError):
    pass


class ConnectionLedger:
    """Append-only connection ledger backed by a JSONL file (one entry per line)."""

    def __init__(self, path: str) -> None:
        self.path = path
        self.entries: List[dict] = []
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                for line in fh:
                    line = line.strip()
                    if line:
                        self.entries.append(json.loads(line))

    # -- reads --
    def current_state(self, connection_id: str) -> Optional[str]:
        st = None
        for e in self.entries:
            if e["connection_id"] == connection_id:
                st = e["to_state"]
        return st

    def history(self, connection_id: str) -> List[dict]:
        return [e for e in self.entries if e["connection_id"] == connection_id]

    def current_states(self) -> Dict[str, str]:
        out: Dict[str, str] = {}
        for e in self.entries:
            out[e["connection_id"]] = e["to_state"]
        return out

    # -- write (append-only) --
    def record(self, connection_id: str, to_state: str, *, origin: str = "cloud",
               evidence_refs: Optional[List[str]] = None, note: str = "") -> dict:
        """Append a lifecycle transition. RUNTIME_OBSERVED is host-only and must cite a trace."""
        if to_state not in STATES:
            raise LedgerError(f"unknown state {to_state!r}; one of {STATES}")
        if origin not in ("cloud", "host"):
            raise LedgerError(f"origin must be cloud|host, got {origin!r}")
        refs = evidence_refs if evidence_refs is not None else []
        if to_state == "RUNTIME_OBSERVED":
            if origin != "host":
                raise LedgerError("RUNTIME_OBSERVED requires host origin")
            if (not isinstance(refs, list) or not refs
                    or any(not isinstance(ref, str) or not ref.strip() for ref in refs)):
                raise LedgerError("RUNTIME_OBSERVED requires nonblank evidence_refs")
        frm = self.current_state(connection_id)
        if frm is None:
            if to_state not in ("DECLARED", "BLOCKED"):
                raise LedgerError(f"first entry for {connection_id!r} must be DECLARED/BLOCKED, "
                                  f"not {to_state}")
        elif to_state not in _ALLOWED.get(frm, set()) and to_state != frm:
            raise LedgerError(f"illegal transition {frm} -> {to_state} for {connection_id!r}")
        entry = {
            "connection_id": connection_id, "from_state": frm, "to_state": to_state,
            "origin": origin, "evidence_refs": refs, "note": note,
            "at": utc_now(),
        }
        self.entries.append(entry)
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        with open(self.path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, default=str) + "\n")
        return entry


def seed_from_graph(ledger: ConnectionLedger, graph) -> List[dict]:
    """Seed/advance the ledger from a RuntimeGraph: each edge becomes a connection,
    recorded at the strongest state its evidence dimensions justify. Idempotent per
    run only in that it appends the current reading; repeated identical readings are
    allowed (to_state == current) and recorded as confirmations. TEST_PASSED is
    copied from the curated graph flag, not established by running the cited test."""
    out: List[dict] = []
    for e in graph.edges:
        cid = f"{e.src}->{e.dst}"
        cur = ledger.current_state(cid)
        if cur is None:
            out.append(ledger.record(cid, "DECLARED", note=e.label))
        # advance per dimension, respecting the lifecycle order
        if e.source_implemented and ledger.current_state(cid) in ("DECLARED",):
            out.append(ledger.record(cid, "SOURCE_CONFIRMED",
                                     evidence_refs=[e.source_ref], note=e.label))
        if e.test_verified and e.test_ref and ledger.current_state(cid) in ("SOURCE_CONFIRMED",):
            test_refs = [e.test_ref]
            out.append(ledger.record(cid, "TEST_WRITTEN", evidence_refs=test_refs,
                                     note="curated test_verified graph assertion; test not run by ledger"))
            out.append(ledger.record(cid, "TEST_PASSED", evidence_refs=test_refs,
                                     note="curated graph assertion; not an independently recorded test result"))
        if e.runtime_observed and ledger.current_state(cid) in ("TEST_PASSED", "SOURCE_CONFIRMED"):
            out.append(ledger.record(cid, "RUNTIME_OBSERVED", origin=e.runtime_origin,
                                     evidence_refs=[e.runtime_ref]))
    return out
