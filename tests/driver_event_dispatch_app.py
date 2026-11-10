"""Compare existing event dispatch paths in one normally launched Android Toad.

This is launch-time instrumentation, not a product setting. Both paths use their
original implementations; selectors and payloads remain live. Timings cover app
work, not physical display presentation.
"""

import argparse
import asyncio
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
from time import monotonic, perf_counter, thread_time
import traceback

from textual._compositor import Compositor
from textual.events import Event
from textual.message import DeclaredMessage, Message
from textual.pilot import Pilot
from toad.application_lifetime import ApplicationLifetime
from toad.cli import main
from toad.comms_root import RemoteCoreConnection
from toad.constants import WELCOME
from toad.navigation_target import channel_target
from toad.screens.welcome import WelcomeEntries
from toad.widgets.comms_sidebar import ThreadStatusRow


class LiveDispatch:
    def activate(self) -> None:
        Event._dispatch_scopes = Message._dispatch_scopes


class BoundDispatch(LiveDispatch):
    def activate(self) -> None:
        Event._dispatch_scopes = DeclaredMessage._dispatch_scopes


@dataclass
class Window:
    mode: str
    rows_before: list[tuple[str, bool]]
    rows_after: list[tuple[str, bool]] = field(default_factory=list)
    paint_wall: list[float] = field(default_factory=list)
    paint_cpu: list[float] = field(default_factory=list)
    elapsed: float = 0
    ui_cpu: float = 0


parser = argparse.ArgumentParser()
parser.add_argument("--profile", type=Path, required=True)
parser.add_argument("--project", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
options = parser.parse_args()
options.output.mkdir(parents=True, exist_ok=True)


async def exercise(lifetime: ApplicationLifetime) -> None:
    app = lifetime.app
    windows: list[Window] = []
    current: Window | None = None
    paint = Compositor._render_chops
    original_dispatch = Event._dispatch_scopes
    result = {"scope": "same-process alternating dispatch; no cProfile; not display FPS"}
    code = 1

    def rows() -> list[tuple[str, bool]]:
        return [(row.target_name, row.busy) for row in app.selected_session.query(ThreadStatusRow)
                if row.animation_visible]

    def painted(*args, **kwargs):
        wall, cpu = perf_counter(), thread_time()
        try:
            return paint(*args, **kwargs)
        finally:
            if current is not None:
                current.paint_wall.append(perf_counter() - wall)
                current.paint_cpu.append(thread_time() - cpu)

    try:
        async with asyncio.timeout(140):
            await lifetime.start_worker.wait()
            assert isinstance(app.coordination_access.connection, RemoteCoreConnection)
            await app.select_session(WELCOME)
            await app.selected_session.open_sidebar_target(channel_target("#comms"))
            await app.select_session(WELCOME)
            pilot = Pilot(app)
            entries = app.selected_session.query_one(WelcomeEntries)
            while not entries.model_state.shows_model() or entries.model_state.shown.observation.shows_status():
                await pilot.pause()
            assert tuple(app.size) == (100, 44), app.size
            result["tabs"] = [str(identity) for identity in app.tab_order.names]
            result["endpoint"] = str(app.coordination_access.connection.endpoint.url)
            app.notify("Dispatch comparison starts in five seconds", timeout=5)
            await asyncio.sleep(5)
            # Warm both real paths before recording either one.
            for mode in (LiveDispatch(), BoundDispatch()):
                mode.activate()
                await asyncio.sleep(3)
            Compositor._render_chops = painted
            for mode in (LiveDispatch(), BoundDispatch(), BoundDispatch(), LiveDispatch()):
                mode.activate()
                await asyncio.sleep(2)
                window = Window(type(mode).__name__, rows())
                assert any(busy for _, busy in window.rows_before)
                current = window
                wall, cpu = monotonic(), thread_time()
                await asyncio.sleep(10)
                window.elapsed, window.ui_cpu = monotonic() - wall, thread_time() - cpu
                current = None
                window.rows_after = rows()
                windows.append(window)
            assert app._exception is None, app._exception
            code = 0
    except BaseException:
        result["failure"] = traceback.format_exc()
    finally:
        Event._dispatch_scopes = original_dispatch
        Compositor._render_chops = paint
        result.update(exit=code, app_exception=repr(app._exception),
                      windows=[asdict(window) for window in windows])
        (options.output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
        app.exit(return_code=code)


def observe(lifetime: ApplicationLifetime) -> None:
    lifetime.app.call_later(lambda: lifetime.app.run_worker(exercise(lifetime), name="Dispatch comparison"))


ApplicationLifetime.observe_next_start(observe)
main(args=["--comms-profile", str(options.profile), str(options.project)])
