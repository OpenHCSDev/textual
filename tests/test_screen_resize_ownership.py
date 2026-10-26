"""Viewport requests and committed geometry must not feed one another."""
from textual.app import App, ComposeResult
from textual.events import Resize
from textual.geometry import Size
from textual.screen import Screen
from textual.widgets import Input


class ResizeScreen(Screen):
    def __init__(self):
        super().__init__()
        self.layout_requests = []
        self.committed_sizes = []

    def compose(self) -> ComposeResult:
        yield Input()

    def _screen_resized(self, size):
        self.layout_requests.append(size)
        return super()._screen_resized(size)

    def on_resize(self, event: Resize):
        self.committed_sizes.append(event.size)


class ResizeApp(App):
    def get_default_screen(self):
        return ResizeScreen()


async def test_queued_viewport_change_cannot_be_replaced_by_layout_output():
    app = ResizeApp()
    async with app.run_test(size=(155, 18)) as pilot:
        screen = app.screen
        await pilot.pause()
        screen.layout_requests.clear()
        # Deliver two actual App viewport changes before the screen consumes
        # them. A queued callback keeps the original requests nonadjacent.
        await app._on_resize(Resize(Size(155, 40), Size(155, 40)))
        app._check_resize()
        screen.call_later(lambda: None)
        await app._on_resize(Resize(Size(155, 18), Size(155, 18)))
        app._check_resize()
        await pilot.pause()
        assert screen.outer_size == app.size == Size(155, 18)
        assert screen.committed_sizes[-1] == app.size
        assert all(size == app.size for size in screen.layout_requests)
        await pilot.click(Input)
        await pilot.press('a')
        assert screen.query_one(Input).value == 'a'


async def test_geometry_notification_does_not_request_another_screen_layout():
    app = ResizeApp()
    async with app.run_test(size=(155, 40)) as pilot:
        await pilot.pause()
        app.screen.layout_requests.clear()
        await pilot.resize_terminal(155, 18)
        assert app.screen.layout_requests == [Size(155, 18)]
        assert app.screen.committed_sizes[-1] == Size(155, 18)
