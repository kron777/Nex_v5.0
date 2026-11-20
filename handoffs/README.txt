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
  2026-11-20_r77-ci-mindmap-fix.txt
    main CI is RED on the p12_selfreport mind_map absence-claim drift
    (hri/apatrapya code now exists but the map still claims it absent). Fix the
    MAP, not the code -> green main -> rebase & merge PR #44 (r77 disarm) ->
    queue the disarm for the next CLEAN restart (after the disk-full cause is
    understood). The r77 verdict itself is verified correct (Branch C).

PRIOR handoffs (r77 completion, the 20-commit sync, infra sequencing, the Beam
relays, the commitment/learning/valence dev rounds, the desktop/icon items)
were delivered by paste before this channel existed. The durable record starts
here; everything from now goes in this folder.
