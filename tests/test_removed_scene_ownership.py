from textual.app import App
from textual.containers import VerticalGroup
from textual.screen import Screen
from textual.widgets import Static
import pytest


@pytest.mark.parametrize("layout", ["vertical", "stream"])
async def test_inactive_scene_releases_removed_geometry_and_arrangements(layout):
    app = App()
    async with app.run_test() as pilot:
        parent = VerticalGroup(Static("retire me"), Static("retain me"))
        parent.styles.layout = layout
        await app.mount(parent)
        await pilot.pause()
        owner = app.screen
        removed = parent.children[0]
        survivor = parent.children[1]
        compositor = owner._compositor
        # Warm every derived projection and several geometry/width entries.
        compositor.full_map
        compositor.visible_widgets
        compositor.layers
        compositor.layers_visible
        parent.arrange(parent.size)
        assert removed in compositor._full_map
        await app.push_screen(Screen())
        await pilot.pause()
        await removed.remove()
        await pilot.pause()
        assert removed._closed
        if layout == "stream":
            assert all(placement.widget is not removed
                       for placement in parent.layout._cached_placements or ())
        assert not any(placement.widget is removed
                       for result in parent._arrangement_cache._cache.values()
                       for placement in result.placements)
        assert removed not in compositor._full_map
        assert removed not in (compositor._visible_map or {})
        assert removed not in compositor.widgets
        assert removed not in compositor.visible_widgets
        assert all(widget is not removed for widget, _ in compositor.layers)
        assert all(widget is not removed for line in compositor.layers_visible
                   for widget, _, _ in line)
        await app.pop_screen()
        await pilot.pause()
        assert survivor in compositor.visible_widgets
        assert survivor.region.y == parent.content_region.y


async def test_removed_child_damage_is_painted_without_retaining_the_child():
    app = App()
    async with app.run_test() as pilot:
        await app.mount(Static("old content", id="old"), Static("survivor", id="survivor"))
        await pilot.pause()
        retired = app.query_one("#old")
        await retired.remove()
        await pilot.pause()
        rows = app.screen._compositor.render_strips()
        text = "\n".join(strip.text for strip in rows)
        assert "old content" not in text
        assert "survivor" in text
        assert retired not in app.screen._compositor.full_map


async def test_inactive_presentation_policy_preserves_models_and_rebuilds_native_pixels():
    class ColdScreen(Screen):
        RETAIN_INACTIVE_PRESENTATION = False

        def compose(self):
            yield Static("Preserved model: café 界", id="model")

    app = App()
    async with app.run_test() as pilot:
        app.add_mode("cold", ColdScreen)
        app.add_mode("other", Screen)
        await app.switch_mode("cold")
        await pilot.pause()
        owner = app.screen
        model = owner.query_one("#model", Static)
        expected = owner._compositor.render_strips()
        assert model._layout_cache
        await app.switch_mode("other")
        await pilot.pause()
        assert model.is_mounted and not model._closed
        assert model._layout_cache == {}
        assert owner._compositor.root is None
        await app.switch_mode("cold")
        await pilot.pause()
        assert owner.query_one("#model") is model
        assert owner._compositor.render_strips() == expected
