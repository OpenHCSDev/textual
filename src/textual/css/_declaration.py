"""Nominal native-property and value-builder contracts, independent of Styles."""

from abc import ABC, abstractmethod
from collections.abc import Callable

from textual.css.tokenizer import Token


class ValueBuilder(ABC):
    @abstractmethod
    def resolve_css(self, name: str, token: Token) -> Callable[[str, list[Token]], None]: ...

    @abstractmethod
    def process_color(self, name: str, tokens: list[Token]) -> None: ...

    @abstractmethod
    def build_edges(self, name: str, tokens: list[Token]) -> None: ...


class NativeProperty:
    name: str

    def build_native(self, builder: ValueBuilder, tokens: list[Token]) -> None:
        raise NotImplementedError(f"Native expressions are not declared for {self.name}")
