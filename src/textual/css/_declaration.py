"""Nominal native-property and value-builder contracts, independent of Styles."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from textual.css.tokenizer import Token


class ValueBuilder(ABC):
    @abstractmethod
    def resolve_css(self, name: str, token: Token) -> Callable[[str, list[Token]], None]: ...



class NativeProperty:
    name: str

    def build_native(self, builder: ValueBuilder, tokens: list[Token]) -> None:
        """A native declaration builds through the same processor its CSS spelling names,
        so every property a stylesheet can set, a widget can declare."""
        builder.resolve_css(self.name, tokens[0])(self.name, tokens)
