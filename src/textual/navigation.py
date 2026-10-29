"""Shared list navigation declarations, consumed through the native keymap."""
from __future__ import annotations

from typing import ClassVar

from textual.binding import Binding, CommandBinding
from textual.document._editing import EditingMode
from textual.dom import DOMNode
from textual.keys import KeyDeclaration


class NavigationCommand(KeyDeclaration["Navigation"]):
    """A list command owns its keys; controls own the operation it requests."""

    keys: ClassVar[tuple[str, ...]] = ()
    _declared: ClassVar[list[type[NavigationCommand]]] = []

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        if "keys" in cls.__dict__:
            NavigationCommand._declared.append(cls)

    @classmethod
    def declarations(cls):
        return (member for member in NavigationCommand._declared
                if issubclass(member, cls))

    @classmethod
    def bindings_for(cls, mode: type[EditingMode]) -> tuple[Binding, ...]:
        return tuple(
            CommandBinding(key=key, action=cls(), description=cls.title,
                           available=cls.available, mode=EditingMode,
                           id=cls.binding_id(mode), show=False, priority=True)
            for key in cls.keys
        )

    @staticmethod
    def available(node: Navigation) -> bool:
        return node.accepts_navigation

    def __call__(self, node: Navigation) -> object:
        return node.apply_navigation(self)

    def apply(self, node: Navigation) -> object:
        raise NotImplementedError


class CursorCommand(NavigationCommand):
    """Move the selected row, not an unrelated scroll container."""


class CursorUp(CursorCommand):
    keys = ("up", "k")

    def apply(self, node):
        return node.action_cursor_up()


class CursorDown(CursorCommand):
    keys = ("down", "j")

    def apply(self, node):
        return node.action_cursor_down()


class ListCommand(NavigationCommand):
    """Navigation through a list's ends and pages."""


class First(ListCommand):
    keys = ("home",)

    def apply(self, node):
        return node.action_first()


class Last(ListCommand):
    keys = ("end",)

    def apply(self, node):
        return node.action_last()


class PageUp(ListCommand):
    keys = ("pageup",)

    def apply(self, node):
        return node.action_page_up()


class PageDown(ListCommand):
    keys = ("pagedown",)

    def apply(self, node):
        return node.action_page_down()


class Navigation(DOMNode):
    """Compose navigation families with the control's other key capabilities."""

    own_navigation: ClassVar[tuple[type[NavigationCommand], ...]] = ()

    def __init_subclass__(cls, navigation: tuple[type[NavigationCommand], ...] = (), **kwargs):
        cls.own_navigation = navigation
        super().__init_subclass__(**kwargs)

    @classmethod
    def present_navigation_binding(cls, declaration, binding):
        return binding

    @classmethod
    def declared_bindings(cls, mode):
        return (
            *super().declared_bindings(mode),
            *(cls.present_navigation_binding(declaration, binding)
              for base in cls.__mro__
              for family in base.__dict__.get("own_navigation", ())
              for declaration in family.declarations()
              for binding in declaration.bindings_for(mode)),
        )

    @property
    def accepts_navigation(self) -> bool:
        return True

    def apply_navigation(self, command: NavigationCommand) -> object:
        return command.apply(self)


class MovesCursor(Navigation, navigation=(CursorCommand,)):
    """Every selectable list shares its up/down/k/j declarations."""

    def action_cursor_up(self) -> None:
        raise NotImplementedError

    def action_cursor_down(self) -> None:
        raise NotImplementedError


class ListNavigation(MovesCursor, navigation=(ListCommand,)):
    """A full list adds end and page operations to the shared cursor keys."""

    def action_first(self) -> None:
        raise NotImplementedError

    def action_last(self) -> None:
        raise NotImplementedError
