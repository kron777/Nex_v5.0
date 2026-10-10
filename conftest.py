# Root pytest collection config.
#
# recursion_teeth_test.py is a diagnostic CLI (argparse + __main__ entry) that
# reads the LIVE dynamic.db to answer an experimental question ("does the
# self-reading move the self?"). Its module-level `test()` is an analysis
# routine, not a unit test, and it errors on the empty temp DB the suite runs
# under. Exclude it from collection so it stays a hand-run diagnostic.
#
# (The live-data guard and fixtures live in tests/conftest.py; this root
# conftest only governs what pytest collects.)
collect_ignore = [
    "theory_x/stage_tom/recursion_teeth_test.py",
]
