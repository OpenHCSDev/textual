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
        self.resize_notifications = []

    def compose(self) -> ComposeResult:
        yield Input()

    def _screen_resized(self, size):
        self.layout_requests.append(size)
        return super()._screen_resized(size)

    def on_resize(self, event: Resize):
        self.resize_notifications.append(event)


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
        assert screen.resize_notifications[-1].size == app.size
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
        assert app.screen.resize_notifications[-1].size == Size(155, 18)


async def test_inline_breakpoints_use_viewport_and_observers_keep_pixel_receipt():
    from textual.drivers.headless_driver import HeadlessDriver

    class InlineHeadlessDriver(HeadlessDriver):
        @property
        def is_inline(self):
            return True

    class InlineApp(ResizeApp):
        CSS = "ResizeScreen { height: 5; padding: 0; border: none; }"
        HORIZONTAL_BREAKPOINTS = [(0, "narrow"), (100, "wide")]
        VERTICAL_BREAKPOINTS = [(0, "short"), (20, "tall")]

    app = InlineApp(driver_class=InlineHeadlessDriver)
    async with app.run_test(headless=False, size=(80, 30)) as pilot:
        await pilot.pause()
        screen = app.screen
        assert screen.outer_size.height == 5 < app.size.height
        assert screen.has_class("narrow", "tall")
        receipt = Resize.from_dimensions((120, 40), (1200, 800))
        app.post_message(receipt)
        await pilot.pause()
        assert screen.outer_size == Size(120, 5)
        assert screen.has_class("wide", "tall")
        assert not screen.has_class("narrow") and not screen.has_class("short")
        assert screen.horizontal_breakpoint == 100
        assert receipt in screen.resize_notifications
        assert receipt.pixel_size == Size(1200, 800)
        assert any(event.size == Size(120, 5) for event in screen.resize_notifications)
        # Pixel-only terminal changes remain observable without copying their
        # metadata into the layout command or inferring it from widget geometry.
        pixel_change = Resize.from_dimensions((120, 40), (2400, 1600))
        app.post_message(pixel_change)
        await pilot.pause()
        assert pixel_change in screen.resize_notifications
        assert screen.outer_size == Size(120, 5)
        # A newly pushed screen receives viewport classes through its ordinary
        # resume path even without another terminal event.
        second = ResizeScreen()
        await app.push_screen(second)
        await pilot.pause()
        assert second.has_class("wide", "tall")
        assert second.outer_size == Size(120, 5)
