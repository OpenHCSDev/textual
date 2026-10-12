import pytest
from unittest.mock import patch

from textual.app import App
from textual.containers import VerticalGroup, VerticalScroll
from textual.screen import Screen
from textual.widgets import Static


class TargetedScreen(Screen):
    CSS = "VerticalScroll { width: 1fr; } VerticalGroup, Static { height: auto; }"
    targets = ()

    def _use_viewport_layout(self):
        return True

    def _layout_geometry_targets(self):
        return self.targets

    def compose(self):
        with VerticalScroll(id="history"):
            for index in range(100):
                with VerticalGroup(id=f"group-{index}"):
                    yield Static(f"Row {index}: " + "wrapped text " * 10, id=f"row-{index}")
                    yield Static("second line " * 5)


@pytest.mark.parametrize("scoped", [False, True])
async def test_cached_overlay_and_fixed_children_match_the_original_scene(scoped):
    from textual._compositor import Compositor, PlacedSubtreeGeometry

    class CachedBody(VerticalGroup):
        CACHE_SUBTREE_GEOMETRY = True

    body = CachedBody(
        Static("Fixed heading", id="fixed-heading"),
        Static("Screen overlay", id="screen-overlay"),
        *(Static(f"Source row {index}", id=f"source-row-{index}") for index in range(80)),
        id="cached-body",
    )

    class OverlayScreen(TargetedScreen):
        CSS = """
        #fixed-heading { dock: top; height: 1; }
        #screen-overlay { overlay: screen; width: 15; height: 1; offset: 5 3; }
        """

        def compose(self):
            with VerticalScroll(id="history"):
                yield body

    app = App()
    async with app.run_test(size=(40, 10)) as pilot:
        screen = OverlayScreen()
        screen.targets = (body,)
        await app.push_screen(screen)
        await pilot.pause()
        history = screen.query_one("#history", VerticalScroll)
        compositor = screen._compositor
        for position in (0, 30, 0):
            history.scroll_to(y=position, immediate=True, animate=False)
            if scoped:
                # As when the scroll reaches the screen before the frame: the
                # scoped reflow of the scrolled container. It keeps the
                # container behind its scrollbars, as the full arrangement does.
                screen._scrolled_widgets.add(history)
            screen._refresh_layout(app.size, scroll=True)
            # The overlay's clip reaches the outer screen, so this resource
            # keeps placed geometry rather than manufacturing an intrinsic clip.
            assert isinstance(compositor._subtree_geometry[body], PlacedSubtreeGeometry)
            expected, _ = Compositor(max_subtree_geometry_entries=0)._arrange_root(
                screen, app.size, visible_only=False,
            )
            paint = compositor._paint_regions(compositor._ordered_geometry(expected), app.size.region)
            admitted = {node: expected[node] for node in paint}
            admitted[body] = expected[body]  # The original explicit geometry target.
            for node, entry in admitted.items():
                assert node in compositor._visible_map, (position, node.id, entry)
                assert compositor._visible_map[node] == entry
            actual_layers = compositor._ordered_geometry(compositor._visible_map)
            expected_layers = compositor._ordered_geometry(expected)
            assert [(node, entry) for node, entry in actual_layers if node in admitted] == [
                (node, entry) for node, entry in expected_layers if node in admitted
            ]


async def test_offscreen_targets_match_full_geometry_without_full_tree_traversal():
    app = App()
    async with app.run_test(size=(80, 25)) as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        history = screen.query_one("#history", VerticalScroll)
        target = screen.query_one("#row-85", Static)
        screen.targets = (target,)
        for width, scroll in ((80, 0), (55, 30), (100, 250), (65, 0)):
            await pilot.resize_terminal(width, 25)
            history.scroll_to(y=scroll, immediate=True, animate=False)
            screen.refresh(layout=True)
            await pilot.pause()
            # Both layout and scrolling retain the original declared boxes.
            screen._refresh_layout(app.size)
            compositor = screen._compositor
            # Scrolling consumes the same original target declaration. Its
            # fast path must not discard the offscreen box just established.
            with patch.object(compositor, "reflow_visible", wraps=compositor.reflow_visible) as scroll_reflow:
                screen._refresh_layout(app.size, scroll=True)
                assert scroll_reflow.call_count == 1
            assert target in compositor._visible_map
            assert screen.query_one("#row-50") not in compositor._visible_map
            assert len(compositor._visible_map) < 80
            with patch.object(compositor, "_arrange_root", side_effect=AssertionError("Anchor query rebuilt all geometry")):
                actual_target = compositor.find_widget(target)
                rendered = tuple(tuple(strip) for strip in compositor.render_strips())
            compositor.reflow(screen, app.size)
            expected_target = compositor.find_widget(target)
            assert actual_target.region == expected_target.region
            assert actual_target.virtual_region == expected_target.virtual_region
            assert rendered == tuple(tuple(strip) for strip in compositor.render_strips())


async def test_foreign_and_removed_targets_do_not_enter_the_scene():
    app = App()
    async with app.run_test() as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        target = screen.query_one("#row-85")
        await target.remove()
        foreign = Static("foreign")
        screen.targets = (target, foreign)
        screen._refresh_layout(app.size)
        screen._refresh_layout(app.size, scroll=True)
        assert target not in screen._compositor._visible_map
        assert foreign not in screen._compositor._visible_map
        assert not tuple(screen._compositor.published_geometry((target, foreign)))


async def test_capture_requires_publication_while_position_queries_acquire_reader_paths():
    app = App()
    async with app.run_test(size=(80, 25)) as pilot:
        screen = TargetedScreen()
        await app.push_screen(screen)
        await pilot.pause()
        body = screen.query_one("#group-85", VerticalGroup)
        screen._refresh_layout(app.size)
        compositor = screen._compositor
        assert body.is_mounted and body not in compositor._visible_map
        published = compositor._full_map, compositor._visible_map
        with patch.object(compositor, "_arrange_root", side_effect=AssertionError("Capture manufactured a full scene")):
            assert not tuple(compositor.published_geometry((body,)))
        assert compositor._full_map is published[0]
        assert compositor._visible_map is published[1]
        # Position queries acquire this original path in the current scene.
        assert compositor.find_widget(body).region.height > 0
        assert body in compositor._visible_map
        assert screen.query_one("#group-50") not in compositor._visible_map
        assert compositor._full_map is published[0]
        assert compositor._full_map_invalidated
