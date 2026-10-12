import asyncio
import gc
from weakref import ref

import pytest

from textual.app import App
from textual.reactive import var
from textual.widgets import Label


class Publisher(Label):
    value = var("quiet")


class Subscriber(Label):
    def receive(self, value):
        self.update(value)


def make_callback(node):
    return lambda value: node.update(value)


@pytest.mark.parametrize("closure", [False, True])
async def test_quiet_reactive_publisher_releases_removed_subscriber(closure):
    app = App()
    async with app.run_test() as pilot:
        publisher = Publisher()
        subscriber = Subscriber("subscriber")
        await app.mount(publisher, subscriber)
        callback = make_callback(subscriber) if closure else subscriber.receive
        subscriber.watch(publisher, "value", callback, init=False)
        retained = ref(subscriber)
        del callback
        await subscriber.remove()
        await pilot.pause()
        assert not getattr(publisher, "__watchers", {}).get("value"), "Quiet publisher retains closed subscriber"
        del subscriber
        gc.collect()
        assert retained() is None


async def test_cancelled_subscriber_unregisters_without_affecting_live_watches():
    app = App()
    async with app.run_test() as pilot:
        publisher, first, second = Publisher(), Subscriber(), Subscriber()
        await app.mount(publisher, first, second)
        first.watch(publisher, "value", first.receive, init=False)
        second.watch(publisher, "value", second.receive, init=False)
        task = first._task
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
        assert [node for node, _ in getattr(publisher, "__watchers")["value"]] == [second]
        publisher.value = "changed"
        await pilot.pause()
        assert second.content == "changed"


async def test_reverse_reactive_ownership_does_not_retain_publisher():
    app = App()
    async with app.run_test() as pilot:
        publisher, subscriber = Publisher(), Label()
        await app.mount(publisher, subscriber)
        subscriber.watch(publisher, "value", subscriber.update, init=False)
        retained = ref(publisher)
        await publisher.remove()
        del publisher
        await pilot.pause()
        gc.collect()
        assert retained() is None
