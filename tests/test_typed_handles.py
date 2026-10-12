"""Listeners and key bindings given as objects, with nothing matched by name."""

from textual import events
from textual.app import App, ComposeResult
from textual.binding import Binding, CallBinding
from textual.containers import Vertical
from textual.widgets import Checkbox, Input


class Panel(Vertical):
    def __init__(self, stop: bool) -> None:
        super().__init__()
        self.box = Checkbox("box")
        self.heard: list[bool] = []
        self.stop = stop
        self.listen(Checkbox.Changed, self.changed)

    def compose(self) -> ComposeResult:
        yield self.box

    def changed(self, message: Checkbox.Changed) -> None:
        self.heard.append(message.value)
        if self.stop:
            message.stop()


class ListeningApp(App[None]):
    def __init__(self, stop: bool) -> None:
        super().__init__()
        self.panel = Panel(stop)
        self.heard: list[bool] = []
        self.mounted = 0
        self.events: list[str] = []
        self.listen(Checkbox.Changed, self.changed)
        self.listen(events.Mount, self.count_mount)
        self.listen(events.Event, self.any_event)

    def compose(self) -> ComposeResult:
        yield self.panel

    async def changed(self, message: Checkbox.Changed) -> None:
        self.heard.append(message.value)

    def count_mount(self, event: events.Mount) -> None:
        self.mounted += 1

    def any_event(self, event: events.Event) -> None:
        self.events.append(type(event).__name__)


async def test_a_parent_hears_the_messages_of_its_children():
    app = ListeningApp(stop=False)
    async with app.run_test() as pilot:
        app.panel.box.value = True
        await pilot.pause()
        assert app.panel.heard == [True]
        assert app.heard == [True]


async def test_a_listener_that_stops_a_message_keeps_it_from_bubbling():
    app = ListeningApp(stop=True)
    async with app.run_test() as pilot:
        app.panel.box.value = True
        await pilot.pause()
        assert app.panel.heard == [True]
        assert app.heard == []


async def test_a_listener_hears_events_and_subclasses_of_its_type():
    app = ListeningApp(stop=False)
    async with app.run_test():
        assert app.mounted == 1
        assert "Mount" in app.events


async def test_a_prevented_message_is_not_heard():
    app = ListeningApp(stop=False)
    async with app.run_test() as pilot:
        with app.panel.box.prevent(Checkbox.Changed):
            app.panel.box.value = True
        await pilot.pause()
        assert app.panel.heard == []


class KeysApp(App[None]):
    def __init__(self) -> None:
        super().__init__()
        self.saved = 0
        self.closed = 0
        self.can_close = False
        self.field = Input()

    def compose(self) -> ComposeResult:
        yield self.field

    def save(self) -> None:
        self.saved += 1

    async def close(self) -> None:
        self.closed += 1

    def close_available(self) -> bool:
        return self.can_close

    BINDINGS = [
        CallBinding("ctrl+s,f2", save, "Save"),
        CallBinding("f3", close, "Close", available=close_available),
    ]


async def test_a_call_binding_calls_the_declaring_node():
    app = KeysApp()
    async with app.run_test() as pilot:
        await pilot.press("ctrl+s", "f2")
        assert app.saved == 2


async def test_an_unavailable_call_binding_is_neither_active_nor_run():
    app = KeysApp()
    async with app.run_test() as pilot:
        await pilot.press("f3")
        assert app.closed == 0
        assert "f3" not in app.screen.active_bindings
        app.can_close = True
        await pilot.press("f3")
        assert app.closed == 1
        assert app.screen.active_bindings["f3"].enabled


def test_splitting_a_key_list_keeps_the_binding_type():
    one, two = Binding.make_bindings([CallBinding("a,b", KeysApp.save, "Save")])
    assert (type(one), one.key, two.key) == (CallBinding, "a", "b")
    assert one.action is KeysApp.save
