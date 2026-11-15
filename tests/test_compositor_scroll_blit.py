"""Unit tests for ScrollUpdate: the terminal-scroll sequences it emits for each band."""

from rich.console import Console

from textual._compositor import LayoutUpdate, ScrollUpdate
from textual.geometry import Region

ESC = "\x1b"


def _empty_fixup() -> LayoutUpdate:
    return LayoutUpdate([], Region(0, 0, 0, 0))


def test_scroll_up_emits_decstbm_region_su_and_reset():
    # Band rows 5..14 (height 10) -> DECSTBM 1-based inclusive = 6;15.
    # shift +2 = content moved up by 2 -> SU (scroll up) by 2.
    update = ScrollUpdate([(Region(0, 5, 80, 10), 2)], _empty_fixup())
    assert update.render_segments(Console()) == f"{ESC}[6;15r{ESC}[2S{ESC}[r"


def test_scroll_down_emits_sd():
    # shift -3 = content moved down by 3 -> SD (scroll down) by 3.
    update = ScrollUpdate([(Region(0, 0, 80, 20), -3)], _empty_fixup())
    assert update.render_segments(Console()) == f"{ESC}[1;20r{ESC}[3T{ESC}[r"


def test_zero_shift_band_emits_no_scroll():
    update = ScrollUpdate([(Region(0, 5, 80, 10), 0)], _empty_fixup())
    assert update.render_segments(Console()) == ""


def test_multiple_bands_scroll_each_independently():
    update = ScrollUpdate(
        [(Region(0, 0, 40, 10), 1), (Region(0, 12, 40, 8), -2)], _empty_fixup()
    )
    assert update.render_segments(Console()) == (
        f"{ESC}[1;10r{ESC}[1S{ESC}[r" f"{ESC}[13;20r{ESC}[2T{ESC}[r"
    )


def test_fixup_segments_follow_the_scroll():
    # The fixup's cells are appended after every band has scrolled.
    from textual.strip import Strip
    from rich.segment import Segment

    fixup = LayoutUpdate([[Strip([Segment("X")])]], Region(3, 7, 1, 1))
    update = ScrollUpdate([(Region(0, 5, 80, 10), 1)], fixup)
    out = update.render_segments(Console())
    assert out.startswith(f"{ESC}[6;15r{ESC}[1S{ESC}[r")
    # fixup moves the cursor to (3,7) 1-based = 8;4 and writes its cell after the scroll
    assert f"{ESC}[8;4H" in out
    assert out.index(f"{ESC}[1S") < out.index(f"{ESC}[8;4H")
