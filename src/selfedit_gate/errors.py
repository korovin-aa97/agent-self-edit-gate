"""Stable errors returned by the public CLI and Python API."""

from __future__ import annotations


class GateError(RuntimeError):
    """A deterministic refusal with a stable machine-readable code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
