"""Native property declarations use the existing value grammar without selectors."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from functools import partial
from typing import ClassVar

from textual.css._declaration import NativeProperty, ValueBuilder
from textual.css._style_properties import StyleProperty
from textual.css.model import Declaration
from textual.css.styles import Styles
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
    prefix: ClassVar[str] = ""

    def text(self) -> str:
        return f"${self.prefix}{self.name}"


@dataclass(frozen=True)
class TextVariable(Variable):
    """The design system's text expression for a named semantic colour."""

    prefix = "text-"


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


@dataclass
class NativeDeclaration(Declaration):
    """The property descriptor owns native dispatch; callers supply its values."""

    owner: NativeProperty = field(kw_only=True)

    @property
    def rule_name(self) -> str:
        return self.owner.name

    def defined(self) -> bool:
        return True

    def bind(self, builder: ValueBuilder) -> Callable[[list[Token]], None]:
        return partial(self.owner.build_native, builder)

    @classmethod
    def of[Value](
        cls, property: StyleProperty[Value], *values: NativeValue
    ) -> "NativeDeclaration":
        name = property.name.replace("_", "-")
        return cls(
            Token("declaration_name", name, ("<native>", name), name, (0, 0)),
            name,
            [value.token() for value in values],
            owner=property,
        )


class NativeStyleResolver(ABC):
    @abstractmethod
    def native_styles(self, *declarations: NativeDeclaration) -> Styles: ...
