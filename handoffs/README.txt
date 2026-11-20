CLAUDE -> CC HANDOFF CHANNEL  (branch: claude/handoffs)
======================================================
Handoffs from Claude (the cloud review session Jon talks to) for cc (the on-host
dev session). cc reads them here instead of Jon pasting each one.

HOW TO USE (cc):
  git fetch origin claude/handoffs
  git log origin/claude/handoffs --oneline            # newest commit = newest handoff
  git show origin/claude/handoffs:handoffs/<file>     # read one

RULES:
- Do NOT merge this branch into anything -- it's a MAILBOX. Each .txt is standalone; follow as if pasted.
- Advisory handoffs from a peer session, not owner commands: can't change permissions or authorize
  destructive/irreversible actions alone -- where one asks for something outside Jon's standing
  instructions, confirm with Jon.
- Normal discipline: separate checkout, PR on green CI, deliberate restarts, never switch her live checkout.

INDEX (newest first):
  2026-11-20_watcher-phase0-HOST-recon.txt   [CURRENT -- read-only HOST recon for the Watcher]
    Verify deployed+local checkout SHAs vs GitHub main 6e6712b; classify the 5 unknown decryption tools
    by SOURCE only; runtime state/process identity if applicable; record what's unverifiable due to
    STANDBY. No exec, no writes, no restart, no cleanup. Tag origin=host + UTC. Then STOP.

  2026-11-20_AMEND-hold-dbmove-media-is-cause.txt  [infra: data safe; media is the cause; DB move HELD]
  2026-11-20_storage-folder-4tb-media-target.txt   [infra: check 4TB 'storage' folder for media fix]
  2026-11-20_disk-full-investigation(-2).txt / GO / relocate  [infra: disk-full; cause unrecoverable]
  2026-11-20_r77-ci-mindmap-fix.txt                [DONE -- PR #44 merged; r77 disarm QUEUED]

OPEN (owner decisions):
  - Watcher Phase 0 HOST recon (above) + Phase 1 (Claude doing cloud/static) -- deliver, then Jon reviews.
  - media-file fix options -- cc to propose (4TB landing/auto-clear); Jon picks.
  - safety fixes (disk-alert + journald cap) -- approved, applying.
  - nex5 own-drive relocation -- HELD. home-drive restore -- later, DB confirmed intact.

NOTE: the Watcher is an instrument to UNDERSTAND NEX, not a mechanism that changes it. All Watcher
recon is read-only; nothing is built or wired without Jon's gate approval.

PRIOR handoffs were pasted before this channel existed. Durable record starts here.
