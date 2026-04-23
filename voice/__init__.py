"""Voice — register-aware LLM client for Qwen2.5-3B via llama-server."""
from .registers import (
    ANALYTICAL,
    CONVERSATIONAL,
    PHILOSOPHICAL,
    REGISTERS,
    TECHNICAL,
    Register,
    by_name,
    classify,
    default_register,
)

THEORY_X_STAGE = None

__all__ = [
    "Register",
    "REGISTERS",
    "ANALYTICAL",
    "CONVERSATIONAL",
    "PHILOSOPHICAL",
    "TECHNICAL",
    "default_register",
    "classify",
    "by_name",
]
