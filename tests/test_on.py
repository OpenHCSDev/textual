from __future__ import annotations

from dataclasses import dataclass

import pytest

from textual import on
from textual._on import ClassScope, OnDecoratorError
from textual.app import App, ComposeResult
from textual.events import Enter, Leave
from textual.message import Message
from textual.message_pump import MessagePump
from textual.widget import Widget
from textual.widgets import Button, TabbedContent, TabPane
from textual import events


async def test_on_button_pressed() -> None:
    """Test handlers with @on decorator."""

    pressed: list[str] = []

    class ButtonApp(App):
        def compose(self) -> ComposeResult:
            yield Button("OK", id="ok")
            yield Button("Cancel", classes="exit cancel")
            yield Button("Quit", classes="exit quit")

        @on(Button.Pressed, "#ok")
        def ok(self):
            pressed.append("ok")

        @on(Button.Pressed, ".exit")
        def exit(self):
            pressed.append("exit")

        @on(Button.Pressed, ".exit.quit")
        def _(self):
            pressed.append("quit")

        @on(Button.Pressed)
        def on_button_pressed(self):
            pressed.append("default")

    app = ButtonApp()
    async with app.run_test() as pilot:
        await pilot.press("enter", "tab", "enter", "tab", "enter")
        await pilot.pause()

    assert pressed == [
        "ok",  # Matched ok first
        "default",  # on_button_pressed matched everything
        "exit",  # Cancel button, matches exit
        "default",  # on_button_pressed matched everything
        "exit",  # Quit button pressed, matched exit and _
        "quit",  # Matched previous button
        "default",  # on_button_pressed matched everything
    ]


async def test_on_inheritance() -> None:
    """Test on decorator and inheritance."""
    pressed: list[str] = []

    class MyWidget(Widget):
        def compose(self) -> ComposeResult:
            yield Button("OK", id="ok")

        # Also called
        @on(Button.Pressed, "#ok")
        def ok(self):
            pressed.append("MyWidget.ok base")

    class DerivedWidget(MyWidget):
        # Should be called first
        @on(Button.Pressed, "#ok")
        def ok(self):
            pressed.append("MyWidget.ok derived")

    class ButtonApp(App):
        def compose(self) -> ComposeResult:
            yield DerivedWidget()

    app = ButtonApp()
    async with app.run_test() as pilot:
        await pilot.press("tab", "enter")

    expected = ["MyWidget.ok derived", "MyWidget.ok base"]
    assert pressed == expected


def test_on_bad_selector() -> None:
    """Check bad selectors raise an error."""

    with pytest.raises(OnDecoratorError):

        @on(Button.Pressed, "@")
        def foo():
            pass


def test_on_no_control() -> None:
    """Check messages with no 'control' attribute raise an error."""

    class CustomMessage(Message):
        pass

    with pytest.raises(OnDecoratorError):

        @on(CustomMessage, "#foo")
        def foo():
            pass


def test_on_attribute_not_listed() -> None:
    """Check `on` checks if the attribute is in ALLOW_SELECTOR_MATCH."""

    class CustomMessage(Message):
        pass

    with pytest.raises(OnDecoratorError):

        @on(CustomMessage, foo="bar")
        def foo():
            pass


async def test_on_arbitrary_attributes() -> None:
    log: list[str] = []

    class OnArbitraryAttributesApp(App[None]):
        def compose(self) -> ComposeResult:
            with TabbedContent():
                yield TabPane("One", id="one")
                yield TabPane("Two", id="two")
                yield TabPane("Three", id="three")

        @on(events.Mount)
        def on_mount(self) -> None:
            self.query_one(TabbedContent).add_class("tabs")

        @on(TabbedContent.TabActivated, pane="#one")
        def one(self) -> None:
            log.append("one")

        @on(TabbedContent.TabActivated, pane="#two")
        def two(self) -> None:
            log.append("two")

    app = OnArbitraryAttributesApp()
    async with app.run_test() as pilot:
        await pilot.press("tab", "right", "right")

    assert log == ["one", "two"]


class MessageSender(Widget):
    @dataclass
    class Parent(Message):
        sender: MessageSender

        @property
        def control(self) -> MessageSender:
            return self.sender

    class Child(Parent):
        pass

    def post_parent(self) -> None:
        self.post_message(self.Parent(self))

    def post_child(self) -> None:
        self.post_message(self.Child(self))


async def test_fire_on_inherited_message() -> None:
    """Handlers should fire when descendant messages are posted."""

    posted: list[str] = []

    class InheritTestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield MessageSender()

        @on(MessageSender.Parent)
        def catch_parent(self) -> None:
            posted.append("parent")

        @on(MessageSender.Child)
        def catch_child(self) -> None:
            posted.append("child")

        @on(events.Mount)
        def on_mount(self) -> None:
            self.query_one(MessageSender).post_parent()
            self.query_one(MessageSender).post_child()

    async with InheritTestApp().run_test():
        pass

    assert posted == ["parent", "child", "parent"]


async def test_fire_inherited_on_single_handler() -> None:
    """Test having parent/child messages on a single handler."""

    posted: list[str] = []

    class InheritTestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield MessageSender()

        @on(MessageSender.Parent)
        @on(MessageSender.Child)
        def catch_either(self, event: MessageSender.Parent) -> None:
            posted.append(f"either {event.__class__.__name__}")

        @on(events.Mount)
        def on_mount(self) -> None:
            self.query_one(MessageSender).post_parent()
            self.query_one(MessageSender).post_child()

    async with InheritTestApp().run_test():
        pass

    assert posted == ["either Parent", "either Child"]


async def test_fire_inherited_on_single_handler_multi_selector() -> None:
    """Test having parent/child messages on a single handler but with different selectors."""

    posted: list[str] = []

    class InheritTestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield MessageSender(classes="a b")

        @on(MessageSender.Parent, ".y")
        @on(MessageSender.Child, ".y")
        @on(MessageSender.Parent, ".a.b")
        @on(MessageSender.Child, ".a.b")
        @on(MessageSender.Parent, ".a")
        @on(MessageSender.Child, ".a")
        @on(MessageSender.Parent, ".b")
        @on(MessageSender.Child, ".b")
        @on(MessageSender.Parent, ".x")
        @on(MessageSender.Child, ".x")
        def catch_either(self, event: MessageSender.Parent) -> None:
            posted.append(f"either {event.__class__.__name__}")

        @on(MessageSender.Child, ".a, .x")
        def catch_selector_list_one_miss(self, event: MessageSender.Parent) -> None:
            posted.append(f"selector list one miss {event.__class__.__name__}")

        @on(MessageSender.Child, ".a, .b")
        def catch_selector_list_two_hits(self, event: MessageSender.Parent) -> None:
            posted.append(f"selector list two hits {event.__class__.__name__}")

        @on(MessageSender.Child, ".a.b")
        def catch_selector_combined_hits(self, event: MessageSender.Parent) -> None:
            posted.append(f"combined hits {event.__class__.__name__}")

        @on(MessageSender.Child, ".a.x")
        def catch_selector_combined_miss(self, event: MessageSender.Parent) -> None:
            posted.append(f"combined miss {event.__class__.__name__}")

        @on(events.Mount)
        def on_mount(self) -> None:
            self.query_one(MessageSender).post_parent()
            self.query_one(MessageSender).post_child()

    async with InheritTestApp().run_test():
        pass

    assert posted == [
        "either Parent",
        "either Child",
        "selector list one miss Child",
        "selector list two hits Child",
        "combined hits Child",
    ]


class MixinMessageSender(Widget):
    class Parent(Message):
        pass

    class JustSomeRandomMixin:
        pass

    class Child(JustSomeRandomMixin, Parent):
        pass

    def post_parent(self) -> None:
        self.post_message(self.Parent())

    def post_child(self) -> None:
        self.post_message(self.Child())


async def test_fire_on_inherited_message_plus_mixins() -> None:
    """Handlers should fire when descendant messages are posted, without mixins messing things up."""

    posted: list[str] = []

    class InheritTestApp(App[None]):
        def compose(self) -> ComposeResult:
            yield MixinMessageSender()

        @on(MixinMessageSender.Parent)
        def catch_parent(self) -> None:
            posted.append("parent")

        @on(MixinMessageSender.Child)
        def catch_child(self) -> None:
            posted.append("child")

        @on(events.Mount)
        def on_mount(self) -> None:
            self.query_one(MixinMessageSender).post_parent()
            self.query_one(MixinMessageSender).post_child()

    async with InheritTestApp().run_test():
        pass

    assert posted == ["parent", "child", "parent"]


async def test_on_with_enter_and_leave_events():
    class EnterLeaveApp(App):
        messages = []

        def compose(self) -> ComposeResult:
            yield Button("OK")

        @on(Enter, "Button")
        @on(Leave, "Button")
        def record(self, event: Enter | Leave) -> None:
            self.messages.append(event.__class__.__name__)

    app = EnterLeaveApp()
    async with app.run_test() as pilot:
        expected_messages = []

        await pilot.hover(Button)
        expected_messages.append("Enter")
        assert app.messages == expected_messages

        await pilot.hover(Button, offset=(0, 20))
        expected_messages.append("Leave")
        assert app.messages == expected_messages


async def test_event_bindings_keep_selectors_and_suppression_live(monkeypatch: pytest.MonkeyPatch) -> None:
    """Reuse event routes while applying each delivery's current state."""
    seen: list[str] = []
    selections = 0
    routes_for = ClassScope.routes_for

    def selected(scope: ClassScope, message_type: type[Message]):
        nonlocal selections
        selections += 1
        return routes_for(scope, message_type)

    monkeypatch.setattr(ClassScope, "routes_for", selected)

    class ParentEvent(events.Event, bubble=False):
        def __init__(self, control: Widget, suppress: bool = False) -> None:
            super().__init__()
            self.target = control
            self.suppress = suppress
            self.set_sender(control)

        @property
        def control(self) -> Widget:
            return self.target

    class ChildEvent(ParentEvent, bubble=False):
        pass

    class BasePump(MessagePump):
        @on(ParentEvent)
        def base(self) -> None:
            seen.append("base")

    class Pump(BasePump):
        @on(ParentEvent)
        @on(ChildEvent)
        def derived(self, event: ParentEvent) -> None:
            seen.append("derived")
            if event.suppress:
                event.prevent_default()

        @on(ParentEvent, ".selected")
        def matching(self) -> None:
            seen.append("selected")

    control = Widget()
    pump = Pump()
    await pump._on_message(ChildEvent(control))
    assert seen == ["derived", "base"]
    bound_selections = selections
    assert bound_selections > 0

    control.add_class("selected")
    await pump._on_message(ChildEvent(control))
    assert seen == ["derived", "base", "derived", "selected", "base"]

    await pump._on_message(ChildEvent(control, suppress=True))
    assert seen[-2:] == ["derived", "selected"]
    assert len(seen) == 7
    assert selections == bound_selections
