"""Text-input bounds survive clipping; cursor visibility is not input admission."""

import pytest

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.cursor_shape import BlinkingBar, CellCursor, CursorShape, SteadyBlock, TextEntryCursor
from textual.geometry import Region
from textual.widgets import Button, Input, Static, TextArea


@pytest.mark.parametrize("cursor", (CellCursor(), BlinkingBar(), SteadyBlock()))
def test_non_entry_cursor_capabilities_do_not_advertise_input(cursor: CursorShape) -> None:
    assert cursor.input_region(Region(3, 4, 20, 5)) == Region()


def test_entry_region_wire_uses_zero_based_cells_and_an_explicit_clear() -> None:
    bounds = Region(3, 4, 20, 5)
    assert TextEntryCursor().input_region(bounds) == bounds
    assert TextEntryCursor().input_region_sequence(bounds) == "\x1b]777;input-region;3;4;20;5\x1b\\"
    assert CellCursor().input_region_sequence() == "\x1b]777;input-region;0;0;0;0\x1b\\"


class InputRegionApp(App):
    CSS = """
    #clip { width: 18; height: 4; overflow: hidden hidden; }
    Input { width: 30; padding: 0 2; border: solid red; }
    """

    def compose(self) -> ComposeResult:
        with Container(id="clip"):
            yield Input("entry", id="entry")
        yield Static("not an input", id="outside")
        yield Button("Other focus", id="other")


async def test_advertised_content_is_clipped_and_non_input_focus_clears() -> None:
    app = InputRegionApp()
    async with app.run_test(size=(40, 15)) as pilot:
        entry = app.query_one(Input)
        entry.focus()
        await pilot.pause()
        expected = entry.scrollable_content_region.intersection(app.query_one("#clip").content_region)
        assert expected and app.cursor_input_region == expected
        assert not app.cursor_input_region.contains_point(app.query_one("#outside").region.offset)
        driver = app._driver
        assert driver is not None
        assert driver.to_terminal_region(expected) == expected

        await pilot.click("#outside")
        assert app.focused is entry
        assert app.cursor_input_region == expected

        await pilot.resize_terminal(12, 15)
        await pilot.pause()
        assert app.cursor_input_region == expected.intersection(Region(0, 0, 12, 15))

        app.query_one(Button).focus()
        await pilot.pause()
        assert app.cursor_input_region == Region()

        entry.focus()
        entry.loading = True
        await pilot.pause()
        assert app.cursor_input_region == Region()
        entry.loading = False
        entry.focus()
        await pilot.pause()
        assert app.cursor_input_region
        entry.visible = False
        await pilot.pause()
        assert app.cursor_input_region == Region()


class TextAreaRegionApp(App):
    def compose(self) -> ComposeResult:
        yield TextArea("text", id="entry")


async def test_text_area_advertises_only_its_entry_cursor_capability() -> None:
    app = TextAreaRegionApp()
    async with app.run_test(size=(40, 12)) as pilot:
        editor = app.query_one(TextArea)
        editor.focus()
        await pilot.pause()
        assert app.cursor_input_region == editor.scrollable_content_region
        editor.read_only = True
        await pilot.pause()
        assert app.cursor_input_region == Region()
