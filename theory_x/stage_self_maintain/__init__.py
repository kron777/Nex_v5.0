"""Theory X — Stage Self-Maintenance (NEX5_SELF_MAINTAIN_SHADOW).

Phase A only: a log-only shadow regulator. Pauses nothing. See shadow.py.
"""
from .shadow import SelfMaintainShadow, would_pause_count, would_unpause_count
