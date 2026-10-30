"""

This module contains the `Binding` class and related objects.

See [bindings](/guide/input#bindings) in the guide for details.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass, field
from inspect import iscoroutinefunction
from types import FunctionType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Self,
    TypeVar,
    overload,
)

import rich.repr

from textual._callback import invoke, invoke_sync
from textual.actions import SkipAction
from textual.keys import DeclaredKey, KeyDeclaration, KeyInvocation, UndecodedKey, _character_to_key

if TYPE_CHECKING:
    from textual.document._editing import EditingMode
    from typing_extensions import TypeAlias

    from textual.app import App
    from textual.dom import DOMNode
    from textual.events import Key
    from textual.widget import Widget
    from textual.widgets import TextArea

BindingType: TypeAlias = "Binding | tuple[str, str] | tuple[str, str, str]"
"""The possible types of a binding found in the `BINDINGS` class variable."""

BindingIDString: TypeAlias = str
"""The ID of a Binding defined somewhere in the application.

Corresponds to the `id` parameter of the `Binding` class.
"""

KeyString: TypeAlias = str
"""A string that represents a key binding.

For example, "x", "ctrl+i", "ctrl+shift+a", "ctrl+j,space,x", etc.
"""

Keymap = Mapping[BindingIDString, KeyString]
"""A mapping of binding IDs to key strings, used for overriding default key bindings."""


class BindingError(Exception):
    """A binding related error."""


class NoBinding(Exception):
    """A binding was not found."""


class InvalidBinding(Exception):
    """Binding key is in an invalid format."""


@dataclass(frozen=True)
class Binding:
    """The configuration of a key binding."""

    key: str
    """Key to bind. This can also be a comma-separated list of keys to map multiple keys to a single action."""
    action: str
    """Action to bind to."""
    description: str = ""
    """Description of action."""
    show: bool = True
    """Show the action in Footer, or False to hide."""
    key_display: str | None = None
    """How the key should be shown in footer.

    If `None`, the display of the key will use the result of `App.get_key_display`.

    If overridden in a keymap then this value is ignored.
    """
    priority: bool = False
    """Enable priority binding for this key."""
    tooltip: str = ""
    """Optional tooltip to show in footer."""

    id: str | None = None
    """ID of the binding. Intended to be globally unique, but uniqueness is not enforced.

    If specified in the App's keymap then Textual will use this ID to lookup the binding,
    and substitute the `key` property of the Binding with the key specified in the keymap.
    """
    system: bool = False
    """Make this binding a system binding, which removes it from the key panel."""

    @dataclass(frozen=True)
    class Group:
        """A binding group causes the keys to be grouped under a single description."""

        description: str = ""
        """Description of the group."""

        compact: bool = False
        """Show keys in compact form (no spaces)."""

    group: Group | None = None
    """Optional binding group (used to group related bindings in the footer)."""

    declared_key: DeclaredKey = field(default=UndecodedKey(), kw_only=True, repr=False)
    """The original native key identity; remapping changes key, never this fact."""

    def command_invocations(self) -> tuple[KeyInvocation, ...]:
        """Named external actions expose no nominal command."""
        return ()

    def invocations(self) -> tuple[KeyInvocation, ...]:
        return self.declared_key.invocations(self.command_invocations())

    def for_mode(self, mode: type[EditingMode]) -> tuple[Self, ...]:
        """Give native arrows their shared preference identity in the actual mode."""
        identity = next((invocation.binding_identity(mode) for invocation in self.invocations()), self.id)
        return (dataclasses.replace(self, id=identity),)

    def parse_key(self) -> tuple[list[str], str]:
        """Parse a key into a list of modifiers, and the actual key.

        Returns:
            A tuple of (MODIFIER LIST, KEY).
        """
        *modifiers, key = self.key.split("+")
        return modifiers, key

    def with_key(self, key: str, key_display: str | None = None) -> Binding:
        """Return a new binding with the key and key_display set to the specified values.

        Args:
            key: The new key to set.
            key_display: The new key display to set.

        Returns:
            A new binding with the key set to the specified value.
        """
        return dataclasses.replace(self, key=key, key_display=key_display)

    def state(self, app: App[Any], node: DOMNode) -> bool | None:
        """Whether the key works now for the node that declares this binding.

        Returns:
            `True` if it works, `None` if it is shown but disabled, `False` if it
            is neither shown nor run.
        """
        return app._check_action_state(self.action, node)

    async def run(self, app: App[Any], node: DOMNode) -> bool:
        """Do what the key is bound to, for the node that declares this binding.

        Returns:
            `True` if the key was handled.
        """
        return await app.run_action(self.action, node)

    def edit(self, node: DOMNode, event: Key) -> bool:
        """Ordinary bindings run through application dispatch, after text handling."""
        return False

    async def run_before_text(self, app: App[object], node: DOMNode, event: Key, target: Widget) -> bool:
        """A configured arrow alias keeps its native action, before type-to-search."""
        return await self.run(app, node)

    def fallback_bindings(self) -> tuple[Binding, ...]:
        """Ordinary keys stay on the focused native ancestor chain."""
        return ()

    def engine_boundary(self, editor: TextArea) -> bool:
        """Native declarations may offer an application edge to an external editor."""
        return False

    @classmethod
    def make_bindings(cls, bindings: Iterable[BindingType]) -> Iterable[Binding]:
        """Convert a list of BindingType (the types that can be specified in BINDINGS)
        into an Iterable[Binding].

        Compound bindings like "j,down" will be expanded into 2 Binding instances.

        Args:
            bindings: An iterable of BindingType.

        Returns:
            An iterable of Binding.
        """
        bindings = list(bindings)
        for binding in bindings:
            # If it's a tuple of length 3, convert into a Binding first
            if isinstance(binding, tuple):
                if len(binding) not in (2, 3):
                    raise BindingError(
                        f"BINDINGS must contain a tuple of two or three strings, not {binding!r}"
                    )
                # `binding` is a tuple of 2 or 3 values at this point
                binding = Binding(*binding)  # type: ignore[reportArgumentType]

            # At this point we have a Binding instance, but the key may
            # be a list of keys, so now we unroll that single Binding
            # into a (potential) collection of Binding instances.
            for key in binding.key.split(","):
                key = key.strip()
                if not key:
                    raise InvalidBinding(
                        f"Can not bind empty string in {binding.key!r}"
                    )
                if len(key) == 1:
                    key = _character_to_key(key)

                yield dataclasses.replace(
                    binding,
                    key=key,
                    declared_key=binding.declared_key.decoded(key),
                    show=bool(binding.description and binding.show),
                )


def _always(node: Any) -> bool:
    return True


@dataclass(frozen=True)
class CallBinding(Binding):
    """A key bound to a function of the node that declares it.

    The function is given the node, so a class binds its own method by
    referring to it in the class body:

        class Editor(Screen):
            def save(self) -> None: ...
            BINDINGS = [CallBinding("ctrl+s", save, "Save")]
    """

    action: Callable[[Any], object]  # type: ignore[assignment]
    """Called with the declaring node when the key is pressed.

    Invocation awaits an awaitable result and ignores a synchronous result,
    including the Worker returned by a method decorated with ``@work``.
    """
    available: Callable[[Any], bool | None] = _always
    """Called with the declaring node: `True` if the key works now, `None` to
    show it disabled, `False` to neither show nor run it."""

    def state(self, app: App[Any], node: DOMNode) -> bool | None:
        return self.available(node)

    def call(self, node: DOMNode) -> object:
        return invoke_sync(self.action, node)

    async def run(self, app: App[Any], node: DOMNode) -> bool:
        if not self.state(app, node):
            return False
        try:
            await invoke(self.call, node)
        except SkipAction:
            return False
        return True


@dataclass(frozen=True, kw_only=True)
class ModeBinding(CallBinding, KeyInvocation):
    """A native callable whose key belongs to a nominal editing capability.

    The declaring class keeps the method and its key together. Applications
    choose which native declarations they expose through their own projection.
    """

    mode: type[EditingMode]

    @property
    def invocation(self) -> KeyInvocation:
        return self

    def command_invocations(self) -> tuple[KeyInvocation, ...]:
        return (self.invocation,)

    def key_identity(self) -> str:
        return self.qualified(self.action)

    def key_title(self) -> str:
        return self.description

    def key_summary(self) -> str:
        return self.tooltip

    def key_system(self) -> bool:
        return self.system

    def for_mode(self, mode: type[EditingMode]) -> tuple[ModeBinding, ...]:
        """Expose a native callable only in its declared capability's active modes."""
        if self.mode not in mode.__mro__:
            return ()
        return super().for_mode(mode)

    def state(self, app: App[object], node: DOMNode) -> bool | None:
        if self.mode not in node.key_mode.__mro__:
            return False
        return super().state(app, node)

    def fallback_bindings(self) -> tuple[Binding, ...]:
        return self.mode.fallback_bindings(self)


@dataclass(frozen=True, kw_only=True)
class MethodBinding(ModeBinding):
    """A native method declares its own keys, with normal Python override dispatch.

    The descriptor retains the original callable for stable invocation identity;
    its name is derived only to bind the actual overriding method on the node.
    No second action-name spelling or implementation lives in a menu.
    """

    action: FunctionType
    selecting: tuple[str, ...] = ()

    @classmethod
    def declare(
        cls, *keys: str, selecting: tuple[str, ...] = (), description: str = "",
        priority: bool = False, available: Callable[[DOMNode], bool | None] = _always,
        show: bool = False,
    ) -> Callable[[Callable[..., object]], MethodBinding]:
        from textual.document._editing import EditingMode

        def declared(method: Callable[..., object]) -> MethodBinding:
            if not isinstance(method, FunctionType):
                raise TypeError("Native method declarations require a Python function")
            if iscoroutinefunction(method):
                raise TypeError("Pre-text editor methods must be synchronous")
            return cls(key=",".join(keys), action=method, mode=EditingMode,
                       description=description or method.__name__.removeprefix("action_").replace("_", " ").capitalize(),
                       tooltip=method.__doc__ or "", show=show, selecting=selecting,
                       priority=priority, available=available)
        return declared

    @overload
    def __get__(self, instance: None, owner: type) -> FunctionType: ...

    @overload
    def __get__(self, instance: object, owner: type) -> Callable[..., object]: ...

    def __get__(self, instance: object, owner: type) -> Callable[..., object]:
        return self.action.__get__(instance, owner)

    def __set_name__(self, owner: type[DOMNode], name: str) -> None:
        owner._declared_key_bindings = (
            *owner.__dict__.get("_declared_key_bindings", ()), self,
            *(SelectingMethodBinding(key=key, action=self.action, mode=self.mode,
                                     description=f"{self.description} select",
                                     tooltip=self.tooltip, show=self.show)
              for key in self.selecting),
        )

    def arguments(self) -> tuple[object, ...]:
        return ()

    def engine_boundary(self, editor: TextArea) -> bool:
        return editor.before_engine_input(self.action)

    def call(self, node: DOMNode) -> object:
        return invoke_sync(getattr(node, self.action.__name__), *self.arguments())

    def state(self, app: App[object], node: DOMNode) -> bool | None:
        if not super().state(app, node):
            return False
        return node.check_action(self.action.__name__.removeprefix("action_"), self.arguments())

    async def run_before_text(self, app: App[object], node: DOMNode, event: Key, target: Widget) -> bool:
        """The native editor, not an earlier dispatch phase, owns this actual Key.

        Forward it once along the ordinary path so pending operators, native
        arity, selection and history see precisely the same original mode.
        """
        target._forward_event(event)
        return True

    def edit(self, node: DOMNode, event: Key) -> bool:
        # Only explicit focused overrides take printable input. Native non-text
        # keys use this same call while the original prefix still owns its state.
        if event.is_printable and self.id not in node.app._keymap:
            return False
        if not self.state(node.app, node):
            return False
        try:
            return node.apply_editor_binding(self, event)
        except SkipAction:
            return False


class SelectingMethodBinding(MethodBinding):
    """The same native method with its real selection argument, not a Vim motion."""

    def arguments(self) -> tuple[object, ...]:
        return (True,)

    def key_identity(self) -> str:
        return f"{super().key_identity()}:{self.qualified(type(self))}"


NodeT = TypeVar("NodeT", bound="DOMNode", contravariant=True)


@dataclass(frozen=True, kw_only=True)
class CommandBinding(ModeBinding, Generic[NodeT]):
    """The callable is the command itself, including its invocation identity."""

    action: KeyDeclaration[NodeT]

    @property
    def invocation(self) -> KeyInvocation:
        return self.action


class ActiveBinding(NamedTuple):
    """Information about an active binding (returned from [active_bindings][textual.screen.Screen.active_bindings])."""

    node: DOMNode
    """The node where the binding is defined."""
    binding: Binding
    """The binding information."""
    enabled: bool
    """Is the binding enabled? (enabled bindings are typically rendered dim)"""
    tooltip: str = ""
    """Optional tooltip shown in Footer."""


@dataclass(frozen=True)
class KeymapClaim:
    """A detached default claim, with its original nominal invocation intact."""

    invocation: KeyInvocation
    keys: tuple[str, ...]

    @classmethod
    def from_bindings(cls, bindings: Iterable[Binding]) -> Iterator[KeymapClaim]:
        return (cls(invocation, (key,)) for key, binding in BindingsMap(bindings)
                for invocation in binding.invocations())


@rich.repr.auto
class BindingsMap:
    """Manage a set of bindings."""

    def __init__(
        self,
        bindings: Iterable[BindingType] | None = None,
    ) -> None:
        """Initialise a collection of bindings.

        Args:
            bindings: An optional set of initial bindings.

        Note:
            The iterable of bindings can contain either a `Binding`
            instance, or a tuple of 3 values mapping to the first three
            properties of a `Binding`.
        """

        self.key_to_bindings: dict[str, list[Binding]] = {}
        """Mapping of key (e.g. "ctrl+a") to list of bindings for that key."""

        for binding in Binding.make_bindings(bindings or {}):
            self.key_to_bindings.setdefault(binding.key, []).append(binding)

    def _add_binding(self, binding: Binding) -> None:
        """Add a new binding.

        Args:
            binding: New Binding to add.
        """
        self.key_to_bindings.setdefault(binding.key, []).append(binding)

    def __iter__(self) -> Iterator[tuple[str, Binding]]:
        """Iterating produces a sequence of (KEY, BINDING) tuples."""
        return iter(
            [
                (key, binding)
                for key, bindings in self.key_to_bindings.items()
                for binding in bindings
            ]
        )

    @classmethod
    def from_keys(cls, keys: dict[str, list[Binding]]) -> BindingsMap:
        """Construct a BindingsMap from a dict of keys and bindings.

        Args:
            keys: A dict that maps a key on to a list of `Binding` objects.

        Returns:
            New `BindingsMap`
        """
        bindings = cls()
        bindings.key_to_bindings = keys
        return bindings

    def copy(self) -> BindingsMap:
        """Return a copy of this instance.

        Return:
            New bindings object.
        """
        copy = BindingsMap()
        copy.key_to_bindings = self.key_to_bindings.copy()
        return copy

    def __rich_repr__(self) -> rich.repr.Result:
        yield self.key_to_bindings

    @classmethod
    def merge(cls, bindings: Iterable[BindingsMap]) -> BindingsMap:
        """Merge a bindings.

        Args:
            bindings: A number of bindings.

        Returns:
            New `BindingsMap`.
        """
        keys: dict[str, list[Binding]] = {}
        for _bindings in bindings:
            for key, key_bindings in _bindings.key_to_bindings.items():
                keys.setdefault(key, []).extend(key_bindings)
        return BindingsMap.from_keys(keys)

    def project(self, mode: type[EditingMode], declarations: Iterable[BindingType] = ()) -> BindingsMap:
        """Raw and nominal declarations use the same native mode projection."""
        return BindingsMap(
            projected
            for binding in (*[binding for _, binding in self], *Binding.make_bindings(declarations))
            for projected in binding.for_mode(mode)
        )

    def apply_keymap(self, keymap: Keymap) -> KeymapApplyResult:
        """Overlay preferences without losing native alternatives or expanding aliases twice.

        Different controls may share an arrow preference, not its implementation.
        Within one scope, keep every distinct native binding in its original order;
        only identical aliases of the same binding collapse.
        """
        defaults: dict[str, list[Binding]] = {}
        remapped: dict[str, list[Binding]] = {}
        clashed_bindings: set[Binding] = set()
        for key, binding in self:
            binding_id = binding.id
            if binding_id is None or binding_id not in keymap:
                defaults.setdefault(key, []).append(binding)
                continue
            for configured_key in keymap[binding_id].split(","):
                if not configured_key:
                    continue
                projected = binding.with_key(configured_key, key_display=None)
                alternatives = remapped.setdefault(configured_key, [])
                if projected not in alternatives:
                    alternatives.append(projected)
        for key, alternatives in remapped.items():
            clashed_bindings.update(defaults.pop(key, ()))
            defaults[key] = alternatives
        self.key_to_bindings = defaults
        return KeymapApplyResult(clashed_bindings)

    @property
    def shown_keys(self) -> list[Binding]:
        """A list of bindings for shown keys."""
        keys = [
            binding
            for bindings in self.key_to_bindings.values()
            for binding in bindings
            if binding.show
        ]
        return keys

    def bind(
        self,
        keys: str,
        action: str,
        description: str = "",
        show: bool = True,
        key_display: str | None = None,
        priority: bool = False,
    ) -> None:
        """Bind keys to an action.

        Args:
            keys: The keys to bind. Can be a comma-separated list of keys.
            action: The action to bind the keys to.
            description: An optional description for the binding.
            show: A flag to say if the binding should appear in the footer.
            key_display: Optional string to display in the footer for the key.
            priority: Is this a priority binding, checked form app down to focused widget?
        """
        all_keys = [key.strip() for key in keys.split(",")]
        for key in all_keys:
            self.key_to_bindings.setdefault(key, []).append(
                Binding(
                    key,
                    action,
                    description,
                    show=bool(description and show),
                    key_display=key_display,
                    priority=priority,
                )
            )

    def get_bindings_for_key(self, key: str) -> list[Binding]:
        """Get a list of bindings for a given key.

        Args:
            key: Key to look up.

        Raises:
            NoBinding: If the binding does not exist.

        Returns:
            A list of bindings associated with the key.
        """
        try:
            return self.key_to_bindings[key]
        except KeyError:
            raise NoBinding(f"No binding for {key}") from None


class KeymapApplyResult(NamedTuple):
    """The result of applying a keymap."""

    clashed_bindings: set[Binding]
    """A list of bindings that were clashed and replaced by the keymap."""
