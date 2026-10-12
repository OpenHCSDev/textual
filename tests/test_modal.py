from __future__ import annotations

from textual.app import App, ComposeResult
from textual.containers import Grid
from textual.screen import ModalScreen
from textual.widgets import Button, Footer, Header, Label

TEXT = """I must not fear.
Fear is the mind-killer.
Fear is the little-death that brings total obliteration.
I will face my fear.
I will permit it to pass over me and through me.
And when it has gone past, I will turn the inner eye to see its path.
Where the fear has gone there will be nothing. Only I will remain."""


class QuitScreen(ModalScreen[bool]):  # (1)!
    """Screen with a dialog to quit."""

    def compose(self) -> ComposeResult:
        yield Grid(
            Label("Are you sure you want to quit?", id="question"),
            Button("Quit", variant="error", id="quit"),
            Button("Cancel", variant="primary", id="cancel"),
            id="dialog",
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "quit":
            self.dismiss(True)
        else:
            self.dismiss(False)


class ModalApp(App):
    """An app with a modal dialog."""

    BINDINGS = [("q", "request_quit", "Quit")]

    CSS = """
QuitScreen {
    align: center middle;
}

#dialog {
    grid-size: 2;
    grid-gutter: 1 2;
    grid-rows: 1fr 3;
    padding: 0 1;
    width: 60;
    height: 11;
    border: thick $background 80%;
    background: $surface;
}

#question {
    column-span: 2;
    height: 1fr;
    width: 1fr;
    content-align: center middle;
}

Button {
    width: 100%;
}

    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield Label(TEXT)
        yield Footer()

    def action_request_quit(self) -> None:
        """Action to display the quit dialog."""

        def check_quit(quit: bool | None) -> None:
            """Called when QuitScreen is dismissed."""

            if quit:
                self.exit()

        self.push_screen(QuitScreen(), check_quit)


async def test_modal_pop_screen():
    # https://github.com/Textualize/textual/issues/4656

    app = ModalApp()
    async with app.run_test() as pilot:
        # Pause to ensure the footer is fully composed to avoid flakiness in CI
        await pilot.pause()
        await pilot.pause()  # Required in Windows
        assert await pilot.click("FooterKey")
        assert await app.wait_for_refresh()
        assert isinstance(app.screen, QuitScreen)
        # Check activating the quit button exits the app
        await pilot.press("enter")
        assert pilot.app._exit


async def test_menu_opening_over_a_screen_keeps_that_screen_drawn():
    """A see-through menu that moves to the pointer as it opens leaves the
    screen behind it on the terminal: every update written while it opens
    draws the rows of the screen below, never blank rows in their place."""
    from textual._compositor import ChopsUpdate, CompositorUpdate, LayoutUpdate
    from textual.containers import Container
    from textual.geometry import Offset
    from textual.widgets import Static

    width, height = 60, 20

    class Menu(ModalScreen[str]):
        CSS = """
        Menu { align: left top; background: transparent; }
        Menu #menu { width: auto; height: auto; border: solid red; }
        Menu .item { height: 1; padding: 0 1; }
        """

        def compose(self) -> ComposeResult:
            with Container(id="menu"):
                for index in range(4):
                    yield Static(f"item {index}", classes="item")

        def on_mount(self) -> None:
            menu = self.query_one("#menu")
            menu.styles.width = 20
            menu.offset = Offset(10, 5)

    class MenuApp(App):
        def __init__(self) -> None:
            super().__init__()
            self.terminal = [[" "] * width for _ in range(height)]

        def compose(self) -> ComposeResult:
            for row in range(height):
                yield Static(f"row {row:02d} " + "x" * 40)

        def write(self, x: int, y: int, text: str) -> None:
            self.terminal[y][x : x + len(text)] = text

        def _display(self, screen, renderable) -> None:
            # Keep the cells each update writes, as a terminal would.
            if isinstance(renderable, CompositorUpdate) and not self._batch_count:
                if isinstance(renderable, LayoutUpdate):
                    for y, line in enumerate(renderable.strips, renderable.region.y):
                        self.write(renderable.region.x, y, "".join(strip.text for strip in line))
                elif isinstance(renderable, ChopsUpdate):
                    for y, x1, x2 in renderable.spans:
                        for x, strip in renderable._get_line_chops(y, x1, x2):
                            self.write(x, y, strip.text)
            super()._display(screen, renderable)

    app = MenuApp()
    async with app.run_test(size=(width, height)) as pilot:
        await pilot.pause()
        app.push_screen(Menu())
        await pilot.pause()
        await pilot.pause()
        shown = ["".join(line) for line in app.terminal]
        assert "item 0" in shown[6]
        for row in (0, 4, 12, height - 1):
            assert shown[row].startswith(f"row {row:02d} xxxx"), shown
        # Beside the menu the screen below is still there.
        assert shown[6].startswith("row 06 xxx") and shown[6].rstrip().endswith("xxxx"), shown
