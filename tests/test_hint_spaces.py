"""Blank hint cells are consumed once, without overwriting the body or footer."""

import pytest

from textual._hint_spaces import HintSpaces
from textual.geometry import Offset, Region, Size


@pytest.mark.parametrize("width", (1, 2, 3))
@pytest.mark.parametrize("size", (Size(12, 4), Size(40, 12), Size(2, 1)))
def test_hint_spaces_exhaust_once_and_preserve_occupied_cells(width: int, size: Size) -> None:
    occupied = (Region(2, 0, 5, 1), Region(4, 0, 4, 1), Region(1, 1, 3, 1))
    spaces = HintSpaces(size, occupied, width)
    origins = (Offset(index % size.width, index % size.height)
               for index in range(len(spaces.slots)))
    chosen = spaces.allocate(origins)
    assert chosen is not None
    assert len(chosen) == len(set(chosen)) == len(spaces.slots)
    occupied_cells = {(x, region.y) for region in occupied for x in region.column_range}
    consumed = set()
    for offset in chosen:
        assert 0 <= offset.x <= size.width - width
        assert 0 <= offset.y < size.height - 1
        cells = {(x, offset.y) for x in range(offset.x, offset.x + width)}
        assert not cells.intersection(occupied_cells)
        assert not cells.intersection(consumed)
        consumed.update(cells)
    assert spaces.take(Offset(0, 0)) is None
