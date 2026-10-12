import asyncio
import sys
from asyncio import sleep as asyncio_sleep
from time import monotonic, perf_counter
from weakref import WeakKeyDictionary

WINDOWS = sys.platform == "win32"


if WINDOWS:
    time = perf_counter
else:
    time = monotonic


if WINDOWS:
    # sleep on windows as a resolution of 15ms
    # Python3.11 is somewhat better, but this home-grown version beats it
    # Deduced from practical experiments

    from textual._win_sleep import sleep as win_sleep

    async def sleep(secs: float) -> None:
        """Sleep for a given number of seconds.

        Args:
            secs: Number of seconds to sleep for.
        """
        await asyncio.create_task(win_sleep(secs))

else:

    async def sleep(secs: float) -> None:
        """Sleep for a given number of seconds.

        Args:
            secs: Number of seconds to sleep for.
        """
        # From practical experiments, asyncio.sleep sleeps for at least half a millisecond too much
        # Presumably there is overhead asyncio itself which accounts for this
        # We will reduce the sleep to compensate, and also don't sleep at all for less than half a millisecond
        sleep_for = secs - 0.0005
        if sleep_for > 0:
            await asyncio_sleep(sleep_for)


get_time = time
"""Get the current wall clock (monotonic) time.

Returns:
    The value (in fractional seconds) of a monotonic clock,
    i.e. a clock that cannot go backwards.
"""


async def after_input() -> None:
    """Resume after the loop has run the input and timers that are due.

    Work split into steps so that input is not held behind it needs this
    between the steps. `asyncio.sleep(0)` does not do it: the loop runs what
    was scheduled during a turn before the input and timers it finds in the
    next, so the following step would run ahead of everything that arrived
    during this one and the two would be one wait. A timer that is already
    due runs after them.
    """
    loop = asyncio.get_running_loop()
    resumed = loop.create_future()
    timer = loop.call_later(0, _resume, resumed)
    try:
        await resumed
    finally:
        timer.cancel()


def _resume(resumed: "asyncio.Future[None]") -> None:
    if not resumed.done():
        resumed.set_result(None)


WORK_SLICE = 0.004
"""Seconds of sliced work the loop runs before its due input and timers get a turn."""

# Per loop: when the slice of work its input and timers have not followed yet began.
_slice_began: "WeakKeyDictionary[asyncio.AbstractEventLoop, float]" = WeakKeyDictionary()


async def next_slice() -> None:
    """Begin a unit of work that many tasks do at once (a widget starting up).

    The loop runs every task that is ready before the input and timers that
    became due meanwhile, so a hundred widgets starting together are one wait
    however short each is. A unit that begins here runs at once while the
    units since the loop last ran its due input and timers have taken under
    `WORK_SLICE`; otherwise it runs after they have, in the next slice.
    """
    loop = asyncio.get_running_loop()
    while True:
        began = _slice_began.get(loop)
        if began is None:
            _slice_began[loop] = loop.time()
            # A timer callback runs after the input and timers due in its turn.
            loop.call_later(0, _slice_began.pop, loop, None)
            return
        if loop.time() - began < WORK_SLICE:
            return
        await after_input()
