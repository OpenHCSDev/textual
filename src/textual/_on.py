from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from functools import update_wrapper
from typing import TYPE_CHECKING, Callable, Protocol, TypeVar, cast

from textual.css.match import match
from textual.css.model import SelectorSet
from textual.css.parse import parse_selectors
from textual.css.tokenizer import TokenError
from textual.message import Message

if TYPE_CHECKING:
    from textual.message_pump import MessagePump

DecoratedType = TypeVar("DecoratedType")


class OnDecoratorError(Exception):
    """Errors related to the `on` decorator.

    Typically raised at import time as an early warning system.
    """


class OnNoWidget(Exception):
    """A selector was applied to an attribute that isn't a widget."""


@dataclass(frozen=True, slots=True)
class MessageDeclaration:
    """One unfiltered message-type declaration on a handler."""

    message_type: type[Message]

    def matches(self, message: Message) -> bool:
        return True


@dataclass(frozen=True, slots=True)
class SelectorDeclaration(MessageDeclaration):
    """A declaration whose widget predicates remain live at delivery."""

    selectors: Mapping[str, tuple[SelectorSet, ...]]

    def matches(self, message: Message) -> bool:
        if not message._sender:
            return False
        # Only selector matching acquires the widget boundary.
        from textual.widget import Widget

        for attribute, selector in self.selectors.items():
            node = getattr(message, attribute)
            if node is None:
                return False
            if not isinstance(node, Widget):
                raise OnNoWidget(
                    f"on decorator can't match against {attribute!r} as it is not a widget."
                )
            if not match(selector, node):
                return False
        return True


class MessageHandler:
    """A method's declared message routes; binding remains the method's work."""

    def __init__(self, method: Callable) -> None:
        self.method = method
        self.declarations: list[MessageDeclaration] = []
        update_wrapper(self, method)

    def __get__(self, instance, owner=None):
        return self.method.__get__(instance, owner)

    def __call__(self, *args, **kwargs):
        return self.method(*args, **kwargs)


@dataclass(frozen=True, slots=True)
class MessageRoute:
    """A declaring scope's reference to a method and one of its declarations."""

    handler: MessageHandler
    declaration: MessageDeclaration

    def method_for(self, receiver: MessagePump, owner: type) -> Callable[..., object]:
        return cast(Callable[..., object], self.handler.__get__(receiver, owner))

    def bound_for(self, receiver: MessagePump, owner: type) -> BoundMessageRoute:
        return BoundMessageRoute(
            self.handler, self.declaration, self.method_for(receiver, owner)
        )


@dataclass(frozen=True, slots=True)
class BoundMessageRoute(MessageRoute):
    """A receiver-owned binding; declaration predicates are not cached."""

    bound_method: Callable[..., object]

    def method_for(self, receiver: MessagePump, owner: type) -> Callable[..., object]:
        return self.bound_method


class MethodDescriptor(Protocol):
    """Python's descriptor boundary for a conventional class-dictionary entry."""

    def __get__(self, instance: object, owner: type) -> Callable[..., object]: ...


@dataclass(frozen=True)
class DispatchScope:
    """One C3 declaring scope and the defaults for absent capabilities."""

    owner: type

    def routes_for(self, message_type: type[Message]) -> Iterable[MessageRoute]:
        return ()

    def conventional_methods(
        self, receiver: MessagePump, message: Message
    ) -> Iterable[Callable[..., object]]:
        return ()

    def bound_for(self, receiver: MessagePump, message_type: type[Message]) -> BoundScope:
        return BoundScope(
            self.owner,
            tuple(route.bound_for(receiver, self.owner)
                  for route in self.routes_for(message_type)),
        )


@dataclass(frozen=True)
class NamedScope(DispatchScope):
    """The live Python namespace still used by unmigrated messages."""

    named: Mapping[str, object]

    @classmethod
    def from_class(cls, owner: type) -> DispatchScope:
        namespace = owner.__dict__
        declarations: dict[type[Message], list[MessageRoute]] = {}
        # A Python class dictionary is foreign until decoded here. The
        # resulting scopes carry their capabilities, not another kind flag.
        for value in namespace.values():
            if isinstance(value, MessageHandler):
                for declaration in value.declarations:
                    declarations.setdefault(declaration.message_type, []).append(
                        MessageRoute(value, declaration)
                    )
        if declarations:
            return ClassScope(
                owner=owner, named=namespace,
                declarations={key: tuple(routes) for key, routes in declarations.items()},
            )
        return cls(owner=owner, named=namespace)

    def conventional_methods(
        self, receiver: MessagePump, message: Message
    ) -> Iterable[Callable[..., object]]:
        conventional = self.named.get('_' + message.handler_name) or self.named.get(message.handler_name)
        # Keep private-name precedence and the live dictionary. A decorated
        # private entry masks the public conventional entry, too.
        if conventional is not None and not isinstance(conventional, MessageHandler):
            yield cast(MethodDescriptor, conventional).__get__(receiver, self.owner)


@dataclass(frozen=True)
class DeclaredRoutes(DispatchScope):
    """Message-type lookup shared by class scopes with declared handlers."""

    declarations: Mapping[type[Message], tuple[MessageRoute, ...]]

    def routes_for(self, message_type: type[Message]) -> Iterable[MessageRoute]:
        for ancestor in message_type._dispatch_types:
            yield from self.declarations.get(ancestor, ())


@dataclass(frozen=True)
class ClassScope(DeclaredRoutes, NamedScope):
    """Compose declared routes and a live conventional namespace by C3."""


@dataclass(frozen=True)
class BoundScope(DispatchScope):
    """A declared-only candidate sequence bound to one receiving pump."""

    routes: tuple[MessageRoute, ...]

    def routes_for(self, message_type: type[Message]) -> Iterable[MessageRoute]:
        return self.routes


def on(
    message_type: type[Message], selector: str | None = None, **kwargs: str
) -> Callable[[DecoratedType], DecoratedType]:
    """Decorator to declare that the method is a message handler.

    The decorator accepts an optional CSS selector that will be matched against a widget exposed by
    a `control` property on the message.

    Example:
        ```python
        # Handle the press of buttons with ID "#quit".
        @on(Button.Pressed, "#quit")
        def quit_button(self) -> None:
            self.app.quit()
        ```

    Keyword arguments can be used to match additional selectors for attributes
    listed in [`ALLOW_SELECTOR_MATCH`][textual.message.Message.ALLOW_SELECTOR_MATCH].

    Example:
        ```python
        # Handle the activation of the tab "#home" within the `TabbedContent` "#tabs".
        @on(TabbedContent.TabActivated, "#tabs", pane="#home")
        def switch_to_home(self) -> None:
            self.log("Switching back to the home tab.")
            ...
        ```

    Args:
        message_type: The message type (i.e. the class).
        selector: An optional [selector](/guide/CSS#selectors). If supplied, the handler will only be called if `selector`
            matches the widget from the `control` attribute of the message.
        **kwargs: Additional selectors for other attributes of the message.
    """

    selectors: dict[str, str] = {}
    if selector is not None:
        selectors["control"] = selector
    if kwargs:
        selectors.update(kwargs)

    parsed_selectors: dict[str, tuple[SelectorSet, ...]] = {}
    for attribute, css_selector in selectors.items():
        if attribute == "control":
            if message_type.control == Message.control:
                raise OnDecoratorError(
                    "The message class must have a 'control' to match with the on decorator"
                )
        elif attribute not in message_type.ALLOW_SELECTOR_MATCH:
            raise OnDecoratorError(
                f"The attribute {attribute!r} can't be matched; have you added it to "
                + f"{message_type.__name__}.ALLOW_SELECTOR_MATCH?"
            )
        try:
            parsed_selectors[attribute] = parse_selectors(css_selector)
        except TokenError:
            raise OnDecoratorError(
                f"Unable to parse selector {css_selector!r} for {attribute}; check for syntax errors"
            ) from None

    def decorator(method: DecoratedType) -> DecoratedType:
        """Compose routes on their declaration, not optional function attributes."""
        handler = method if isinstance(method, MessageHandler) else MessageHandler(cast(Callable, method))
        declaration = (
            SelectorDeclaration(message_type, parsed_selectors)
            if parsed_selectors else MessageDeclaration(message_type)
        )
        handler.declarations.append(declaration)
        return cast(DecoratedType, handler)

    return decorator
