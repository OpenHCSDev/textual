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


def test_both_chop_writers_preserve_wide_cell_clipping_and_metadata():
    """A damage edge inside a wide cell must not overwrite its untouched half."""
    from rich.console import Console
    from rich.control import Control
    from rich.segment import Segment
    from rich.style import Style
    from textual._compositor import ChopsUpdate
    from textual.strip import Strip

    style = Style(meta={"owner": "original"})
    update = ChopsUpdate(
        [{0: Strip([Segment("A界BCD", style)], 6)}],
        [(0, 2, 5)],
        [[0, 6]],
    )
    console = Console(force_terminal=True, color_system="truecolor")
    rich_segments = list(update.__rich_console__(console, console.options))
    assert rich_segments[0] == Control.move_to(2, 0).segment
    content = [segment for segment in rich_segments if not segment.control]
    assert "".join(segment.text for segment in content) == " BC"
    assert all(segment.style.meta == {"owner": "original"} for segment in content)
    assert update.render_segments(console) == Control.move_to(2, 0).segment.text + " BC"


async def test_sparse_damage_publishes_only_selected_native_rows():
    from textual.geometry import Region

    class SparseApp(App):
        def compose(self):
            yield Static("\n".join("ABCDEFGHIJKLM" for _ in range(12)))

    app = SparseApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        cuts = compositor.cuts
        compositor._dirty_regions = {Region(2, 1, 3, 1), Region(4, 8, 2, 1)}
        update = compositor.render_partial_update()
        assert update.cuts is cuts
        assert {y for y, row in enumerate(update.chops) if row} == {1, 8}
        segments = list(update.__rich_console__(app.console, app.console.options))
        assert "".join(segment.text for segment in segments if not segment.control) == "CDE\nEF"


async def test_body_capture_keeps_original_nonzero_row_coordinates():
    class BodyApp(App):
        CSS = "#body { width: 12; height: 3; offset: 5 4; }"

        def compose(self):
            yield Static("ABC界DEF\nSECOND_ROW\nTHIRD_ROW", id="body")

    app = BodyApp()
    async with app.run_test(size=(40, 12)) as pilot:
        await pilot.pause()
        compositor = app.screen._compositor
        body = app.query_one("#body")
        [(original, placement)] = list(compositor.published_geometry([body]))
        assert placement.region.y == 4
        size, strips = compositor.render_subtree_strips(original, placement)
        assert size == Size(12, 3)
        assert [strip.text.rstrip() for strip in strips] == ["ABC界DEF", "SECOND_ROW", "THIRD_ROW"]
