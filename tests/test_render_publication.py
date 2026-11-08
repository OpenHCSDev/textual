"""Widget source information follows the original output, including partial writes."""

from dataclasses import dataclass

from textual.app import App
from textual._render_publication import SourcePublication
from textual.geometry import Region
from textual.widgets import Static


async def test_source_is_captured_with_strips_and_admitted_only_for_written_cells():
    accepted = []

    @dataclass
    class Captured(SourcePublication):
        text: str

        def admit(self, region):
            accepted.append((self.text, region))

    class Body(Static):
        def capture_render(self, origin, region, strips):
            return Captured("\n".join(strip.text for strip in strips))

    class PublicationApp(App):
        def compose(self):
            yield Body("original body", id="body")

    app = PublicationApp()
    async with app.run_test(size=(20, 4)) as pilot:
        await pilot.pause()
        body = app.query_one(Body)
        compositor = app.screen._compositor
        accepted.clear()
        with app.screen.hold_frames():
            body.update("captured body")
            compositor.update_widgets({body})
            compositor._dirty_regions.clear()
            body.refresh(Region(2, 0, 3, 1))
            compositor.update_widgets({body})
            update = compositor.render_partial_update()
            assert update is not None
            assert accepted == []
            body.update("later unpainted body")
            app._display(app.screen, update)
            assert accepted
            assert all("captured body" in text for text, _region in accepted)
            assert {region for _text, region in accepted} == {Region(2, 0, 3, 1)}
