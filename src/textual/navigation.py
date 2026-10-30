"""Shared list navigation declarations, consumed through the native keymap."""
from __future__ import annotations

from abc import abstractmethod
from typing import ClassVar

from textual.binding import Binding, CommandBinding
from textual.document._editing import EditingMode
from textual.dom import DOMNode
from textual.keys import DeclaredKey, DownKey, KeyDeclaration, LeftKey, RightKey, UndecodedKey, UpKey


class NavigationCommand(KeyDeclaration["Navigation"]):
    """A list command owns its keys; controls own the operation it requests."""

    keys: ClassVar[tuple[str, ...]] = ()
    priority: ClassVar[bool] = False
    declared_key: ClassVar[DeclaredKey] = UndecodedKey()

    @classmethod
    def bindings_for(cls, mode: type[EditingMode]) -> tuple[Binding, ...]:
        if not cls.keys:
            return ()
        command = cls()
        return tuple(
            CommandBinding(key=key, action=command, description=cls.title,
                           available=cls.available, mode=EditingMode,
                           id=cls.binding_id(mode), show=False, priority=cls.priority,
                           declared_key=cls.declared_key)
            for key in cls.keys
        )

    @staticmethod
    def available(node: Navigation) -> bool:
        return node.accepts_navigation

    def __call__(self, node: Navigation) -> object:
        return node.apply_navigation(self)

    @abstractmethod
    def apply(self, node: Navigation) -> object: ...


class CursorCommand(NavigationCommand):
    """Move the selected row before a list's optional type-to-search handler."""

    priority = True


class VerticalCursorCommand(CursorCommand):
    """Move within a vertical selection without claiming horizontal keys."""


class HorizontalCursorCommand(CursorCommand):
    """Step a horizontal selection using the same cursor priority."""


class CursorLeft(HorizontalCursorCommand):
    keys = ("left",)
    declared_key = LeftKey()

    def apply(self, node: MovesHorizontalCursor) -> object:
        return node.action_cursor_left()


class CursorRight(HorizontalCursorCommand):
    keys = ("right",)
    declared_key = RightKey()

    def apply(self, node: MovesHorizontalCursor) -> object:
        return node.action_cursor_right()


class UpNavigation(NavigationCommand):
    declared_key = UpKey()

    def apply(self, node):
        return node.action_cursor_up()


class DownNavigation(NavigationCommand):
    declared_key = DownKey()

    def apply(self, node):
        return node.action_cursor_down()


class CursorUp(UpNavigation, VerticalCursorCommand):
    keys = ("up",)


class CursorDown(DownNavigation, VerticalCursorCommand):
    keys = ("down",)


class ListCommand(NavigationCommand):
    """Navigation through a list's ends and pages."""


class SelectionCommand(NavigationCommand):
    """Activate the native control's current selection."""

    def apply(self, node):
        return node.action_select_cursor()


class SelectCursor(SelectionCommand, ListCommand):
    keys = ("enter",)


class ActivateSelection(SelectionCommand):
    keys = ("space",)


class FirstNavigation(NavigationCommand):
    def apply(self, node):
        return node.action_first()


class LastNavigation(NavigationCommand):
    def apply(self, node):
        return node.action_last()


class First(FirstNavigation, ListCommand):
    keys = ("home",)


class Last(LastNavigation, ListCommand):
    keys = ("end",)


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

    @property
    def accepts_navigation(self) -> bool:
        return True

    def apply_navigation(self, command: NavigationCommand) -> object:
        return command.apply(self)


class MovesHorizontalCursor(Navigation, key_families=(HorizontalCursorCommand,)):
    """Horizontal lists share declarations while retaining native stepping."""

    def action_cursor_left(self) -> None:
        raise NotImplementedError

    def action_cursor_right(self) -> None:
        raise NotImplementedError


class MovesCursor(Navigation, key_families=(VerticalCursorCommand,)):
    """Selectable controls share arrow declarations, not printable input policy."""

    def action_cursor_up(self) -> None:
        raise NotImplementedError

    def action_cursor_down(self) -> None:
        raise NotImplementedError


class ListNavigation(MovesCursor, key_families=(ListCommand,)):
    """A full list adds end and page operations to the shared cursor keys."""

    def action_first(self) -> None:
        raise NotImplementedError

    def action_last(self) -> None:
        raise NotImplementedError
