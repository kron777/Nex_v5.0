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
  2026-11-20_r77-ci-mindmap-fix.txt   [DONE 2026-11-20 -- verified against GitHub]
    Fix the p12_selfreport mind_map absence-claim drift -> green main -> merge
    PR #44 (r77 disarm) -> queue the disarm for the next clean restart.
    OUTCOME: p12_selfreport fixed (ecf9c43; source -> inferred-from-hri_apatrapya;
    NEX5_SHAME / NEX5_SELF_REPORT confirmed genuinely absent). Main green. PR #44
    merged (6e6712b). The rebase changed the disarm SHA 7039ced -> 2803f38 and cc
    corrected the self-references in r77.md / DEPLOY_LEDGER.tsv / CARRY_OVER.md.
    r77 DISARM IS QUEUED, not applied -- flag removed from main's nex_keepalive.sh,
    no restart, instance off since 2026-11-16. Applies at the next clean restart.

OPEN (owner decisions -- not a cc instruction yet, waiting on Jon):
  - home-drive checkout restore (waits on the disk-full root cause being understood)
  - what actually filled the disk beyond nex5's ~800MB

NEXT EXPERIMENT (when infra is stable and Jon directs it):
  r78 -- NEX5_SELF_PRESENT (structured carry / continuity of attention across
  turns), one variable at a time, pre-registered after r77. Falsifier: the carried
  winner must change when the salience vector changes and reach the composed
  prompt; turn_count advancing while winner_kind is frozen = decorative.

PRIOR handoffs (r77 completion, the 20-commit sync, infra sequencing, the Beam
relays, the commitment/learning/valence dev rounds, the desktop/icon items)
were delivered by paste before this channel existed. The durable record starts
here; everything from now goes in this folder.
