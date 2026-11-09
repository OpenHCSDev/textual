import asyncio
import threading


from textual.app import App, ComposeResult
from textual.events import Key
from textual.message import Message
from textual.message_pump import MessagePump
from textual.widget import Widget
from textual.widgets import Button, Input, Label
from textual import events
from textual import on


def test_layout_replacement_preserves_distinct_source_requests():
    from textual.messages import Layout

    first, second = Widget(), Widget()
    request = Layout(first)
    assert request.can_replace(Layout(first))
    assert not request.can_replace(Layout(second))


class ListenerMessage(Message):
    pass


class ChildListenerMessage(ListenerMessage):
    pass


class ListenerPump(MessagePump):
    def __init__(self) -> None:
        super().__init__()
        self.seen: list[str] = []

    @on(ChildListenerMessage)
    def on_child_listener_message(self, message: ChildListenerMessage) -> None:
        self.seen.append("handler")


async def test_listener_self_removal_keeps_the_other_admitted_callback() -> None:
    pump = MessagePump()
    seen: list[str] = []

    def first(message: ListenerMessage) -> None:
        seen.append("first")
        pump.unlisten(ListenerMessage, first)

    def second(message: ListenerMessage) -> None:
        seen.append("second")

    pump.listen(ListenerMessage, first)
    pump.listen(ListenerMessage, second)
    await pump._on_message(ListenerMessage())
    assert seen == ["first", "second"]
    await pump._on_message(ListenerMessage())
    assert seen == ["first", "second", "second"]


async def test_listener_cut_includes_base_callbacks_before_handlers() -> None:
    pump = ListenerPump()

    def later() -> None:
        pump.seen.append("later")

    def parent(message: ListenerMessage) -> None:
        pump.seen.append("parent")

    def first(message: ChildListenerMessage) -> None:
        pump.seen.append("first")
        pump.unlisten(ChildListenerMessage, first)
        pump.unlisten(ListenerMessage, parent)
        pump.listen(ChildListenerMessage, later)

    pump.listen(ChildListenerMessage, first)
    pump.listen(ListenerMessage, parent)
    await pump._on_message(ChildListenerMessage())
    assert pump.seen == ["first", "parent", "handler"]
    await pump._on_message(ChildListenerMessage())
    assert pump.seen == ["first", "parent", "handler", "later", "handler"]


class PreventTestApp(App):
    def __init__(self) -> None:
        self.input_changed_events = []
        super().__init__()

    def compose(self) -> ComposeResult:
        yield Input()

    @on(Input.Changed)
    def on_input_changed(self, event: Input.Changed) -> None:
        self.input_changed_events.append(event)


async def test_message_queue_size():
    """Test message queue size property."""
    app = App()
    assert app.message_queue_size == 0

    class TestMessage(Message):
        pass

    async with app.run_test() as pilot:
        assert app.message_queue_size == 0
        app.post_message(TestMessage())
        assert app.message_queue_size == 1
        app.post_message(TestMessage())
        assert app.message_queue_size == 2
        # A pause will process all the messages
        await pilot.pause()
        assert app.message_queue_size == 0


async def test_peeking_does_not_steal_from_a_waking_message_pump():
    """Selection may inspect the app's next event while its pump is awaiting it."""
    pump = MessagePump()
    waiting = asyncio.create_task(pump._get_message())
    try:
        await asyncio.sleep(0)
        message = Key("x", "x")
        pump._message_queue.put_nowait(message)
        assert pump._peek_message() is message
        assert pump._peek_message() is message
        assert await asyncio.wait_for(waiting, 1) is message
        assert pump._message_queue.empty()
        assert pump._peek_message() is None
    finally:
        waiting.cancel()
        await asyncio.gather(waiting, return_exceptions=True)


async def test_prevent() -> None:
    app = PreventTestApp()

    async with app.run_test() as pilot:
        assert not app.input_changed_events
        input = app.query_one(Input)
        input.value = "foo"
        await pilot.pause()
        assert len(app.input_changed_events) == 1
        assert app.input_changed_events[0].value == "foo"

        with input.prevent(Input.Changed):
            input.value = "bar"

        await pilot.pause()
        assert len(app.input_changed_events) == 1
        assert app.input_changed_events[0].value == "foo"


async def test_prevent_with_call_next() -> None:
    """Test for https://github.com/Textualize/textual/issues/3166.

    Does a callback scheduled with `call_next` respect messages that
    were prevented when it was scheduled?
    """

    hits = 0

    class PreventTestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield Input()

        def change_input(self) -> None:
            self.query_one(Input).value += "a"

        @on(Input.Changed)
        def on_input_changed(self) -> None:
            nonlocal hits
            hits += 1

    app = PreventTestApp()
    async with app.run_test() as pilot:
        app.call_next(app.change_input)
        await pilot.pause()
        assert hits == 1

        with app.prevent(Input.Changed):
            app.call_next(app.change_input)
        await pilot.pause()
        assert hits == 1

        app.call_next(app.change_input)
        await pilot.pause()
        assert hits == 2


async def test_prevent_default():
    """Test that prevent_default doesn't apply when a message is bubbled."""

    app_button_pressed = False

    class MyButton(Button):
        @on(Button.Pressed)
        def _on_button_pressed(self, event: Button.Pressed) -> None:
            event.prevent_default()

    class PreventApp(App[None]):
        def compose(self) -> ComposeResult:
            yield MyButton("Press me")
            yield Label("No pressure")

        @on(Button.Pressed)
        def on_button_pressed(self, event: Button.Pressed) -> None:
            nonlocal app_button_pressed
            app_button_pressed = True
            self.query_one(Label).update("Ouch!")

    app = PreventApp()
    async with app.run_test() as pilot:
        await pilot.click(MyButton)
        assert app_button_pressed


async def test_thread_safe_post_message():
    class TextMessage(Message):
        pass

    class TestApp(App):

        @on(events.Mount)
        def on_mount(self) -> None:
            msg = TextMessage()
            threading.Thread(target=self.post_message, args=(msg,)).start()

        @on(TextMessage)
        def on_text_message(self, message):
            self.exit()

    app = TestApp()

    async with app.run_test() as pilot:
        await pilot.pause()
