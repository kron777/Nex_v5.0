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
  2026-11-20_disk-full-investigation.txt   [CURRENT -- read-only, awaiting cc's findings]
    Before the home-drive restore: find what filled the disk on ~2026-11-16 so
    the restore can't refill and get eaten again. READ-ONLY scan (df/du, WAL,
    logs, journald, backups, caches, deleted-but-open files, what's still
    growing, timeline). NO cleanup, NO restore yet -- report findings, then we
    plug the cause, confirm free space, and restore as a separate step.

  2026-11-20_r77-ci-mindmap-fix.txt   [DONE 2026-11-20 -- verified against GitHub]
    Fixed the p12_selfreport mind_map absence-claim drift (ecf9c43); main green;
    PR #44 merged (6e6712b); disarm SHA corrected 7039ced->2803f38 in the docs.
    r77 DISARM IS QUEUED, not applied (flag removed from main's keepalive, no
    restart, instance off since 2026-11-16). Applies at the next clean restart.

OPEN (owner decisions):
  - disk-full root cause -- UNDER INVESTIGATION now (handoff above). Must be
    understood + capped before the restore.
  - home-drive checkout restore -- BLOCKED on the disk-full cause. Separate step,
    after free space is confirmed healthy.

NEXT EXPERIMENT (after infra is stable and Jon directs it):
  r78 -- NEX5_SELF_PRESENT (structured carry / continuity of attention across
  turns), one variable at a time, pre-registered after r77. Falsifier: the carried
  winner must change when the salience vector changes and reach the composed
  prompt; turn_count advancing while winner_kind is frozen = decorative.

PRIOR handoffs (r77 completion, the 20-commit sync, infra sequencing, the Beam
relays, the commitment/learning/valence dev rounds, the desktop/icon items)
were delivered by paste before this channel existed. The durable record starts
here; everything from now goes in this folder.
