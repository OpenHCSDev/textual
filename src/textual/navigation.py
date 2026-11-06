"""Shared list navigation declarations, consumed through the native keymap."""
from __future__ import annotations

from abc import abstractmethod
from typing import ClassVar

from textual.actions import SkipAction
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


class ScrollCommand(NavigationCommand):
    """A key a scrolling view answers by moving its viewport."""


class ScrollUp(ScrollCommand):
    keys = ("up",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_scroll_up()


class ScrollDown(ScrollCommand):
    keys = ("down",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_scroll_down()


class ScrollLeft(ScrollCommand):
    keys = ("left",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_scroll_left()


class ScrollRight(ScrollCommand):
    keys = ("right",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_scroll_right()


class ScrollHome(ScrollCommand):
    keys = ("home",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_scroll_home()


class ScrollEnd(ScrollCommand):
    keys = ("end",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_scroll_end()


class PageUp(ListCommand, ScrollCommand):
    """A list's page and a view's page are one key and one operation."""

    keys = ("pageup",)

    def apply(self, node):
        return node.action_page_up()


class PageDown(ListCommand, ScrollCommand):
    keys = ("pagedown",)

    def apply(self, node):
        return node.action_page_down()


class PageLeft(ScrollCommand):
    keys = ("ctrl+pageup",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_page_left()


class PageRight(ScrollCommand):
    keys = ("ctrl+pagedown",)

    def apply(self, node: ScrollsView) -> object:
        return node.action_page_right()


class Navigable(DOMNode):
    """A node that answers navigation commands: each command's operation runs on it."""

    @property
    def accepts_navigation(self) -> bool:
        return True

    def apply_navigation(self, command: NavigationCommand) -> object:
        return command.apply(self)


class Navigation(Navigable):
    """Compose navigation families with the control's other key capabilities."""


class ScrollsView(Navigable):
    """Every widget's viewport answers the scroll commands; a scrolling container declares
    their keys (ScrollableContainer's key_families), and a subclass overrides an operation,
    never a key name."""

    def action_scroll_home(self) -> None:
        if not self._allow_scroll:
            raise SkipAction()
        self.scroll_home(x_axis=self.scroll_y == 0)

    def action_scroll_end(self) -> None:
        if not self._allow_scroll:
            raise SkipAction()
        self.scroll_end(x_axis=self.scroll_y == self.is_vertical_scroll_end)

    def action_scroll_left(self) -> None:
        if not self.allow_horizontal_scroll:
            raise SkipAction()
        self.scroll_left()

    def action_scroll_right(self) -> None:
        if not self.allow_horizontal_scroll:
            raise SkipAction()
        self.scroll_right()

    def action_scroll_up(self) -> None:
        if not self.allow_vertical_scroll:
            raise SkipAction()
        self.scroll_up()

    def action_scroll_down(self) -> None:
        if not self.allow_vertical_scroll:
            raise SkipAction()
        self.scroll_down()

    def action_page_down(self) -> None:
        if not self.allow_vertical_scroll:
            raise SkipAction()
        self.scroll_page_down()

    def action_page_up(self) -> None:
        if not self.allow_vertical_scroll:
            raise SkipAction()
        self.scroll_page_up()

    def action_page_left(self) -> None:
        if not self.allow_horizontal_scroll:
            raise SkipAction()
        self.scroll_page_left()

    def action_page_right(self) -> None:
        if not self.allow_horizontal_scroll:
            raise SkipAction()
        self.scroll_page_right()


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
