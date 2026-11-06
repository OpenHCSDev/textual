from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.lazy import Lazy, Reveal
from textual.widgets import Label


class LazyApp(App):
    def __init__(self) -> None:
        super().__init__()
        self.drawn: list[tuple[int, int]] = []
        """(#foo, #bar) present when each frame was written."""

    def compose(self) -> ComposeResult:
        with Vertical():
            with Lazy(Horizontal()):
                yield Label(id="foo")
            with Horizontal():
                yield Label(id="bar")

    def _display(self, screen, renderable) -> None:
        self.drawn.append((len(self.query("#foo")), len(self.query("#bar"))))
        super()._display(screen, renderable)


async def test_lazy():
    app = LazyApp()
    async with app.run_test() as pilot:
        await pilot.pause()
        await pilot.pause()
        # The first frame is drawn without #foo; it is mounted after that refresh.
        assert app.drawn[0] == (0, 1)
        assert len(app.query("#foo")) == 1
        assert len(app.query("#bar")) == 1


class RevealApp(App):
    def compose(self) -> ComposeResult:
        with Reveal(Vertical()):
            yield Label(id="foo")
            yield Label(id="bar")
            yield Label(id="baz")


async def test_lazy_reveal():
    app = RevealApp()
    async with app.run_test() as pilot:
        # No #foo on initial mount

        # Only first child should be available initially
        assert app.query_one("#foo").display
        # Next two aren't mounted yet
        assert not app.query("#baz")

        # All children should be visible after a pause
        await pilot.pause()
        for n in range(3):
            await pilot.pause(1 / 60)
            await pilot.pause()

        assert app.query_one("#foo").display
        assert app.query_one("#bar").display
        assert app.query_one("#baz").display
