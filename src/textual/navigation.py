"""Textual's controls for the shared navigation commands: the scroll operations every
widget's viewport answers, and the cursor capabilities lists compose."""
from __future__ import annotations

from formbridge.navigation_commands import (
    HorizontalCursorCommand,
    ListCommand,
    NavigationTarget,
    VerticalCursorCommand,
)

from textual.actions import SkipAction
from textual.dom import DOMNode


class Navigable(NavigationTarget, DOMNode):
    """A node that answers navigation commands: each command's operation runs on it."""


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
