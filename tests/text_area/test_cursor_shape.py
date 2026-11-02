import pytest

from textual.app import App, ComposeResult
from textual.document._editing import EditingMode
from textual.widget import Widget
from textual.widgets import Input, TextArea


class CursorShapeApp(App[None]):
    def compose(self) -> ComposeResult:
        text_area = TextArea("hello")
        text_area.cursor_blink = False
        yield text_area
        yield Input("hello")


HIDDEN_DEFAULT = "\x1b[0 q\x1b[?25l"
TERMINAL_BAR = "\x1b[5 q\x1b[?25h"


async def test_editing_mode_sets_terminal_cursor_shape() -> None:
    """The editing mode owns the cursor shape; the app writes it once per change
    and returns the terminal to its hidden default shape when focus leaves."""
    app = CursorShapeApp()
    async with app.run_test() as pilot:
        text_area = app.query_one(TextArea)
        text_area.focus()
        text_area.editing_mode = EditingMode()
        await pilot.pause()

        assert text_area._draw_cursor is False
        assert app._cursor_shape_change() == TERMINAL_BAR
        assert app._cursor_shape_change() == ""

        app.set_focus(None)
        assert app._cursor_shape_change() == HIDDEN_DEFAULT


@pytest.mark.parametrize("entry", [TextArea, Input])
async def test_focused_text_entry_shows_the_terminal_cursor(entry: type[Widget]) -> None:
    """A visible terminal cursor is the signal a phone terminal (Termux) reads to raise
    its soft keyboard, so every focused text entry shows one."""
    app = CursorShapeApp()
    async with app.run_test() as pilot:
        app.query_one(entry).focus()
        await pilot.pause()
        assert app._cursor_shape_change() == TERMINAL_BAR
