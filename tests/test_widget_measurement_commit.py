from unittest.mock import patch

from textual.app import App
from textual.geometry import Size
from textual.widget import Widget
from textual.widgets import Static


class Measured(Widget):
    DEFAULT_CSS = "Measured { width: 10; height: 4; overflow: hidden hidden; }"

    def __init__(self, *children):
        self.observed = []
        self.resize_from_watch = False
        super().__init__(*children)

    def watch_virtual_size(self, value):
        self.observed.append(value)
        if self.resize_from_watch:
            self.styles.height = value.height


async def test_committed_extent_notifies_watchers_without_remeasuring_parent():
    app = App()
    async with app.run_test() as pilot:
        widget = Measured()
        await app.mount(widget)
        await pilot.pause()
        with patch.object(widget, "refresh", wraps=widget.refresh) as refresh:
            widget._size_updated(Size(10, 4), Size(10, 12), Size(10, 4))
            assert widget.observed[-1] == Size(10, 12)
            assert not any(call.kwargs.get("layout") for call in refresh.call_args_list)
            # Authored extent changes remain ordinary layout inputs.
            widget.virtual_size = Size(10, 16)
            assert any(call.kwargs.get("layout") for call in refresh.call_args_list)


async def test_extent_watcher_can_still_request_real_geometry_change():
    app = App()
    async with app.run_test() as pilot:
        widget = Measured()
        await app.mount(widget)
        await pilot.pause()
        widget.resize_from_watch = True
        with patch.object(widget, "refresh", wraps=widget.refresh) as refresh:
            widget._size_updated(Size(10, 4), Size(10, 8), Size(10, 4))
            assert widget.styles.height.value == 8
            assert any(call.kwargs.get("layout") for call in refresh.call_args_list)


async def test_committed_extent_keeps_scrollbar_layout_invalidation():
    app = App()
    async with app.run_test() as pilot:
        widget = Measured(Widget())
        widget.styles.overflow_y = "auto"
        await app.mount(widget)
        await pilot.pause()
        assert not widget.show_vertical_scrollbar
        with patch.object(widget, "refresh", wraps=widget.refresh) as refresh:
            widget._size_updated(Size(10, 4), Size(10, 20), Size(10, 4))
            assert widget.show_vertical_scrollbar
            assert any(call.kwargs.get("layout") for call in refresh.call_args_list)


async def test_unchanged_geometry_retains_visual_until_content_refresh():
    app = App()
    async with app.run_test() as pilot:
        widget = Static("original")
        await app.mount(widget)
        await pilot.pause()
        visual = widget._render()
        with patch.object(widget, "render", wraps=widget.render) as render:
            widget._size_updated(widget._size, widget.virtual_size, widget._container_size)
            assert widget._render() is visual
            render.assert_not_called()
            widget.update("changed")
            assert widget._render() is not visual
            assert render.call_count == 1
