from unittest.mock import patch

import pytest
from rich.style import Style
from rich.text import Text

from textual.app import App
from textual.geometry import Region
from textual.widgets import Static


@pytest.mark.parametrize("offset,width", [(3, 23), (0, 20), (20, 20)])
async def test_horizontal_occlusion_skips_covered_cells_with_native_render_parity(offset, width):
    class Counted(Static):
        def __init__(self):
            super().__init__(Text("界 café 界 " * 50, style=Style(
                bold=True, link="https://example.com/original-row",
                meta={"@click": "original_row"},
            )))
            self.crops = []

        def render_lines(self, crop):
            self.crops.append(crop)
            return super().render_lines(crop)

    class CoverApp(App):
        CSS = """
        Screen { layers: content overlay; }
        Counted { width: 100%; height: 12; layer: content; }
        #cover { height: 12; layer: overlay; dock: top; background: blue 40%; }
        """

        def compose(self):
            yield Counted()
            cover = Static("Foreground", id="cover")
            cover.styles.width = width
            cover.styles.offset = (offset, 0)
            yield cover

    app = CoverApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.pause()
        background = app.query_one(Counted)
        background.crops.clear()
        compositor = app.screen._compositor
        optimized = compositor.render_strips()
        assert background.crops
        optimized_crops = tuple(background.crops)
        covered = Region(offset, 0, width, 12)
        assert all(not crop.overlaps(covered) for crop in background.crops)
        original = compositor._get_renders
        with patch.object(compositor, "_get_renders", lambda crop=None, render_regions=None, *, widgets: original(crop, widgets=widgets)):
            reference = compositor.render_strips()
        assert optimized == reference
        # Query the accepted scene without rendering again. It must expose
        # exactly the cells the native painter requested, even when the cover
        # allows pointer hits through to the widget underneath.
        expected = {crop + background.region.offset for crop in optimized_crops}
        cover = app.query_one("#cover")
        cover.hit_test_transparent = True
        with patch.object(background, "render_lines", side_effect=AssertionError("visibility must not paint")):
            exposed = compositor.exposed_regions((background,))
        actual = set(exposed.get(background, ()))
        assert actual == expected
        assert all(not region.overlaps(covered) for region in actual)
        # Strip parity includes authored links and click metadata, rather than
        # only terminal text after cutting around the foreground overlay.
        authored = [segment.style for strip in optimized for segment in strip
                    if segment.style and segment.style.link]
        assert authored
        assert all(style.link == "https://example.com/original-row"
                   and style.meta["@click"] == "original_row" for style in authored)


async def test_exposure_holds_the_published_scene_until_pending_layout_is_painted():
    class ExposureApp(App):
        CSS = """
        Screen { layers: content overlay; }
        #body { width: 100%; height: 4; layer: content; }
        #cover { width: 100%; height: 1; layer: overlay; dock: top; }
        """

        def compose(self):
            yield Static("body\nbody\nbody\nbody", id="body")
            yield Static("header", id="cover")

    app = ExposureApp()
    async with app.run_test(size=(12, 4)) as pilot:
        await pilot.pause()
        body, cover = app.query_one("#body"), app.query_one("#cover")
        compositor = app.screen._compositor
        expected = {body: (Region(0, 1, 12, 3),)}
        assert compositor.exposed_regions((body,)) == expected
        with app.screen.hold_frames():
            cover.display = False
            await pilot.pause()
            assert compositor.exposed_regions((body,)) == expected
        await pilot.pause()
        assert compositor.exposed_regions((body,)) == {body: (Region(0, 0, 12, 4),)}
