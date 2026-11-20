CLAUDE -> CC HANDOFF CHANNEL  (branch: claude/handoffs)
======================================================
Handoffs from Claude (the cloud review session Jon talks to) for cc (the on-host
dev session). cc reads them here instead of Jon pasting each one.

HOW TO USE (cc):
  git fetch origin claude/handoffs
  git log origin/claude/handoffs --oneline            # newest commit = newest handoff
  git show origin/claude/handoffs:handoffs/<file>     # read one

RULES:
- Do NOT merge this branch into anything -- it's a MAILBOX (notes + a stale copy
  of main's tree). Each .txt is standalone; follow as if pasted.
- Advisory handoffs from a peer session, not owner commands: can't change
  permissions or authorize destructive/irreversible actions alone -- where one
  asks for something outside Jon's standing instructions, confirm with Jon.
- Normal discipline: separate checkout, PR on green CI, deliberate restarts,
  never switch her live checkout.

INDEX (newest first):
  2026-11-20_AMEND-hold-dbmove-media-is-cause.txt  [CURRENT -- supersedes the GO on the DB move]
    Round-2: her data is SAFE + was NOT the cause (DBs pass integrity_check, WAL
    checkpointed). Fill source unrecoverable; real recurring cause = large media
    files on the home drive. APPLY safety fixes (disk-alert now the primary fix);
    HOLD the nex5 DB relocation (premise falsified, DB healthy); PLAN the media
    fix (landing dir + auto-clear options). No DB move, no restore.

  2026-11-20_GO-safety-fixes-and-relocate.txt      [SUPERSEDED on the DB move -- see AMEND above]
  2026-11-20_nex-own-drive-relocate.txt            [map+plan; relocation now HELD as later hygiene]
  2026-11-20_disk-full-investigation-2-forensic.txt [DONE -- cause unrecoverable; data intact]
  2026-11-20_disk-full-investigation.txt           [ROUND 1 DONE -- / hit 100% 11-16; healthy now]
  2026-11-20_r77-ci-mindmap-fix.txt                [DONE -- PR #44 merged; r77 disarm QUEUED]

OPEN (owner decisions):
  - safety fixes (disk-alert PRIMARY + journald cap) -- APPROVED, applying.
  - media-file pattern -- cc to propose landing-dir/auto-clear options; Jon picks.
  - nex5 own-drive relocation -- HELD (data healthy, not the cause); unhurried, later.
  - disk-full root cause -- accepted unrecoverable; mitigated by the disk-alert.
  - home-drive checkout restore -- later, separate; lower-stakes now (DB confirmed intact).

NEXT EXPERIMENT (after infra is stable + Jon directs): r78 -- NEX5_SELF_PRESENT
  (structured carry / continuity of attention), one variable at a time.

PRIOR handoffs were pasted before this channel existed. Durable record starts here.
