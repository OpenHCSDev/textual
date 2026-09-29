"""Old-scene damage must be projected into the admitted render frame."""
import pytest
from textual.app import App
from textual.geometry import Size
from textual.widgets import Static

@pytest.mark.parametrize('before,after', [(Size(139,40),Size(139,25)),(Size(80,40),Size(30,12)),(Size(30,12),Size(80,40))])
async def test_partial_damage_uses_current_frame_for_spans_and_chops(before,after):
    class FrameApp(App):
        def compose(self):
            yield Static('\n'.join(f'FRAME_CONTENT_{i}' for i in range(60)))
    app=FrameApp()
    async with app.run_test(size=tuple(before)) as pilot:
        await pilot.pause()
        compositor=app.screen._compositor
        compositor.reflow(app.screen,after)
        update=compositor.render_partial_update()
        assert update is not None
        assert len(update.chops)==len(update.chop_ends)==after.height
        assert all(0<=y<after.height and 0<=left<right<=after.width for y,left,right in update.spans)
        assert 'FRAME_CONTENT' in update.render_segments(app.console)
