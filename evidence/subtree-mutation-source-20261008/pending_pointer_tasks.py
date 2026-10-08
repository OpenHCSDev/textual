"""Read original pending pointer receipts on the application's event loop.

Used by the existing saved-history observer during a slow delivery. No handler,
queue, task, future or timer is replaced; nothing is awaited or scheduled here.
Only identities, declaration locations and native custody are returned, never
event text, widget content or arbitrary frame locals.
"""

import asyncio
import gc
import inspect
from functools import partial

from textual.message import Message
from textual.message_pump import MessagePump
from textual.await_complete import AwaitCompletion


def capture_pointer_wait(app):
    """Capture current App forwarding and the FIFO which owns its receipt."""
    tasks = asyncio.all_tasks()
    frames_by_task = {}
    for task in tasks:
        operation = task.get_coro()
        frames, visited = [], set()
        while operation is not None and id(operation) not in visited:
            visited.add(id(operation))
            if inspect.iscoroutine(operation):
                frame, operation = operation.cr_frame, operation.cr_await
            elif inspect.isgenerator(operation):
                frame, operation = operation.gi_frame, operation.gi_yieldfrom
            else:
                # Coroutine wrappers expose the original coroutine to GC,
                # whereas Future iterators do not own another Python frame.
                operation = next((item for item in gc.get_referents(operation)
                                  if inspect.iscoroutine(item) or inspect.isgenerator(item)), None)
                continue
            if frame is not None:
                frames.append(frame)
        frames_by_task[task] = frames

    def identity(value):
        return None if value is None else f"{type(value).__qualname__}@{id(value):x}"

    def future_state(future):
        if future is None:
            return None
        state = {"identity": identity(future), "done": future.done(),
                 "cancelled": future.cancelled()}
        if isinstance(future, asyncio.Task):
            state["name"] = future.get_name()
        if children := getattr(future, "_children", ()):
            state["children"] = [future_state(child) for child in children]
        return state

    def task_state(task):
        if task is None:
            return None
        chain = []
        for frame in frames_by_task.get(task, ()):
            entry = {"file": frame.f_code.co_filename,
                     "function": frame.f_code.co_qualname, "line": frame.f_lineno}
            owner = frame.f_locals.get("self")
            if isinstance(owner, MessagePump):
                entry["pump"] = identity(owner)
                queue = owner.__dict__.get("_message_queue")
                entry["queued"] = 0 if queue is None else queue.qsize()
            message = frame.f_locals.get("message", frame.f_locals.get("event", frame.f_locals.get("callback")))
            if isinstance(message, Message):
                entry["message"] = identity(message)
                callback = getattr(message, "callback", None)
            else:
                callback = frame.f_locals.get("callback")
            while isinstance(callback, partial):
                callback = callback.func
            if callback is not None:
                entry["callback"] = getattr(callback, "__qualname__", type(callback).__qualname__)
            if isinstance(owner, AwaitCompletion):
                # Observe an already acquired receipt without calling _start:
                # removal may otherwise begin its optional completion here.
                values = vars(owner)
                entry["receipt"] = identity(owner)
                entry["receipt_future"] = future_state(values.get("_future", values.get("_completion")))
            chain.append(entry)
        state = future_state(task)
        state["await_chain"] = chain
        # This is the actual Task waiter, including a gather's original children.
        # An Event / executor waiter does not prove which external operation
        # will release it; the Python await chain remains the evidence there.
        state["waiter"] = future_state(getattr(task, "_fut_waiter", None))
        return state

    receipts = []
    for task, frames in frames_by_task.items():
        for frame in frames:
            if frame.f_code.co_qualname != "MessagePump._post_message_and_wait.<locals>.wait_for_dispatch":
                continue
            message = frame.f_locals["message"]
            custody = message._dispatch_completion
            if custody is None:
                continue
            receiver, caller, completion = custody
            if caller is not app._task or completion.done():
                continue
            queue = receiver.__dict__.get("_message_queue")
            receipts.append({
                "message": identity(message), "receiver": identity(receiver),
                "queued_on_receiver": 0 if queue is None else queue.qsize(),
                "receiver_task": task_state(receiver._task),
                "receipt_wait_task": task_state(task),
                "completion": future_state(completion),
            })
    return {
        "app_task": task_state(app._task), "forwarded_receipts": receipts,
        # Preserve original concurrent await chains for mount / worker joins;
        # no inferred dependency edges are manufactured from similar names.
        "tasks": [task_state(task) for task in tasks],
    }
