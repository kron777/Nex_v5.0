"""Admin — argon2id-backed single-password authentication."""
from .auth import (
    is_configured,
    needs_rehash,
    set_password,
    verify_password,
)

THEORY_X_STAGE = None

__all__ = ["verify_password", "set_password", "is_configured", "needs_rehash"]
