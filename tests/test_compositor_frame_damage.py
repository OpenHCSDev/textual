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
        assert len(update.chops)==len(update.cuts)==after.height
        assert all(0<=y<after.height and 0<=left<right<=after.width for y,left,right in update.spans)
        assert 'FRAME_CONTENT' in update.render_segments(app.console)

async def test_lazy_full_geometry_preserves_old_caption_damage():
    from textual.screen import Screen
    from textual.widgets import Label
    from textual.containers import VerticalGroup

    class CaptionScreen(Screen):
        CSS = """
        #prompt { dock: bottom; height: auto; }
        #controls { display: none; height: 1; }
        """

        def _use_viewport_layout(self):
            return True

        def compose(self):
            with VerticalGroup(id='prompt'):
                yield Label('Submitting: ORIGINAL_INPUT', id='caption')
                yield Label('Enter queues', id='controls')
                yield Label('Editor')

    app = App()
    async with app.run_test(size=(60, 12)) as pilot:
        screen = CaptionScreen()
        await app.push_screen(screen)
        await pilot.pause()
        compositor = screen._compositor
        caption = screen.query_one('#caption', Label)
        previous = caption.region
        assert compositor._visible_map is not None
        compositor._dirty_regions.clear()
        screen.query_one('#controls', Label).display = True
        caption.update('Queued: ORIGINAL_INPUT')
        # This is the native lazy geometry lookup, before the next timer reflow.
        current = compositor.full_map[caption].region
        assert current.y == previous.y - 1
        update = compositor.render_partial_update()
        assert update is not None
        assert any(y == previous.y and left <= previous.x < right
                   for y, left, right in update.spans), 'Old caption row lost its damage'
        assert any(y == current.y and left <= current.x < right
                   for y, left, right in update.spans)
