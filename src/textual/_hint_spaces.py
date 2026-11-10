"""Available visible cells for hint keys, consumed without repeated screen searches."""

from bisect import bisect_left
from collections import defaultdict
from collections.abc import Iterable

from textual.geometry import Offset, Region, Size


class HintSpaces:
    """One frame's blank key-sized slots and their remaining neighbours.

    The occupied spans are sorted once. Successor and predecessor forests remove
    each chosen slot once; a target never restarts a search over the screen.
    """

    def __init__(self, size: Size, occupied: Iterable[Region], width: int) -> None:
        rows: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for region in occupied:
            if 0 <= region.y < size.height - 1:
                rows[region.y].append((max(0, region.x), min(size.width, region.right)))
        slots = []
        for y in range(max(0, size.height - 1)):
            end = 0
            for left, right in sorted(rows[y]):
                slots.extend(Offset(x, y) for x in range(end, left - width + 1, width + 1))
                end = max(end, right + 1)
            slots.extend(Offset(x, y) for x in range(end, size.width - width + 1, width + 1))
        self.slots = tuple(slots)
        self._following = list(range(len(slots) + 1))
        self._preceding = list(range(len(slots) + 1))

    @staticmethod
    def _remaining(parents: list[int], index: int) -> int:
        while parents[index] != index:
            parents[index] = parents[parents[index]]
            index = parents[index]
        return index

    def take(self, origin: Offset) -> Offset | None:
        count = len(self.slots)
        split = bisect_left(self.slots, (origin.y, origin.x),
                            key=lambda offset: (offset.y, offset.x))
        following = self._remaining(self._following, split)
        preceding = self._remaining(self._preceding, count - split)
        candidates = []
        if following < count:
            candidates.append(following)
        if preceding < count:
            candidates.append(count - preceding - 1)
        if not candidates:
            return None
        chosen = min(candidates, key=lambda index: (
            abs(self.slots[index].y - origin.y) + abs(self.slots[index].x - origin.x),
            abs(self.slots[index].y - origin.y), index,
        ))
        self._following[chosen] = self._remaining(self._following, chosen + 1)
        reverse = count - chosen - 1
        self._preceding[reverse] = self._remaining(self._preceding, reverse + 1)
        return self.slots[chosen]

    def allocate(self, origins: Iterable[Offset]) -> tuple[Offset, ...] | None:
        offsets = []
        for origin in origins:
            offset = self.take(origin)
            if offset is None:
                return None
            offsets.append(offset)
        return tuple(offsets)
