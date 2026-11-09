"""Property 13 — finitude: a real, persisted-spend, per-moment budget.

SHADOW MODULE — NOT IN THE LIVE PATH.
Nothing in gui/server.py or selector.py imports this file.
Wiring target: 2026-11-21 (r77 close). See MIND_MAP.yaml p13_finitude.

Why a shadow and not a wire-up: gui/server.py's chat-block assembly and
selector.py's fountain injection are both live-measured, load-bearing code
inside the r77 freeze window (closes ~2026-11-21). They are off-limits
regardless of flag-gating until then. This module is a stand-in that mirrors
the real chat-path budget's semantics without touching gui/server.py, so it
can be pointed at the real call site once the freeze lifts.

INTERFACE CONTRACT — the real function this shadow delegates to (DELEGATE
mode, not a duplicate): `select_within_budget` is PURE — no I/O, no DB
write, no mutation of its arguments. Confirmed by reading it directly.

    theory_x/stage_tom/global_workspace.py:144-166

    def select_within_budget(candidates: list[tuple[float, str, bool]],
                              char_budget: int) -> list[str]:
        '''candidates: (salience, text, exempt). Keeps every exempt
        candidate (still counted against the budget), then admits the
        rest by descending salience until char_budget is reached. Returns
        kept texts in original order.'''

Because it's pure, the shadow does not reimplement selection — it computes
`remaining` locally and calls the real function with it. Every measurement
this module produces about *selection* is therefore a measurement of the
real selector; what remains unverified is only whether the live caller
(gui/server.py) is actually passing it a `remaining` that has been debited
by real spend()s — that is the open claim this shadow does not close (see
Step 3 budget semantics below, and test_shadow_budget_reorders_real_selection's
docstring).

Two objects, not one — do not conflate them:

  Balance   per-moment. Fresh at moment start, capped, structurally
            enforced (this class). Answers finitude: it cannot be widened
            away mid-moment.
  Spend     permanent. One immutable ledger entry per draw, in
            shadow_budget_spend (substrate/schema/dynamic.sql). Answers
            irreversibility: it cannot be refunded.

A balance that survived a restart would be a lifetime quota, not a price:
it would make refuse() a resource-management game (past prices depending on
process history), and a reset balance would refund every spend so far. So
`remaining` lives only in this object's memory for the moment's lifetime;
only the fact that a draw happened is persisted.

The consequence this budget exists to support (design only, not implemented
here — it needs refuse(), which is still blocked): if a moment cannot afford
to hold a tension, it must resolve it, not drop it silently. Nothing vetoes;
scarcity simply runs out, and running out is what forces the commitment.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import nex_config
from theory_x.stage_tom.global_workspace import select_within_budget

_CAPACITY_FLAG = "NEX5_SHADOW_BUDGET_CAPACITY"
_DEFAULT_CAPACITY = 700  # half of NEX5_CHAT_WORKSPACE_BUDGET's own default (1400) --
# deliberately tight so a realistic candidate set actually binds (see Step 0
# BINDING finding below); config, not a literal -- override via the flag.


class InsufficientBudget(Exception):
    """Raised by Budget.spend() on overdraw. Never clamped, never swallowed --
    a caller that wants to recover must catch this explicitly."""


@dataclass(frozen=True)
class Receipt:
    amount: int
    entry_id: int
    remaining_after: int


class Budget:
    """One moment's spending balance. Construct fresh per moment; never reuse
    across moments or persist the instance itself.

    `remaining` is material a caller may read to price candidates. It is
    never a gate: nothing in this module raises, blocks, or drops a
    candidate based on `remaining` except spend() itself refusing an
    overdraw (that refusal is about money, not about the candidate).
    """

    def __init__(self, dyn_writer, moment_id: Optional[str] = None,
                 capacity: Optional[int] = None):
        self._writer = dyn_writer
        self.moment_id = moment_id or f"shadow-{time.time():.6f}"
        self.capacity = (capacity if capacity is not None
                          else nex_config.get_int(_CAPACITY_FLAG, _DEFAULT_CAPACITY))
        self._spent = 0

    @property
    def remaining(self) -> int:
        return self.capacity - self._spent

    def check_capacity(self, amount: int) -> None:
        """Pure check, no mutation: raises if `amount` can't be drawn right
        now. Factored out of spend() so a second writer (ledger_primitives.
        refuse()) can reuse the exact same capacity rule while writing its
        own row into its own table, in its own transaction, rather than
        going through spend()'s shadow_budget_spend write. Shared check,
        independent writes -- see ledger_primitives.py's module docstring
        for why spend()'s own target table didn't move."""
        if amount <= 0:
            raise ValueError(f"spend amount must be > 0, got {amount}")
        if amount > self.remaining:
            raise InsufficientBudget(
                f"moment {self.moment_id}: cannot spend {amount}, "
                f"only {self.remaining} remaining of capacity {self.capacity}")

    def spend(self, amount: int) -> Receipt:
        """Write one immutable ledger entry AND decrement `remaining`, as one
        unit: the entry is written first; `_spent` only advances if that
        write succeeds, so a failed write never leaves a phantom decrement,
        and a successful decrement never happens without a row to show for
        it (test_shadow_atomicity).
        """
        self.check_capacity(amount)
        remaining_after = self.remaining - amount
        entry_id = self._writer.write(
            "INSERT INTO shadow_budget_spend "
            "(moment_id, amount, remaining_after, created_at) "
            "VALUES (?, ?, ?, ?)",
            (self.moment_id, amount, remaining_after, time.time()),
        )
        self._spent += amount
        return Receipt(amount=amount, entry_id=entry_id, remaining_after=remaining_after)

    def select(self, candidates: "list[tuple[float, str, bool]]") -> list[str]:
        """The reader: delegates to the real select_within_budget with this
        moment's current `remaining` as the char budget. A Budget with
        writers (spend) and no reader would be a counter, not a Price —
        this method is what makes it one (test_shadow_budget_reorders_real_selection).
        """
        return select_within_budget(candidates, self.remaining)
