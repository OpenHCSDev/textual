import pytest

from textual.app import App, ComposeResult
from textual.document._editing import EditingMode
from textual.widgets import TextArea


class CursorShapeApp(App[None]):
    def compose(self) -> ComposeResult:
        text_area = TextArea("hello")
        text_area.cursor_blink = False
        yield text_area


HIDDEN_DEFAULT = "\x1b[0 q\x1b[?25l"


@pytest.mark.parametrize(
    ("mode", "focused_sequence", "draws_cell"),
    [
        (EditingMode(), "", True),
    ],
)
async def test_editing_mode_sets_terminal_cursor_shape(
    mode: EditingMode, focused_sequence: str, draws_cell: bool
) -> None:
    """The editing mode owns the cursor shape; the app writes it once per change
    and returns the terminal to its hidden default shape when focus leaves."""
    app = CursorShapeApp()
    async with app.run_test() as pilot:
        text_area = app.query_one(TextArea)
        text_area.focus()
        text_area.editing_mode = mode
        await pilot.pause()

        assert text_area._draw_cursor is draws_cell
        assert app._cursor_shape_change() == focused_sequence
        assert app._cursor_shape_change() == ""

        app.set_focus(None)
        assert app._cursor_shape_change() == (focused_sequence and HIDDEN_DEFAULT)
