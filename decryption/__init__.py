"""
NEX Protocol Decryption Framework
==================================
Systematic probe-and-response analysis for mapping NEX's opcode set.

Modules:
  probe_set          — probe condition definitions and matrix generation
  probe_runner       — executes probes against a live NEX instance
  probes_db          — SQLite schema and I/O for probe results
  differential_analyzer — pairwise divergence analysis
  atlas_builder      — compiles results into condition × opcode matrix
"""
