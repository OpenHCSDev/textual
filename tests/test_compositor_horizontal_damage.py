from unittest.mock import patch

import pytest
from rich.style import Style
from rich.text import Text

from textual.app import App
from textual._compositor import ExposedSpans
from textual.geometry import Region
from textual.widgets import Static


def test_sparse_exposure_retains_source_cells_and_vertical_gaps():
    cuts = [[0, 2, 3, 6, 8] for _ in range(7)]
    bounds = Region(0, 71, 8, 7)
    exposure = ExposedSpans([(71, 0, 8), (72, 0, 8), (75, 0, 8), (77, 0, 8)], cuts, bounds)
    cells = {(x, y) for y in (71, 72, 75, 77) for x in range(8)}
    assert exposure.take(72, 2)
    cells.remove((2, 72))
    exposure.cover(Region(3, 75, 3, 1))
    cells.difference_update((x, 75) for x in range(3, 6))
    for top in range(70, 79):
        for bottom in range(top + 1, 80):
            for left, right in ((0, 8), (0, 3), (2, 6), (3, 8), (1, 7)):
                crop = Region(left, top, right - left, bottom - top)
                actual = {(x, y) for region in exposure.regions(crop)
                          for y in region.line_range for x in range(region.x, region.right)}
                # Chops retain their original complete cut, even when the query
                # starts/ends inside a cell; the output owner crops it later.
                expected = {(x, y) for y in (71, 72, 75, 77) if top <= y < bottom
                            for start, end in zip(cuts[0], cuts[0][1:]) if left <= start < right
                            for x in range(start, end) if (x, y) in cells}
                assert actual == expected
    exposure.cover(bounds)
    assert not tuple(exposure.regions(bounds))


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
        # Strip parity includes authored links and click metadata, rather than
        # only terminal text after cutting around the foreground overlay.
        authored = [segment.style for strip in optimized for segment in strip
                    if segment.style and segment.style.link]
        assert authored
        assert all(style.link == "https://example.com/original-row"
                   and style.meta["@click"] == "original_row" for style in authored)
