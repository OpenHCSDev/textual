"""Native and Styles line policy reach actual measurement and scene paint."""

import pickle

import pytest

from textual.app import App, ComposeResult
from textual.css.scalar import Scalar, Unit
from textual.css.styles import Styles
from textual.geometry import Region, Size
from textual.text_format import TextFormat
from textual.view import WidgetView
from textual.widgets import Static


class NativeText(WidgetView, Static):
    width = Scalar(8, Unit.CELLS, Unit.WIDTH)
    line_align = "right"
    line_wrap = "nowrap"
    line_overflow = "ellipsis"
    line_pad = 1


class TextApp(App):
    def compose(self) -> ComposeResult:
        yield NativeText("one two three four", id="native")
        yield Static("one two three four", id="styled", markup=False)

    def on_mount(self) -> None:
        styled = self.query_one("#styled", Static)
        styled.styles.width = 8
        styled.styles.height = "auto"
        styled.styles.text_align = "right"
        styled.styles.text_wrap = "nowrap"
        styled.styles.text_overflow = "ellipsis"
        styled.styles.line_pad = 1


@pytest.mark.asyncio
async def test_native_line_policy_measures_and_paints_like_styles():
    app = TextApp()
    async with app.run_test() as pilot:
        native = app.query_one(NativeText)
        styled = app.query_one("#styled", Static)
        assert native.text_format is native
        assert styled.text_format is styled.styles
        assert native.content_size == styled.content_size == Size(8, 1)
        assert native.get_content_width(Size(80, 24), Size(80, 24)) == 20
        native_line = native.render_lines(Region(0, 0, 8, 1))[0].text
        styled_line = styled.render_lines(Region(0, 0, 8, 1))[0].text
        assert native_line == styled_line
        assert "…" in native_line

        epoch = styled.styles._cache_key
        styled.styles.text_wrap = "wrap"
        styled.styles.text_overflow = "fold"
        await pilot.pause()
        assert styled.styles._cache_key != epoch
        assert styled.content_size.height > 1
        assert native.content_size.height == 1


def test_styles_preserve_descriptor_defaults_and_snapshot_publication():
    styles = Styles()
    assert styles.text_align == "start"
    assert styles.line_align == TextFormat().line_align == "start"
    styles.text_align = "end"
    styles.text_wrap = "nowrap"
    styles.text_overflow = "ellipsis"
    styles.line_pad = 2
    acquired = pickle.loads(pickle.dumps(styles.snapshot()))
    assert acquired.line_align == "end"
    assert acquired.line_wrap == "nowrap"
    assert acquired.line_overflow == "ellipsis"
    assert acquired.line_pad == 2
    styles.text_align = "right"
    styles.line_pad = 0
    assert acquired.line_align == "end"
    assert acquired.line_pad == 2
