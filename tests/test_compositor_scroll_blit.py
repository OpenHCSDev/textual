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


# --- pure-scroll detection ---

from textual._compositor import Compositor
from textual.geometry import Size, Spacing
from textual.map_geometry import MapGeometry

_CLIP = Region(0, 5, 80, 20)  # rows 5..24, height 20


def _geo(region: Region, clip: Region = _CLIP) -> MapGeometry:
    return MapGeometry(
        region=region, order=(), clip=clip, virtual_size=Size(80, 100),
        container_size=Size(80, 20), virtual_region=region, dock_gutter=Spacing(),
        ancestors=(), gutter=Spacing(),
    )


def _detect(before, after):
    return Compositor._detect_scroll_bands(before, after)


def test_detects_uniform_vertical_scroll():
    a, b = object(), object()
    before = {a: _geo(Region(0, 10, 80, 3)), b: _geo(Region(0, 13, 80, 3))}
    after = {a: _geo(Region(0, 8, 80, 3)), b: _geo(Region(0, 11, 80, 3))}
    # content moved up 2 rows -> shift +2 over the shared clip band
    assert _detect(before, after) == (_CLIP, 2)


def test_scroll_down_is_negative_shift():
    a = object()
    before = {a: _geo(Region(0, 8, 80, 3))}
    after = {a: _geo(Region(0, 11, 80, 3))}  # moved down 3 -> shift -3
    assert _detect(before, after) == (_CLIP, -3)


def test_resize_is_not_a_scroll():
    a = object()
    before = {a: _geo(Region(0, 10, 80, 3))}
    after = {a: _geo(Region(0, 8, 80, 4))}  # height changed
    assert _detect(before, after) is None


def test_horizontal_move_is_not_a_vertical_scroll():
    a = object()
    before = {a: _geo(Region(0, 10, 80, 3))}
    after = {a: _geo(Region(2, 8, 80, 3))}  # dx != 0
    assert _detect(before, after) is None


def test_two_different_translations_are_not_one_scroll():
    a, b = object(), object()
    before = {a: _geo(Region(0, 10, 80, 3)), b: _geo(Region(0, 13, 80, 3))}
    after = {a: _geo(Region(0, 8, 80, 3)), b: _geo(Region(0, 9, 80, 3))}  # -2 and -4
    assert _detect(before, after) is None


def test_shift_clearing_the_band_is_not_blittable():
    a = object()
    before = {a: _geo(Region(0, 5, 80, 3))}
    after = {a: _geo(Region(0, 25, 80, 3))}  # dy 20 == clip height
    assert _detect(before, after) is None


def test_edge_child_scrolling_in_is_allowed():
    a, b, newcomer = object(), object(), object()
    before = {a: _geo(Region(0, 10, 80, 3)), b: _geo(Region(0, 13, 80, 3))}
    after = {
        a: _geo(Region(0, 8, 80, 3)), b: _geo(Region(0, 11, 80, 3)),
        newcomer: _geo(Region(0, 22, 80, 3)),  # scrolled in at the band's bottom
    }
    assert _detect(before, after) == (_CLIP, 2)


def test_change_outside_the_clip_is_not_a_scroll():
    a, outsider = object(), object()
    before = {a: _geo(Region(0, 10, 80, 3))}
    after = {a: _geo(Region(0, 8, 80, 3)), outsider: _geo(Region(0, 100, 80, 3))}
    assert _detect(before, after) is None
