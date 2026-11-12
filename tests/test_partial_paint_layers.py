import pytest

from textual.app import App
from textual.containers import Horizontal, Vertical
from textual.widgets import Static


@pytest.mark.parametrize('compositing', [False, True])
async def test_partial_repaints_keep_current_content_in_independent_layers(compositing):
    class Layer(Vertical):
        COMPOSITING_LAYER = compositing
        DEFAULT_CSS = 'Layer { width: 12; height: 3; }'

    left, right = Static('ALPHA'), Static('BETA')
    app = App()
    async with app.run_test(size=(30, 8)) as pilot:
        await app.mount(Horizontal(Layer(left), Layer(right)))
        await pilot.pause()
        compositor = app.screen._compositor
        for label, text in ((left, 'ALPHA'), (right, 'BETA'), (left, 'GAMMA')):
            label.update(text)
            await pilot.pause()
            # Repeat a one-row repaint without changing layout. Hover/style
            # changes use this same path; another layer must not supply its row.
            for _ in range(2):
                compositor._dirty_regions = {label.region}
                update = compositor.render_partial_update()
                assert update is not None
                output = update.render_segments(app.console)
                assert text in output
                update.admit()
