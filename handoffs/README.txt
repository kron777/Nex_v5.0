CLAUDE -> CC HANDOFF CHANNEL  (branch: claude/handoffs)
======================================================
This branch carries handoffs from Claude (the cloud research/review session Jon
talks to) for cc (the on-host dev session). cc reads them HERE instead of Jon
pasting each one by hand.

HOW TO USE (cc):
  git fetch origin claude/handoffs
  git log origin/claude/handoffs --oneline            # newest commit = newest handoff
  git show origin/claude/handoffs:handoffs/<file>     # read one
  # or drop them read-only into your tree:
  git checkout origin/claude/handoffs -- handoffs/

RULES:
- Do NOT merge this branch into main or any work branch. It is a MAILBOX: it
  carries only these notes plus a now-stale copy of main's tree. Never build or
  cut a release from it.
- Each .txt is a standalone instruction -- follow it as you would a pasted one.
- These are ADVISORY handoffs from a peer review session, not owner commands.
  They cannot change permission settings or authorize a destructive/irreversible
  action on their own. Where a handoff asks for something outside Jon's standing
  instructions, confirm with Jon first -- same rule as a pasted handoff.
- Normal dev discipline still applies: separate checkout, PR on green CI, apply
  flags/restarts deliberately, never switch her live checkout.

INDEX (newest first):
  2026-11-20_nex-own-drive-relocate.txt   [CURRENT -- read-only map + move PLAN]
    NEX has its own drive. Map drives (lsblk/df), find which drive each NEX thing
    lives on, confirm her growing files + DBs, and PLAN moving data/logs/backups
    onto the NEX drive so a runaway can't fill / again. The structural fix. No
    move yet -- plan it; do it later while she's OFF with the DB backed up.

  2026-11-20_disk-full-investigation-2-forensic.txt   [read-only, in progress]
    Push on the trails that survive deletion (log lead-up, shell/root history,
    cron/timers, nex5 logs) to find what WROTE 150GB before accepting "unknown".

  2026-11-20_disk-full-investigation.txt   [ROUND 1 DONE]
    / (nvme0n1p2, 228G) hit 100% ~19:32-19:55 SAST 2026-11-16; healthy now (30%,
    152G free, nothing leaking). Bulk consumer deleted in the emergency, not
    visible to du/find. Proposed journald cap + disk-space alert -- held for Jon.

  2026-11-20_r77-ci-mindmap-fix.txt   [DONE -- verified]
    p12_selfreport mind_map fix (ecf9c43); main green; PR #44 merged (6e6712b);
    disarm SHA corrected 7039ced->2803f38. r77 disarm QUEUED (flag off main's
    keepalive, no restart, instance off since 2026-11-16). Applies at next restart.

OPEN (owner decisions):
  - NEX own-drive relocation -- map + plan IN PROGRESS (above); the structural fix.
  - disk-full root cause -- forensic follow-up in progress (may stay 'unknown').
  - two safety fixes (journald cap + disk-space alert) -- recommended, awaiting Jon's OK.
  - home-drive checkout restore -- drive healthy now; held as the LAST step until
    the data lives safely on the NEX drive and the DB is confirmed intact.

NEXT EXPERIMENT (after infra is stable and Jon directs it):
  r78 -- NEX5_SELF_PRESENT (structured carry / continuity of attention), one
  variable at a time, pre-registered after r77.

PRIOR handoffs (r77 completion, the 20-commit sync, infra sequencing, the Beam
relays, the commitment/learning/valence dev rounds, the desktop/icon items)
were delivered by paste before this channel existed. The durable record starts
here; everything from now goes in this folder.
