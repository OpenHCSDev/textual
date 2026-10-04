from unittest.mock import patch

import pytest

from textual.app import App
from textual.geometry import Region
from textual.widgets import Static


@pytest.mark.parametrize("offset,width", [(3, 23), (0, 20), (20, 20)])
async def test_horizontal_occlusion_skips_covered_cells_with_native_render_parity(offset, width):
    class Counted(Static):
        def __init__(self):
            super().__init__("[bold]界 café 界[/bold] " * 50)
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
        covered = Region(offset, 0, width, 12)
        assert all(not crop.overlaps(covered) for crop in background.crops)
        original = compositor._get_renders
        with patch.object(compositor, "_get_renders", lambda crop=None, render_regions=None, *, widgets: original(crop, widgets=widgets)):
            reference = compositor.render_strips()
        assert optimized == reference
