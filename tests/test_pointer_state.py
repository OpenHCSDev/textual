"""The pointer does not move when the scene under it is replaced, so the app re-asks what is there.

A retirement used to blank mouse_over and stop, and no mouse event follows a retirement, so a
hovered link lost its highlight until the user moved the mouse.
"""

from textual.app import App, ComposeResult
from textual.widgets import Static


class Links(Static):
    DEFAULT_CSS = """
    Links {
        link-background: red;
        link-background-hover: blue;
    }
    """


class HoverApp(App[None]):
    def compose(self) -> ComposeResult:
        yield Links("[@click=app.bell]hover me[/]")


async def test_a_retirement_under_a_still_pointer_keeps_the_hovered_link() -> None:
    app = HoverApp()
    async with app.run_test(size=(40, 6)) as pilot:
        links = app.query_one(Links)
        cell = (0, 0)
        resting = app.screen.get_style_at(*cell).bgcolor
        await pilot.hover(offset=cell)
        await pilot.pause()
        assert app.screen.get_style_at(*cell).bgcolor != resting, "the hover did not take"
        hovered = app.screen.get_style_at(*cell).bgcolor
        link = links.highlight_link_id
        assert link, "the hovered link has no id"

        # The scene under the pointer is retired. The pointer has not moved.
        app._retire_pointer_widgets({links})
        await pilot.pause()
        await pilot.pause()

        assert app.mouse_over is not None, "the app forgot what the mouse is over"
        assert links.highlight_link_id == link, "the retirement dropped the highlighted link"
        assert app.screen.get_style_at(*cell).bgcolor == hovered, "the link stopped being drawn hovered"


async def test_a_mount_under_a_still_pointer_keeps_the_hovered_link() -> None:
    app = HoverApp()
    async with app.run_test(size=(40, 6)) as pilot:
        links = app.query_one(Links)
        cell = (0, 0)
        await pilot.hover(offset=cell)
        await pilot.pause()
        hovered = app.screen.get_style_at(*cell).bgcolor
        link = links.highlight_link_id

        await app.mount(Static("mounted after the hover"))
        await pilot.pause()
        await pilot.pause()

        assert links.highlight_link_id == link
        assert app.screen.get_style_at(*cell).bgcolor == hovered
