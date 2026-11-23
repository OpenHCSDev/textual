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


def _geo(region: Region, clip: Region = _CLIP, *, fixed: bool = False) -> MapGeometry:
    return MapGeometry(
        region=region, order=(), clip=clip, virtual_size=Size(80, 100),
        container_size=Size(80, 20), virtual_region=region, dock_gutter=Spacing(),
        ancestors=(), gutter=Spacing(), fixed=fixed,
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
    # content moved up 2 (shift +2) exposes the band's bottom 2 rows (23..24); the
    # child scrolling in is visible only there.
    after = {
        a: _geo(Region(0, 8, 80, 3)), b: _geo(Region(0, 11, 80, 3)),
        newcomer: _geo(Region(0, 23, 80, 2)),
    }
    assert _detect(before, after) == (_CLIP, 2)


def test_change_outside_the_clip_is_not_a_scroll():
    a, outsider = object(), object()
    before = {a: _geo(Region(0, 10, 80, 3))}
    after = {a: _geo(Region(0, 8, 80, 3)), outsider: _geo(Region(0, 100, 80, 3))}
    assert _detect(before, after) is None


def test_scroll_repaints_fixed_placement_inside_carried_band():
    """The terminal moves every cell in the band, including fixed viewport chrome.

    Its geometry does not move, so the compositor must repaint that region after the
    terminal scroll rather than waiting for a geometry change that will never happen.
    """
    moving, fixed = object(), object()
    before = {
        moving: _geo(Region(0, 10, 80, 3)),
        fixed: _geo(Region(0, 5, 80, 1), fixed=True),
    }
    after = {
        moving: _geo(Region(0, 8, 80, 3)),
        fixed: _geo(Region(0, 5, 80, 1), fixed=True),
    }

    class Owner:
        def check_idle(self) -> None:
            pass

    compositor = Compositor()
    compositor.size = Size(80, 30)
    compositor._damage_geometry(before, after, Owner())

    assert compositor._scroll_bands == [(_CLIP, 2)]
    assert Region(0, 5, 80, 1) in compositor._dirty_regions
    assert Region(0, 23, 80, 2) in compositor._dirty_regions


def test_scroll_damages_carried_ghost_of_top_and_bottom_overlays_and_non_fixed_overlay_children():
    """Scrolling up carries a top overlay down by +dy; scrolling down carries a bottom
    overlay (including a visible child of an invisible docked container, whose own `fixed`
    is False) up by -|dy|. Both the overlay's own region and the carried ghost region must
    be damaged, including when the overlay disappears on that scroll step."""

    class Owner:
        def check_idle(self) -> None:
            pass

    # 1. Scroll UP (dy = +2, shift = -2) with a top sticky header at y=5..6:
    #    terminal blit copies y=5 -> y=7; BOTH y=5 (pinned spot) and y=7 (ghost) must be damaged.
    moving, header = object(), object()
    before = {
        moving: _geo(Region(0, 8, 80, 3)),
        header: _geo(Region(0, 5, 80, 1), fixed=True),
    }
    after = {
        moving: _geo(Region(0, 10, 80, 3)),
        header: _geo(Region(0, 5, 80, 1), fixed=True),
    }
    compositor = Compositor()
    compositor.size = Size(80, 30)
    compositor._damage_geometry(before, after, Owner())
    assert compositor._scroll_bands == [(_CLIP, -2)]
    assert Region(0, 5, 80, 1) in compositor._dirty_regions
    assert Region(0, 7, 80, 1) in compositor._dirty_regions

    # 2. Scroll DOWN (dy = -3, shift = +3) with a bottom button child (fixed=False!) at y=22..25:
    #    terminal blit copies y=22..25 -> y=19..22; BOTH y=22..25 and y=19..22 must be damaged.
    button = object()
    before = {
        moving: _geo(Region(0, 10, 80, 3)),
        button: _geo(Region(25, 22, 30, 3), fixed=False),
    }
    after = {
        moving: _geo(Region(0, 7, 80, 3)),
        button: _geo(Region(25, 22, 30, 3), fixed=False),
    }
    compositor = Compositor()
    compositor.size = Size(80, 30)
    compositor._damage_geometry(before, after, Owner())
    assert compositor._scroll_bands == [(_CLIP, 3)]
    assert Region(25, 22, 30, 3) in compositor._dirty_regions
    assert Region(25, 19, 30, 3) in compositor._dirty_regions

    # 3. Same bottom button disappearing when scrolling down by 3 to the bottom:
    #    the button is absent from `after`, yet the blit still copied its old cells to y=19..22.
    compositor = Compositor()
    compositor.size = Size(80, 30)
    compositor._damage_geometry(before, {moving: _geo(Region(0, 7, 80, 3))}, Owner())
    assert compositor._scroll_bands == [(_CLIP, 3)]
    assert Region(25, 22, 30, 3) in compositor._dirty_regions
    assert Region(25, 19, 30, 3) in compositor._dirty_regions


def test_real_app_scroll_blit_with_top_and_bottom_overlays_never_smears_cells():
    """End-to-end Textual app with a docked top StickyHeader-style overlay AND a docked bottom
    invisible JumpBar holding a visible BackToBottom child: simulate DECSTBM/DECSLRM scroll
    blits and assert every single scroll step matches a full redraw cell-for-cell."""
    import asyncio
    import re
    from textual._compositor import run_steps
    from textual.containers import Center, VerticalScroll
    from textual.widgets import Static
    from tests.test_paint_output import PaintApp

    class TopPin(Static):
        DEFAULT_CSS = """
        TopPin {
            dock: top;
            overlay: screen;
            layer: overlay;
            width: 32;
            height: 1;
            background: #502060;
        }
        """

    class BottomBar(Center):
        DEFAULT_CSS = """
        BottomBar {
            dock: bottom;
            overlay: screen;
            layer: overlay;
            height: 3;
            width: 100%;
            visibility: hidden;
        }
        """

    class BottomButton(Static):
        DEFAULT_CSS = """
        BottomButton {
            width: auto;
            height: auto;
            visibility: visible;
            background: #204060;
        }
        """

    # Minimal VT100/DECSLRM screen grid simulator covering every sequence Textual emits here.
    csi = re.compile(r"\x1b\[(\??)([0-9;]*)([A-Za-z])")

    class Grid:
        def __init__(self, width: int, height: int) -> None:
            self.w, self.h = width, height
            self.cells = [[" "] * width for _ in range(height)]
            self.x = self.y = 0
            self.top, self.bottom = 0, height - 1
            self.left, self.right = 0, width - 1
            self.lrmm = False

        def feed(self, text: str) -> None:
            pos = 0
            for match in csi.finditer(text):
                self._put(text[pos:match.start()])
                pos = match.end()
                priv, params_str, cmd = match.groups()
                params = [int(p) if p else 0 for p in params_str.split(";")] if params_str else []
                if priv == "?" and cmd == "h" and 69 in params:
                    self.lrmm = True
                elif priv == "?" and cmd == "l" and 69 in params:
                    self.lrmm = False
                    self.left, self.right = 0, self.w - 1
                elif priv == "" and cmd == "r":
                    self.top = (params[0] - 1) if len(params) >= 1 and params[0] else 0
                    self.bottom = (params[1] - 1) if len(params) >= 2 and params[1] else self.h - 1
                elif priv == "" and cmd == "s" and self.lrmm:
                    self.left = (params[0] - 1) if len(params) >= 1 and params[0] else 0
                    self.right = (params[1] - 1) if len(params) >= 2 and params[1] else self.w - 1
                elif priv == "" and cmd in ("H", "f"):
                    self.y = max(0, min(self.h - 1, (params[0] if len(params) >= 1 and params[0] else 1) - 1))
                    self.x = max(0, min(self.w - 1, (params[1] if len(params) >= 2 and params[1] else 1) - 1))
                elif priv == "" and cmd == "S":
                    n = params[0] if params and params[0] else 1
                    for row in range(self.top, self.bottom + 1):
                        src = row + n
                        for col in range(self.left, self.right + 1):
                            self.cells[row][col] = self.cells[src][col] if src <= self.bottom else " "
                elif priv == "" and cmd == "T":
                    n = params[0] if params and params[0] else 1
                    for row in range(self.bottom, self.top - 1, -1):
                        src = row - n
                        for col in range(self.left, self.right + 1):
                            self.cells[row][col] = self.cells[src][col] if src >= self.top else " "
            self._put(text[pos:])

        def _put(self, chunk: str) -> None:
            from rich.cells import cell_len
            for ch in chunk:
                if ch in ("\r", "\n"):
                    continue
                width = cell_len(ch)
                if width <= 0:
                    continue
                if 0 <= self.y < self.h and 0 <= self.x < self.w:
                    self.cells[self.y][self.x] = ch
                    if width == 2 and self.x + 1 < self.w:
                        self.cells[self.y][self.x + 1] = ""
                self.x += width

        def lines(self) -> list[str]:
            return ["".join(row) for row in self.cells]

    async def verify() -> None:
        app = PaintApp()
        async with app.run_test(size=(100, 36)) as pilot:
            await pilot.pause()
            app.screen._compositor._supports_rectangular_scroll = True
            history = app.query_one("#history", VerticalScroll)
            top_pin = TopPin("PINNED HEADER")
            bottom_bar = BottomBar(BottomButton("Back to bottom\nEscape"))
            await history.mount(top_pin)
            await history.mount(bottom_bar)
            await pilot.pause()
            history.scroll_to(y=40, animate=False, immediate=True)
            await pilot.pause()

            grid = Grid(100, 36)
            cursor = 0

            def assert_matches(label: str) -> None:
                nonlocal cursor
                for chunk in app.updates[cursor:]:
                    grid.feed(chunk)
                cursor = len(app.updates)
                full = run_steps(app.screen._compositor.render_update(full=True)).render_segments(app.console)
                expected = Grid(100, 36)
                expected.feed(full)
                assert grid.lines() == expected.lines(), f"grid diverged at {label}"

            assert_matches("initial")
            blits = 0
            # Scroll up (carries TopPin down) AND scroll down (carries BottomButton up).
            for step, delta in enumerate((-2, -3, -1, 2, 3, 1, -4, 4)):
                before_len = len(app.updates)
                history.scroll_to(y=history.scroll_y + delta, animate=False)
                await pilot.pause()
                blits += sum(1 for u in app.updates[before_len:] if "\x1b[?69h" in u)
                assert_matches(f"step {step} delta={delta}")
            # Hiding TopPin on scroll-up and BottomBar on scroll-down must also erase blitted ghosts.
            top_pin.display = False
            history.scroll_to(y=history.scroll_y - 2, animate=False)
            await pilot.pause()
            assert_matches("hide top_pin while scrolling up")
            bottom_bar.display = False
            history.scroll_to(y=history.scroll_y + 3, animate=False)
            await pilot.pause()
            assert_matches("hide bottom_bar while scrolling down")
            assert blits > 0, "expected DECSLRM scroll blits to fire"

    asyncio.run(verify())


# --- a resize invalidates a pending scroll blit ---


def test_resize_drops_a_pending_scroll_blit():
    # A band was detected against the old size; applying its terminal scroll region after a
    # resize shifts the wrong rows and leaves a torn frame the optimistic `published` commit
    # then trusts forever. A size change drops the bands and repaints the whole new screen.
    compositor = Compositor()
    compositor.size = Size(80, 24)
    compositor._scroll_bands = [(Region(0, 5, 80, 10), 2)]
    compositor._dirty_regions = {Region(0, 0, 10, 1)}
    compositor._resize(Size(100, 30))
    assert compositor.size == Size(100, 30)
    assert compositor._scroll_bands == []
    assert compositor._dirty_regions == {Region(0, 0, 100, 30)}


def test_same_size_reflow_keeps_a_pending_scroll_blit():
    # Only a real size change invalidates: a same-size reflow keeps the pending band so
    # scroll-blit still fires. Clearing on every reflow would defeat the optimization.
    compositor = Compositor()
    compositor.size = Size(80, 24)
    band = (Region(0, 5, 80, 10), 2)
    compositor._scroll_bands = [band]
    compositor._dirty_regions = {Region(0, 0, 10, 1)}
    compositor._resize(Size(80, 24))
    assert compositor._scroll_bands == [band]


# --- DECRQM capability probe: st's reply -> capability message ---

def test_decrqm_mode69_reply_becomes_rectangular_scroll_message():
    from textual._xterm_parser import XTermParser
    from textual import messages as _messages
    parser = XTermParser(debug=False)
    tokens = list(parser.feed("\x1b[?69;2$y"))  # st: mode 69 recognised, reset
    assert any(isinstance(t, _messages.TerminalSupportsRectangularScroll) for t in tokens)
    # a "not recognised" reply (setting 0) must NOT claim support
    parser2 = XTermParser(debug=False)
    tokens2 = list(parser2.feed("\x1b[?69;0$y"))
    assert not any(isinstance(t, _messages.TerminalSupportsRectangularScroll) for t in tokens2)
