"""Clipped keyboard-input admission survives changes of cursor appearance."""

import pytest

from textual.app import App, ComposeResult
from textual.containers import Container
from textual.cursor_shape import CursorShape, SteadyBlock
from textual.document._editing import EditingMode
from textual.geometry import Region
from textual.widget import Widget
from textual.widgets import Button, Input, Static, TextArea


@pytest.mark.parametrize("widget_type", (Widget, Static, Button))
def test_non_editable_widgets_do_not_advertise_input(widget_type: type[Widget]) -> None:
    assert widget_type().input_region(Region(3, 4, 20, 5)) == Region()


def test_region_wire_uses_zero_based_cells_and_an_explicit_clear() -> None:
    bounds = Region(3, 4, 20, 5)
    assert App._input_region_sequence(bounds) == "\x1b]777;input-region;3;4;20;5\x1b\\"
    assert App._input_region_sequence() == "\x1b]777;input-region;0;0;0;0\x1b\\"


class InputRegionApp(App[None]):
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
        assert expected and app.keyboard_input_region == expected
        assert not app.keyboard_input_region.contains_point(app.query_one("#outside").region.offset)
        driver = app._driver
        assert driver is not None
        assert driver.to_terminal_region(expected) == expected

        await pilot.click("#outside")
        assert app.focused is entry
        assert app.keyboard_input_region == expected

        await pilot.resize_terminal(12, 15)
        await pilot.pause()
        assert app.keyboard_input_region == expected.intersection(Region(0, 0, 12, 15))

        app.query_one(Button).focus()
        await pilot.pause()
        assert app.keyboard_input_region == Region()

        entry.focus()
        entry.loading = True
        await pilot.pause()
        assert app.keyboard_input_region == Region()
        entry.loading = False
        entry.focus()
        await pilot.pause()
        assert app.keyboard_input_region
        entry.visible = False
        await pilot.pause()
        assert app.keyboard_input_region == Region()


class CommandMode(EditingMode):
    @property
    def accepts_text(self) -> bool:
        return False

    @property
    def cursor_shape(self) -> CursorShape:
        return SteadyBlock()


class TextAreaRegionApp(App[None]):
    def compose(self) -> ComposeResult:
        yield TextArea("text", id="entry")


async def test_editable_input_survives_command_cursor_and_read_only_clears() -> None:
    app = TextAreaRegionApp()
    async with app.run_test(size=(40, 12)) as pilot:
        editor = app.query_one(TextArea)
        editor.focus()
        await pilot.pause()
        assert app.keyboard_input_region == editor.scrollable_content_region
        editor.editing_mode = CommandMode()
        await pilot.pause()
        assert app.cursor_shape == SteadyBlock()
        assert not editor.editing_mode.accepts_text
        assert app.keyboard_input_region == editor.scrollable_content_region
        editor.read_only = True
        await pilot.pause()
        assert app.cursor_shape == SteadyBlock()
        assert app.keyboard_input_region == Region()
