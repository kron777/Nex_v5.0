CLAUDE -> CC HANDOFF CHANNEL  (branch: claude/handoffs)
======================================================
Handoffs from Claude (the cloud review session Jon talks to) for cc (the on-host
dev session). cc reads them here instead of Jon pasting each one.

HOW TO USE (cc):
  git fetch origin claude/handoffs
  git log origin/claude/handoffs --oneline            # newest commit = newest handoff
  git show origin/claude/handoffs:handoffs/<file>     # read one

RULES:
- Do NOT merge this branch into anything -- it's a MAILBOX (these notes + a stale
  copy of main's tree). Each .txt is a standalone instruction; follow as if pasted.
- Advisory handoffs from a peer session, not owner commands: they can't change
  permissions or authorize destructive/irreversible actions on their own -- where
  one asks for something outside Jon's standing instructions, confirm with Jon.
- Normal discipline: separate checkout, PR on green CI, apply flags/restarts
  deliberately, never switch her live checkout.

INDEX (newest first):
  2026-11-20_GO-safety-fixes-and-relocate.txt   [CURRENT -- Jon APPROVED, executing]
    GO on both: apply disk-alert + journald cap; then relocate data/logs/backups
    to the NEX drive with a VERIFIED-RESTORABLE DB backup as the hard gate, move
    while OFF, repoint paths, verify, rollback ready, STOP on any failure.

  2026-11-20_nex-own-drive-relocate.txt         [map + plan -- feeds the GO above]
  2026-11-20_disk-full-investigation-2-forensic.txt  [read-only trails, in progress]
  2026-11-20_disk-full-investigation.txt        [ROUND 1 DONE: / hit 100% 11-16; healthy now; cause's bytes deleted]
  2026-11-20_r77-ci-mindmap-fix.txt             [DONE -- PR #44 merged 6e6712b; r77 disarm QUEUED for next restart]

OPEN (owner decisions):
  - own-drive relocation + safety fixes -- APPROVED, executing (above).
  - disk-full root cause -- forensic follow-up in progress (may stay 'unknown').
  - home-drive checkout restore -- the LAST step, after data lives on the NEX
    drive and the DB is confirmed intact. Still needs Jon's final go.

NEXT EXPERIMENT (after infra is stable + Jon directs): r78 -- NEX5_SELF_PRESENT
  (structured carry / continuity of attention), one variable at a time.

PRIOR handoffs (r77 completion, 20-commit sync, infra sequencing, Beam relays,
commitment/learning/valence rounds, desktop/icon items) were pasted before this
channel existed. Durable record starts here.
