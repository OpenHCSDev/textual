"""How a click hint shows its stable assigned key."""
from abc import ABC, abstractmethod


class HintLabelStyle(ABC):
    """Presentation never changes the key or its original activation."""

    @classmethod
    @abstractmethod
    def caption(cls, key: str, prefix: str) -> str: ...


class NextLetterHints(HintLabelStyle):
    """Show the next untyped letter at the target."""

    @classmethod
    def caption(cls, key: str, prefix: str) -> str:
        return key[len(prefix):len(prefix) + 1]


class FullKeyHints(HintLabelStyle):
    """Show the complete assigned sequence, including the typed prefix."""

    @classmethod
    def caption(cls, key: str, prefix: str) -> str:
        return key
