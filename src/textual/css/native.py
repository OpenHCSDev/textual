"""Native property declarations use the existing value grammar without selectors."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar

from textual.css._style_properties import StyleProperty
from textual.css.model import Declaration
from textual.css.tokenizer import Token


class NativeValue(ABC):
    """One value in a native declaration; its class owns its lexical form."""

    token_name: ClassVar[str]

    @abstractmethod
    def text(self) -> str: ...

    def token(self) -> Token:
        text = self.text()
        return Token(self.token_name, text, ("<native>", ""), text, (0, 0))


@dataclass(frozen=True)
class Variable(NativeValue):
    """A reference into the stylesheet's existing theme-variable namespace."""

    name: str
    token_name = "variable_ref"

    def text(self) -> str:
        return f"${self.name}"


@dataclass(frozen=True)
class Keyword(NativeValue):
    """A keyword consumed and validated by the property's existing value builder."""

    value: str
    token_name = "token"

    def text(self) -> str:
        return self.value


@dataclass(frozen=True)
class Percent(NativeValue):
    """A percentage retains the native property's own alpha interpretation."""

    value: float
    token_name = "scalar"

    def text(self) -> str:
        return f"{self.value:g}%"


class NativeDeclaration(Declaration):
    """The property descriptor supplies its name; callers supply only its values."""

    @classmethod
    def of[Value](
        cls, property: StyleProperty[Value], *values: NativeValue
    ) -> "NativeDeclaration":
        name = property.name.replace("_", "-")
        return cls(
            Token("declaration_name", name, ("<native>", name), name, (0, 0)),
            name,
            [value.token() for value in values],
        )
