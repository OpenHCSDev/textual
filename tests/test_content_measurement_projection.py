import pytest

from textual.content import Content
from textual.style import Style
from textual.text_format import TextFormatSnapshot
from textual.visual import RenderOptions


@pytest.mark.parametrize("text", ["", "\n", "a\n\n", "  padded words  ", "a " * 40,
                                  "abcdefghijklmnop", "界 café 界 👍🏽 é", "a\tb\n界\tend"])
@pytest.mark.parametrize("width", [1, 2, 5, 12, 40])
@pytest.mark.parametrize("wrap", ["wrap", "nowrap"])
@pytest.mark.parametrize("overflow", ["fold", "ellipsis", "clip"])
def test_height_projection_matches_native_formatter(text, width, wrap, overflow):
    content = Content(text)
    formatting = TextFormatSnapshot("left", wrap, overflow, 0)
    painted = content.render_strips(
        width, None, Style(), RenderOptions(Style.parse, formatting)
    )
    assert content.get_height(formatting, width) == len(painted)


def test_line_padding_does_not_alias_another_widths_measurement():
    content = Content("one two three four five six")
    for width, padding in [(10, 1), (12, 0), (8, 2), (12, 0)]:
        formatting = TextFormatSnapshot("left", "wrap", "fold", padding)
        painted = content.render_strips(
            width, None, Style(), RenderOptions(Style.parse, formatting)
        )
        assert content.get_height(formatting, width) == len(painted)


@pytest.mark.parametrize("width", [0, 2])
def test_no_available_width_measurement_consumes_all_source_lines(width):
    content = Content("first\n\nlast")
    formatting = TextFormatSnapshot("left", "nowrap", "clip", 1)
    assert content.get_height(formatting, width) == 3
