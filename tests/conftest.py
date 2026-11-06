"""Session-wide test terminal.

Rich caches a Style's ANSI codes on the Style itself the first time any console
renders it, whatever that console's colour system, and combined styles are
shared through lru caches. A test run creates many consoles, so their colour
system must be one fact for the whole session, set before any app exists:
otherwise the first 256-colour console fixes those styles' bytes for every
later truecolor one (test_paint_output's digest after the frame-damage tests).
"""

import os

os.environ["COLORTERM"] = "truecolor"
