"""Native source invalidation through real mounted line surfaces and chrome."""
from textual.app import App
from textual.containers import Container
from textual.geometry import Size
from textual.scroll_view import ScrollView
from textual.scrollbar import ScrollBarRender
from textual.widgets import Log, RichLog, TextArea


async def test_native_line_measurements_survive_paint_and_retire_on_extent():
    lines = Log()
    editor = TextArea("saved\n" * 30)
    group = Container(lines, editor)

    class LinesApp(App):
        CSS = "Container { height: 12; } Log, TextArea { width: 30; height: 5; }"

        def compose(self):
            yield group

    async with LinesApp().run_test(size=(60, 18)) as pilot:
        lines.write_line("original retained row " * 10)
        await pilot.pause()
        chrome = tuple(child for widget in (lines, editor)
                       for child in widget._get_virtual_dom())
        assert chrome
        originals = {widget: widget._layout_updates for widget in (lines, editor, *chrome)}
        before = (lines.virtual_size, editor.virtual_size)
        group.styles.scrollbar_color = "red"
        assert {widget: widget._layout_updates for widget in originals} == originals
        await pilot.pause()
        assert (lines.virtual_size, editor.virtual_size) == before
        # Both original measurement methods follow the actual extent source.
        lines.virtual_size = Size(before[0].width + 2, before[0].height + 3)
        assert lines._layout_updates > originals[lines]
        assert lines.get_content_width(Size(10, 10), Size(60, 18)) == lines.virtual_size.width
        assert lines.get_content_height(Size(10, 10), Size(60, 18), 10) == lines.virtual_size.height
        # A replacement bar renderer still paints within the reserved extent.
        class CustomBar(ScrollBarRender):
            pass
        bar = editor.vertical_scrollbar
        bar.renderer = CustomBar
        before = editor._layout_updates, bar._layout_updates
        group.styles.scrollbar_color = "blue"
        assert (editor._layout_updates, bar._layout_updates) == before


async def test_custom_extent_and_method_supply_stays_conservative():
    class Computed(ScrollView):
        def compute_virtual_size(self):
            return Size(30, 30)

    class Replaced(ScrollView):
        @property
        def virtual_size(self):
            return Size(30, 30)

    class CustomHeight(ScrollView):
        def get_content_height(self, container, viewport, width):
            return 3

    for widget in (Computed(), Replaced(), CustomHeight(), RichLog()):
        assert (widget._content_height_dependency.styles_sensitive(widget)
                or widget._content_width_dependency.styles_sensitive(widget))
        before = widget._layout_updates
        widget.styles.scrollbar_color = "red"
        assert widget._layout_updates > before


def test_scrollbar_paint_contract_follows_class_declaration():
    from textual.scrollbar import ScrollBar, ScrollBarCorner

    class InheritedBar(ScrollBar):
        pass

    class ReplacedBar(ScrollBar):
        def render(self):
            return "custom source"

    class ReplacedBarBody(ScrollBar):
        def _render_bar(self, style):
            return "custom source"

    class InheritedCorner(ScrollBarCorner):
        pass

    class ReplacedCorner(ScrollBarCorner):
        def render(self):
            return "custom source"

    assert not ScrollBar()._render_styles_sensitive()
    assert not InheritedBar()._render_styles_sensitive()
    assert ReplacedBar()._render_styles_sensitive()
    assert ReplacedBarBody()._render_styles_sensitive()
    assert not ScrollBarCorner()._render_styles_sensitive()
    assert not InheritedCorner()._render_styles_sensitive()
    assert ReplacedCorner()._render_styles_sensitive()
