"""The application's local clipboard payload."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ClipboardContent:
    text: str

    @classmethod
    def of(cls, value: str | ClipboardContent) -> ClipboardContent:
        return value if isinstance(value, ClipboardContent) else cls(value)
