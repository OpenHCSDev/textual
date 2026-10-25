"""How a focused widget's text cursor appears.

A widget either paints its cursor into a cell (the terminal cursor stays
hidden at its default shape) or hands the cursor to the terminal, which draws
the shape named by its DECSCUSR code at the position the app already places
the terminal cursor (see `App.cursor_position`).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class CursorShape(ABC):
    """How the text cursor appears; equal shapes need no terminal write."""

    @abstractmethod
    def terminal_sequence(self) -> str:
        """Escape sequence that puts the terminal cursor into this shape."""

    @abstractmethod
    def draws_cell(self, cell_visible: bool) -> bool:
        """Whether the widget paints the cursor cell, given its blink phase."""


class CellCursor(CursorShape):
    """The widget paints the cursor cell; the terminal cursor is hidden at its default shape."""

    def terminal_sequence(self) -> str:
        return "\x1b[0 q\x1b[?25l"

    def draws_cell(self, cell_visible: bool) -> bool:
        return cell_visible


class TerminalCursor(CursorShape, ABC):
    """The terminal draws the cursor in the shape its DECSCUSR code names."""

    code: ClassVar[int]

    def terminal_sequence(self) -> str:
        return f"\x1b[{self.code} q\x1b[?25h"

    def draws_cell(self, cell_visible: bool) -> bool:
        return False


class SteadyBlock(TerminalCursor):
    code = 2


class BlinkingBar(TerminalCursor):
    code = 5
