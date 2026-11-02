"""Native geometry/paint consumers and focus-listener lifetime."""

from textual import events
from textual.app import App, ComposeResult
from textual.color import Color
from textual.containers import VerticalGroup
from textual.css._style_properties import Edges
from textual.css.scalar import Scalar
from textual.geometry import Region, Size, Spacing
from textual.view import FocusWithinView, WidgetView
from textual.widgets import Input, Static


class NativeLabel(WidgetView, Static):
    width = Scalar.from_number(12)
    height = Scalar.from_number(3)
    padding = Spacing(0, 1, 0, 1)


class NativeInput(WidgetView, Input):
    """Native presentation must retain the actual input's focus capability."""


class FocusFrame(FocusWithinView, VerticalGroup):
    width = Scalar.from_number(20)
    height = Scalar.from_number(5)

    @property
    def border(self) -> Edges:
        colour = Color(255, 0, 0) if self.has_focus_within else Color(0, 255, 0)
        return Edges(*(("solid", colour),) * 4)


class NativeViewApp(App[None]):
    AUTO_FOCUS = None

    def compose(self) -> ComposeResult:
        native = NativeLabel("native", id="native")
        native.styles.width = 55
        yield native
        styled = Static("styled", id="styled")
        styled.styles.width = 23
        styled.styles.height = 2
        yield styled
        yield FocusFrame(Input(id="inside"), id="frame")
        yield NativeInput(id="outside")


def border_colour(frame: FocusFrame) -> tuple[int, int, int]:
    strip = frame.render_lines(Region(0, 0, frame.region.width, 1))[0]
    style = next(iter(strip)).style
    assert style is not None and style.color is not None
    assert style.color.triplet is not None
    red, green, blue = style.color.triplet
    return red, green, blue


async def test_native_geometry_and_styles_backed_sibling() -> None:
    app = NativeViewApp()
    async with app.run_test(size=(80, 24)):
        native = app.query_one("#native", NativeLabel)
        styled = app.query_one("#styled", Static)
        assert native.region.size == Size(12, 3)
        assert styled.region.size == Size(23, 2)
        assert native.geometry is native
        assert native.frame_paint is native
        assert str(native.styles.width) == "55"


async def test_native_input_focus_and_blur_reach_the_real_control() -> None:
    app = NativeViewApp()
    blurred: list[Input.Blurred] = []
    async with app.run_test(size=(80, 24)) as pilot:
        native = app.query_one("#outside", NativeInput)
        native.listen(Input.Blurred, blurred.append)
        native.focus()
        await pilot.pause()
        assert app.focused is native
        native.value = "edited"
        app.query_one("#inside", Input).focus()
        await pilot.pause()
        assert len(blurred) == 1
        assert blurred[0].value == "edited"


async def test_focus_frame_repaints_and_remount_retires_only_its_listeners() -> None:
    app = NativeViewApp()
    external_focus: list[events.DescendantFocus] = []
    async with app.run_test(size=(80, 24)) as pilot:
        frame = app.query_one(FocusFrame)
        frame.listen(events.DescendantFocus, external_focus.append)
        assert border_colour(frame) == (0, 255, 0)
        app.query_one("#inside", Input).focus()
        await pilot.pause()
        assert border_colour(frame) == (255, 0, 0)
        app.query_one("#outside", Input).focus()
        await pilot.pause()
        assert border_colour(frame) == (0, 255, 0)
        await frame.remove()
        assert frame._listeners[events.DescendantFocus] == [external_focus.append]
        await app.mount(frame)
        await frame.mount(Input(id="inside"))
        await pilot.pause()
        assert len(frame._listeners[events.DescendantFocus]) == 2
        assert len(frame._listeners[events.DescendantBlur]) == 1
        app.query_one("#inside", Input).focus()
        await pilot.pause()
        assert border_colour(frame) == (255, 0, 0)
        assert len(external_focus) == 2
