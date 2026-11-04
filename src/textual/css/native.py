"""Native property declarations use the existing value grammar without selectors."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from functools import cache, partial
from typing import ClassVar, Protocol, Self, overload

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
class Number(NativeValue):
    """A plain number, such as one cell of spacing or a fractional opacity."""

    value: float
    token_name = "number"

    def text(self) -> str:
        return f"{self.value:g}"


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


class Component(Enum):
    """A widget's styled parts. Members are the parts; each part's CSS component
    class name is derived here, once, from the declaring widget's prefix."""

    def __init_subclass__(cls, *, prefix: str = "", **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if prefix:
            cls._prefix = prefix
        Component.named.cache_clear()

    @property
    def css_name(self) -> str:
        return f"{type(self)._prefix}--{self.name.lower().replace('_', '-')}"

    @staticmethod
    @cache
    def named(css_name: str) -> "Component | None":
        """The declared part a stylesheet component class names, if any."""
        pending: list[type[Component]] = [Component]
        while pending:
            parts = pending.pop()
            pending.extend(parts.__subclasses__())
            for part in parts:
                if part.css_name == css_name:
                    return part
        return None


class DeclaresTheme:
    """Owns native theme declarations: each class declares its own, the MRO composes them."""

    native_theme: ClassVar[tuple[NativeDeclaration, ...]] = ()

    @classmethod
    @cache
    def declared_theme(cls) -> tuple[NativeDeclaration, ...]:
        """Every class's own declarations, base first, so the most derived wins."""
        return tuple(
            declaration
            for owner in reversed(cls.__mro__)
            for declaration in vars(owner).get("native_theme", ())
        )


class ThemedNode(Protocol):
    """What a theme state needs from the node holding it."""

    _theme_looks: dict["ThemeState", type[DeclaresTheme]]

    def update_node_styles(self, animate: bool = True) -> None: ...


class ThemeState[Look: DeclaresTheme]:
    """A node's look: the family member its state selects. Assigning it restyles the node."""

    def __init__(self, default: type[Look]) -> None:
        self.default = default

    @overload
    def __get__(self, node: None, owner: type) -> Self: ...

    @overload
    def __get__(self, node: ThemedNode, owner: type) -> type[Look]: ...

    def __get__(self, node: ThemedNode | None, owner: type) -> "type[Look] | Self":
        if node is None:
            return self
        return node._theme_looks.get(self, self.default)

    def __set__(self, node: ThemedNode, look: type[Look]) -> None:
        if node._theme_looks.get(self, self.default) is not look:
            node._theme_looks[self] = look
            node.update_node_styles()


class NativeStyleResolver(ABC):
    @abstractmethod
    def native_styles(self, *declarations: NativeDeclaration) -> Styles: ...
