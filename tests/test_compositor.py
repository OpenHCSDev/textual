from textual.app import App, ComposeResult
from textual.containers import Container
from textual.widgets import Static
from unittest.mock import patch
import gc
from types import FunctionType
import pytest


async def test_reflow_releases_recursive_closures_without_gc():
    app = App()
    names = {"Compositor._arrange_root.<locals>.add_widget",
             "Compositor._arrange_root.<locals>.get_layers"}

    def retained_closures():
        return {id(value) for value in gc.get_objects()
                if type(value) is FunctionType and value.__qualname__ in names}

    async with app.run_test() as pilot:
        await pilot.pause()
        enabled = gc.isenabled()
        gc.disable()
        try:
            before = retained_closures()
            for _ in range(20):
                app.screen._compositor._arrange_root(app.screen, app.screen.size)
            assert retained_closures() == before, "Finished reflows retained their scene graphs"
        finally:
            if enabled:
                gc.enable()


async def test_compositor_scroll_placements():
    """Regression test for https://github.com/Textualize/textual/issues/5249
    The Static should remain visible.
    """

    class ScrollApp(App):
        CSS = """
        Screen {
            overflow: scroll;
        }
        Container {
            width: 200vw;
        }
        #hello {
            width: 20;
            height: 10;
            offset: 50 10;
            background: blue;
            color: white;
        }
        """

        def compose(self) -> ComposeResult:
            with Container():
                yield Static("Hello", id="hello")

        def on_mount(self) -> None:
            self.screen.scroll_to(20, 0, animate=False)

    app = ScrollApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        static = app.query_one("#hello")
        widgets = app.screen._compositor.visible_widgets
        # The static wasn't scrolled out of view, and should be visible
        # This wasn't the case <= v0.86.1
        assert static in widgets


async def test_full_reflow_replaces_invalidated_scroll_map():
    app = App()
    async with app.run_test() as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        compositor.reflow_visible(app.screen, app.screen.size)
        assert compositor._full_map_invalidated
        compositor.reflow(app.screen, app.screen.size)
        with patch.object(compositor, "_arrange_root", wraps=compositor._arrange_root) as arrange:
            assert compositor.full_map is compositor._full_map
            arrange.assert_not_called()


async def test_layout_geometry_reads_do_not_recursively_rebuild_scene():
    from textual.geometry import Size

    class GeometryReader(Static):
        def get_content_height(self, container, viewport, width):
            # Layouts/widgets can consult their last committed geometry while
            # measuring. That read must not recursively start the same layout.
            self.parent.region
            return super().get_content_height(container, viewport, width)

    class GeometryApp(App):
        CSS = "Container { height: auto; } GeometryReader { height: auto; }"

        def compose(self):
            with Container():
                yield GeometryReader("Word " * 30)

    app = GeometryApp()
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        # Scrolling invalidates the full map; a later width change needs one
        # full arrangement, not a second one from measurement's geometry read.
        compositor.reflow_visible(app.screen, app.screen.size)
        assert compositor._full_map_invalidated
        with patch.object(compositor, "_arrange_root", wraps=compositor._arrange_root) as arrange:
            compositor.reflow(app.screen, Size(45, 20))
            assert arrange.call_count == 1
        actual = compositor.full_map.copy()
        # Force a fresh native pass over the same complete tree for comparison.
        compositor.reflow(app.screen, Size(45, 20))
        assert compositor.full_map == actual

        # A failed lazy measurement must retain its invalidation so the next
        # geometry lookup retries, instead of treating the old map as current.
        compositor._full_map_invalidated = True
        with patch.object(app.screen, "arrange", side_effect=ValueError("measure failed")):
            with pytest.raises(ValueError, match="measure failed"):
                compositor.full_map
        assert not compositor._arranging and compositor._full_map_invalidated
        assert compositor.full_map == actual


async def test_layer_inheritance_updates_between_reflows():
    class LayersApp(App):
        CSS = """
        Container { height: 5; }
        Static { width: 10; height: 1; dock: top; }
        #low { layer: low; }
        #high { layer: high; }
        """

        def compose(self):
            with Container(id="outer"):
                with Container(id="inner"):
                    yield Static("LOW", id="low")
                    yield Static("HIGH", id="high")

    app = LayersApp()
    async with app.run_test() as pilot:
        outer = app.query_one("#outer")
        inner = app.query_one("#inner")
        low = app.query_one("#low")
        high = app.query_one("#high")
        outer.styles.layers = ("low", "high")
        inner.styles.layers = ("high", "low")
        await pilot.pause()
        geometry = app.screen._compositor.full_map
        assert geometry[high].order > geometry[low].order
        outer.styles.layers = ("high", "low")
        await pilot.pause()
        geometry = app.screen._compositor.full_map
        assert geometry[low].order > geometry[high].order


async def test_custom_widget_layers_are_respected():
    class CustomLayers(Container):
        @property
        def layers(self):
            return ("high", "low")

    class LayersApp(App):
        CSS = """
        Container { height: 5; }
        Static { width: 10; height: 1; dock: top; }
        #low { layer: low; }
        #high { layer: high; }
        """

        def compose(self):
            with CustomLayers():
                yield Static("LOW", id="low")
                yield Static("HIGH", id="high")

    app = LayersApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        geometry = app.screen._compositor.full_map
        assert geometry[app.query_one("#low")].order > geometry[app.query_one("#high")].order


async def test_covered_widgets_skip_rendering_without_changing_output():
    class CoverApp(App):
        CSS = """
        Container { width: 100%; height: 100%; background: $primary; }
        Static { width: 100%; height: 100%; background: $background 40%; }
        """

        def compose(self):
            with Container():
                with Container():
                    yield Static("Covered backgrounds\nUnicode café 界", id="foreground")

    app = CoverApp()
    async with app.run_test(size=(60, 20)) as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        outer = app.query_one(Container)
        with patch.object(outer, "render_lines", wraps=outer.render_lines) as render:
            optimized = compositor.render_strips()
            render.assert_not_called()
            original = compositor._get_renders
            # Render every layer as before, using the exact same geometry.
            with patch.object(compositor, "_get_renders", lambda crop=None, render_regions=None: original(crop)):
                reference = compositor.render_strips()
            assert render.call_count > 0
        assert optimized == reference


@pytest.mark.parametrize("rows", [(2, 3), (1, 8), (0, 2, 3, 7, 8)])
async def test_partial_redraw_requests_only_damaged_vertical_rows(rows):
    from textual.geometry import Region

    class Counted(Static):
        def __init__(self):
            self.requested_rows = []
            super().__init__("\n".join(f"Row {index}: café 界" for index in range(40)))

        def render_lines(self, crop):
            self.requested_rows.extend(crop.line_range)
            return super().render_lines(crop)

    class DamageApp(App):
        CSS = "Container { height: 10; overflow-y: scroll; } Counted { height: 40; }"

        def compose(self):
            with Container():
                yield Counted()

    app = DamageApp()
    async with app.run_test(size=(40, 15)) as pilot:
        container = app.query_one(Container)
        widget = app.query_one(Counted)
        compositor = app.screen._compositor
        for scroll_y in (0, 5):
            container.scroll_to(y=scroll_y, animate=False, immediate=True)
            await pilot.pause()
            damage = {Region(3, y, 7, 1) for y in rows}
            widget.requested_rows.clear()
            compositor._dirty_regions = damage.copy()
            actual = compositor.render_partial_update()
            assert widget.requested_rows == [y + scroll_y for y in rows]

            # Native whole-height rendering must generate identical terminal
            # operations/metadata for the same dirty spans, including x clipping.
            original = compositor._get_renders
            with patch.object(compositor, "_get_renders", lambda crop=None, render_regions=None: original(None)):
                compositor._dirty_regions = damage.copy()
                expected = compositor.render_partial_update()
            assert actual.render_segments(app.console) == expected.render_segments(app.console)


async def test_partly_covered_widgets_render_only_exposed_rows():
    class Counted(Static):
        def __init__(self):
            super().__init__("\n".join(f"[bold]Row {y}[/bold]: café 界" for y in range(20)))
            self.requested_rows = []

        def render_lines(self, crop):
            self.requested_rows.extend(crop.line_range)
            return super().render_lines(crop)

    class CoverApp(App):
        CSS = """
        Screen { layers: content overlay; }
        Counted { width: 100%; height: 20; layer: content; }
        #cover { width: 100%; height: 12; offset: 0 4; layer: overlay; dock: top; }
        """

        def compose(self):
            yield Counted()
            yield Static("Foreground", id="cover")

    app = CoverApp()
    async with app.run_test(size=(40, 20)) as pilot:
        await pilot.pause()
        widget = app.query_one(Counted)
        compositor = app.screen._compositor
        widget.requested_rows.clear()
        actual = compositor.render_strips()
        assert widget.requested_rows == [*range(4), *range(16, 20)]
        original = compositor._get_renders
        with patch.object(compositor, "_get_renders", lambda crop=None, render_regions=None: original(crop)):
            expected = compositor.render_strips()
        assert actual == expected
