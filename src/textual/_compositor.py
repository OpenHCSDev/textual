"""

The compositor handles combining widgets into a single screen (i.e. compositing).

It also stores the results of that process, so that Textual knows the widgets on
the screen and their locations. The compositor uses this information to answer
queries regarding the widget under an offset, or the style under an offset.

Additionally, the compositor can render portions of the screen which may have updated,
without having to render the entire screen.
"""

from __future__ import annotations

from dataclasses import dataclass
from abc import ABC, abstractmethod
from contextlib import contextmanager
from functools import cached_property
from operator import itemgetter
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Callable,
    Generic,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Sequence,
    TypeVar,
    cast,
)

import rich.repr
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.control import Control
from rich.segment import Segment
from rich.style import Style

from textual import errors
from textual._cells import cell_len
from textual._context import visible_screen_stack
from textual._loop import loop_last
from textual.geometry import NULL_SPACING, Offset, Region, Size, Spacing
from textual.map_geometry import MapGeometry
from textual.strip import Strip, StripRenderable
from textual.widget import Widget

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from textual.screen import Screen


class ReflowResult(NamedTuple):
    """The result of a reflow operation. Describes the chances to widgets."""

    hidden: set[Widget]  # Widgets that are hidden
    shown: set[Widget]  # Widgets that are shown
    resized: set[Widget]  # Widgets that have been resized


# Maps a widget on to its geometry (information that describes its position in the composition)
CompositorMap: TypeAlias = "dict[Widget, MapGeometry]"


class SubtreeGeometryKey(NamedTuple):
    geometry_revision: int
    nodes_revision: int
    virtual_region: Region
    region: Region
    order: tuple
    layer_order: int
    clip: Region
    visible: bool
    dock_gutter: Spacing
    screen_size: Size
    visible_only: bool
    scroll_offset: Offset
    inherited_layers: tuple

    @classmethod
    def from_widget(cls, widget: Widget, virtual_region: Region, region: Region,
                    order: tuple, layer_order: int, clip: Region, visible: bool,
                    dock_gutter: Spacing, screen_size: Size, visible_only: bool,
                    inherited_layers: tuple) -> SubtreeGeometryKey:
        """Bind original placement inputs to the widget's current native source."""
        return cls(widget._geometry_revision, widget._nodes._updates,
                   virtual_region, region, order,
                   layer_order, clip, visible, dock_gutter, screen_size,
                   visible_only, widget.scroll_offset, inherited_layers)

    def intrinsic(self) -> SubtreeGeometryKey:
        """Separate placement from the same declared native arrangement inputs."""
        return self._replace(
            virtual_region=self.virtual_region.reset_offset,
            region=self.region.reset_offset, clip=Region(), order=(), layer_order=0,
        )

    def project_order(self, order: tuple, destination: SubtreeGeometryKey) -> tuple:
        """Apply the current native root's rank to its unchanged descendants."""
        if (self.order, self.layer_order) == (destination.order, destination.layer_order):
            return order
        rank_delta = destination.layer_order - self.layer_order
        return destination.order + tuple(
            (layer, z, rank + rank_delta)
            for layer, z, rank in order[len(self.order):]
        )


class SceneClip(ABC):
    """The original clip declaration path, before intersection loses its bounds."""

    @property
    @abstractmethod
    def region(self) -> Region: ...

    def intersect(self, region: Region) -> SceneClip:
        return NestedSceneClip(self, region)

    @abstractmethod
    def relative_bounds(
        self, root: SceneClip, origin: Offset,
    ) -> tuple[SceneClip, tuple[Region, ...]]:
        """Return the original reached scope and at most one relative bound.

        Reaching another root preserves its identity for placed capture; an
        inherited scope stops at the requested declaration. Bounds exclude
        that scope, so outer viewport clipping is never captured as intrinsic.
        """
        ...


@dataclass(frozen=True)
class RootSceneClip(SceneClip):
    bound: Region

    @property
    def region(self) -> Region:
        return self.bound

    def relative_bounds(
        self, root: SceneClip, origin: Offset,
    ) -> tuple[SceneClip, tuple[Region, ...]]:
        return self, ()


@dataclass(frozen=True)
class NestedSceneClip(SceneClip):
    source: SceneClip
    bound: Region

    @cached_property
    def region(self) -> Region:
        return self.source.region.intersection(self.bound)

    def relative_bounds(
        self, root: SceneClip, origin: Offset,
    ) -> tuple[SceneClip, tuple[Region, ...]]:
        if self is root:
            return self, ()
        scope, bounds = self.source.relative_bounds(root, origin)
        bound = self.bound - origin
        return scope, (bounds[0].intersection(bound) if bounds else bound,)


class SubtreeMapGeometry(NamedTuple):
    """Original native geometry with its untruncated intrinsic clip bounds."""

    geometry: MapGeometry
    clip_bounds: tuple[Region, ...]

    def project(self, original: SubtreeGeometryKey, current: SubtreeGeometryKey,
                clip: SceneClip, *, root: bool) -> tuple[MapGeometry, SceneClip]:
        for bound in self.clip_bounds:
            clip = clip.intersect(bound + current.region.offset)
        offset = current.region.offset - original.region.offset
        order = original.project_order(self.geometry.order, current)
        virtual_region = current.virtual_region if root else self.geometry.virtual_region
        if (not offset and clip.region == self.geometry.clip
                and order == self.geometry.order and virtual_region == self.geometry.virtual_region):
            return self.geometry, clip
        return self.geometry._replace(
            region=self.geometry.region + offset, clip=clip.region,
            order=order, virtual_region=virtual_region,
        ), clip


GeometryEntry = TypeVar("GeometryEntry")


@dataclass(frozen=True)
class SubtreeGeometry(ABC, Generic[GeometryEntry]):
    """One immutable native arrangement resource in the compositor's cache."""

    key: SubtreeGeometryKey
    geometry: Mapping[Widget, GeometryEntry]
    widgets: frozenset[Widget]
    invisible_widgets: frozenset[Widget]

    @classmethod
    def complete_arrangement(cls, enclosing_complete: bool) -> bool:
        return enclosing_complete

    @classmethod
    def capture(cls, key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates):
        return cls(key, MappingProxyType(geometry), widgets, invisible_widgets)

    @abstractmethod
    def matches(self, key: SubtreeGeometryKey) -> bool:
        ...

    def restore_into(
        self, geometry: CompositorMap, widgets: set[Widget], invisible_widgets: set[Widget],
        key: SubtreeGeometryKey, clip: SceneClip, clips: dict[Widget, SceneClip],
        root: Widget,
    ) -> None:
        self.project_into(geometry, key, clip, clips, root)
        widgets.update(self.widgets)
        invisible_widgets.update(self.invisible_widgets)

    @abstractmethod
    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
                     clip: SceneClip, clips: dict[Widget, SceneClip], root: Widget) -> None:
        ...

    def references_retired(self, owner: Widget, retired: set[Widget]) -> bool:
        return not retired.isdisjoint((owner, *self.geometry, *self.widgets, *self.invisible_widgets))


@dataclass(frozen=True)
class PlacedSubtreeGeometry(SubtreeGeometry[MapGeometry]):
    """A culled or screen-dependent arrangement keeps its exact placement."""

    def matches(self, key: SubtreeGeometryKey) -> bool:
        return self.key == key

    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
                     clip: SceneClip, clips: dict[Widget, SceneClip], root: Widget) -> None:
        geometry.update(self.geometry)
        clips.update((node, RootSceneClip(entry.clip)) for node, entry in self.geometry.items())


@dataclass(frozen=True)
class IntrinsicSubtreeGeometry(SubtreeGeometry[SubtreeMapGeometry]):
    """The same bounded resource, reusable under a new original outer clip."""

    @classmethod
    def complete_arrangement(cls, enclosing_complete: bool) -> bool:
        return True

    @classmethod
    def capture(cls, key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates):
        if not (widgets | invisible_widgets).isdisjoint(screen_coordinates):
            return PlacedSubtreeGeometry.capture(
                key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates)
        intrinsic = {}
        origin = key.region.offset
        for node, entry in geometry.items():
            scope, bounds = clips[node].relative_bounds(clip, origin)
            if scope is not clip:
                return PlacedSubtreeGeometry.capture(
                    key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates)
            intrinsic[node] = SubtreeMapGeometry(entry, bounds)
        return cls(key, MappingProxyType(intrinsic), widgets, invisible_widgets)

    def matches(self, key: SubtreeGeometryKey) -> bool:
        return self.key.intrinsic() == key.intrinsic()

    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
                     clip: SceneClip, clips: dict[Widget, SceneClip], root: Widget) -> None:
        for node, entry in self.geometry.items():
            geometry[node], clips[node] = entry.project(self.key, key, clip, root=node is root)


class CompositorUpdate:
    """An update generated by the compositor, which also doubles as console renderables."""

    def render_segments(self, console: Console) -> str:
        """Render the update to raw data, suitable for writing to terminal.

        Args:
            console: Console instance.

        Returns:
            Raw data with escape sequences.
        """
        return ""


@rich.repr.auto(angular=True)
class LayoutUpdate(CompositorUpdate):
    """A renderable containing the result of a render for a given region."""

    def __init__(self, strips: list[Iterable[Strip]], region: Region) -> None:
        self.strips = strips
        self.region = region

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        x = self.region.x
        new_line = Segment.line()
        move_to = Control.move_to
        for last, (y, line) in loop_last(enumerate(self.strips, self.region.y)):
            yield move_to(x, y).segment
            for strip in line:
                yield from strip
            if not last:
                yield new_line

    def render_segments(self, console: Console) -> str:
        """Render the update to raw data, suitable for writing to terminal.

        Args:
            console: Console instance.

        Returns:
            Raw data with escape sequences.
        """
        sequences: list[str] = []
        append = sequences.append
        extend = sequences.extend
        x = self.region.x
        move_to = Control.move_to
        for last, (y, line) in loop_last(enumerate(self.strips, self.region.y)):
            append(move_to(x, y).segment.text)
            extend([strip.render(console) for strip in line])
            if not last:
                append("\n")
        return "".join(sequences)

    def __rich_repr__(self) -> rich.repr.Result:
        yield self.region


@rich.repr.auto(angular=True)
class InlineUpdate(CompositorUpdate):
    """A renderable to write an inline update."""

    def __init__(self, strips: list[Strip], clear: bool = False) -> None:
        self.strips = strips
        self.clear = clear

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        new_line = Segment.line()
        for last, line in loop_last(self.strips):
            yield from line
            if not last:
                yield new_line

    def render_segments(self, console: Console) -> str:
        """Render the update to raw data, suitable for writing to terminal.

        Args:
            console: Console instance.

        Returns:
            Raw data with escape sequences.
        """
        sequences: list[str] = []
        append = sequences.append
        for last, strip in loop_last(self.strips):
            append(strip.render(console))
            if not last:
                append("\n")
        if self.clear:
            if len(self.strips) > 1:
                append("\n")
            append("\x1b[J")  # Clear down
        if len(self.strips) > 1:
            back_lines = len(self.strips) if self.clear else len(self.strips) - 1
            append(f"\x1b[{back_lines}A\r")  # Move cursor back to original position
        else:
            append("\r")
        append("\x1b[6n")  # Query new cursor position
        return "".join(sequences)


@rich.repr.auto(angular=True)
class ChopsUpdate(CompositorUpdate):
    """A renderable that applies updated spans to the screen."""

    def __init__(
        self,
        chops: Sequence[Mapping[int, Strip | None]],
        spans: list[tuple[int, int, int]],
        chop_ends: list[list[int]],
    ) -> None:
        """A renderable which updates chops (fragments of lines).

        Args:
            chops: A mapping of offsets to list of segments, per line.
            crop: Region to restrict update to.
            chop_ends: A list of the end offsets for each line
        """
        self.chops = chops
        self.spans = spans
        self.chop_ends = chop_ends

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        move_to = Control.move_to
        new_line = Segment.line()
        chops = self.chops
        chop_ends = self.chop_ends
        last_y = self.spans[-1][0]

        _cell_len = cell_len
        for y, x1, x2 in self.spans:
            line = chops[y]
            ends = chop_ends[y]
            for end, (x, strip) in zip(ends, line.items()):
                # TODO: crop to x extents
                if strip is None:
                    continue

                if x > x2 or end <= x1:
                    continue

                if x2 > x >= x1 and end <= x2:
                    yield move_to(x, y).segment
                    yield from strip
                    continue

                iter_segments = iter(strip)
                if x < x1:
                    for segment in iter_segments:
                        next_x = x + _cell_len(segment.text)
                        if next_x > x1:
                            yield move_to(x, y).segment
                            yield segment
                            break
                        x = next_x
                else:
                    yield move_to(x, y).segment
                if end <= x2:
                    yield from iter_segments
                else:
                    for segment in iter_segments:
                        if x >= x2:
                            break
                        yield segment
                        x += _cell_len(segment.text)

            if y != last_y:
                yield new_line

    def render_segments(self, console: Console) -> str:
        """Render the update to raw data, suitable for writing to terminal.

        Args:
            console: Console instance.

        Returns:
            Raw data with escape sequences.
        """
        sequences: list[str] = []
        append = sequences.append

        move_to = Control.move_to
        chops = self.chops
        chop_ends = self.chop_ends
        last_y = self.spans[-1][0]

        for y, x1, x2 in self.spans:
            line = chops[y]
            ends = chop_ends[y]
            for end, (x, strip) in zip(ends, line.items()):
                if strip is None:
                    continue

                if x > x2 or end <= x1:
                    continue

                if x2 > x >= x1 and end <= x2:
                    append(move_to(x, y).segment.text)
                    append(strip.render(console))
                    continue

                strip = strip.crop(0, min(end, x2) - x)
                append(move_to(x, y).segment.text)
                append(strip.render(console))

            if y != last_y:
                append("\n")

        terminal_sequences = "".join(sequences)
        return terminal_sequences

    def __rich_repr__(self) -> rich.repr.Result:
        yield from ()


@rich.repr.auto(angular=True)
class Compositor:
    """Responsible for storing information regarding the relative positions of Widgets and rendering them."""

    DEFAULT_SUBTREE_GEOMETRY_CACHE_ENTRIES = 64
    """Tunable initial entry budget, not a bound derived from layout semantics."""

    def __init__(self, *, max_subtree_geometry_entries: int = DEFAULT_SUBTREE_GEOMETRY_CACHE_ENTRIES) -> None:
        # A mapping of Widget on to its "render location" (absolute position / depth)
        self._full_map: CompositorMap = {}
        self._full_map_invalidated = True
        self._arranging = False
        """Geometry reads during measurement observe the last committed map."""
        self._render_geometry: tuple[Widget, CompositorMap] | None = None
        """The original arrangement selected by a synchronous body capture."""
        self._visible_map: CompositorMap | None = None
        self._layers: list[tuple[Widget, MapGeometry]] | None = None

        # All widgets considered in the arrangement
        # Note this may be a superset of self.full_map.keys() as some widgets may be invisible for various reasons
        self.widgets: set[Widget] = set()

        # Mapping of visible widgets on to their region, and clip region
        self._visible_widgets: dict[Widget, tuple[Region, Region]] | None = None

        # The top level widget
        self.root: Widget | None = None

        # Dimensions of the arrangement
        self.size = Size(0, 0)

        # The points in each line where the line bisects the left and right edges of the widget
        self._cuts: list[list[int]] | None = None

        # Regions that require an update
        self._dirty_regions: set[Region] = set()

        # Mapping of line numbers on to lists of widget and regions
        self._layers_visible: list[list[tuple[Widget, Region, Region]]] | None = None
        self._subtree_geometry: dict[Widget, SubtreeGeometry] = {}
        self.max_subtree_geometry_entries = max_subtree_geometry_entries

    @property
    def max_subtree_geometry_entries(self) -> int:
        return self._max_subtree_geometry_entries

    @max_subtree_geometry_entries.setter
    def max_subtree_geometry_entries(self, capacity: int) -> None:
        if type(capacity) is not int or capacity < 0:
            raise ValueError("max_subtree_geometry_entries must be a non-negative integer")
        self._max_subtree_geometry_entries = capacity
        while len(self._subtree_geometry) > capacity:
            self._subtree_geometry.pop(next(iter(self._subtree_geometry)))

    def clear(self) -> None:
        """Remove all references to widgets (used when the screen closes)."""
        self.root = None
        self._full_map.clear()
        self._full_map_invalidated = True
        self._visible_map = None
        self._layers = None
        self.widgets.clear()
        self._visible_widgets = None
        self._layers_visible = None
        self._cuts = None
        self._dirty_regions.clear()
        self._subtree_geometry.clear()

    def discard_widgets(self, widgets: set[Widget]) -> None:
        """Release retired scene objects while preserving their repaint damage.

        Geometry invalidation alone leaves the old full map and derived layer
        projections owning removed widgets indefinitely on inactive screens.
        Damage needs rectangles, not the retired widget trees that occupied them.
        """
        for owner, resource in tuple(self._subtree_geometry.items()):
            if resource.references_retired(owner, widgets):
                del self._subtree_geometry[owner]
        changed = False
        for mapping in (self._full_map, self._visible_map):
            if mapping is None:
                continue
            for widget in widgets:
                geometry = mapping.pop(widget, None)
                if geometry is not None:
                    changed = True
                    if region := geometry.region.intersection(geometry.clip):
                        self._dirty_regions.add(region)
        self.widgets.difference_update(widgets)
        if changed:
            self._full_map_invalidated = True
            self._visible_widgets = None
            self._layers = None
            self._layers_visible = None
            self._cuts = None

    @classmethod
    def _regions_to_spans(
        cls, regions: Iterable[Region]
    ) -> Iterable[tuple[int, int, int]]:
        """Converts the regions to horizontal spans. Spans will be combined if they overlap
        or are contiguous to produce optimal non-overlapping spans.

        Args:
            regions: An iterable of Regions.

        Returns:
            Yields tuples of (Y, X1, X2).
        """
        inline_ranges: dict[int, list[tuple[int, int]]] = {}
        setdefault = inline_ranges.setdefault
        for region_x, region_y, width, height in regions:
            span = (region_x, region_x + width)
            for y in range(region_y, region_y + height):
                setdefault(y, []).append(span)

        slice_remaining = slice(1, None)
        for y, ranges in sorted(inline_ranges.items()):
            if len(ranges) == 1:
                # Special case of 1 span
                yield (y, *ranges[0])
            else:
                ranges.sort()
                x1, x2 = ranges[0]
                for next_x1, next_x2 in ranges[slice_remaining]:
                    if next_x1 <= x2:
                        if next_x2 > x2:
                            x2 = next_x2
                    else:
                        yield (y, x1, x2)
                        x1 = next_x1
                        x2 = next_x2
                yield (y, x1, x2)

    def __rich_repr__(self) -> rich.repr.Result:
        yield "size", self.size
        yield "widgets", self.widgets

    def reflow(
        self, parent: Widget, size: Size, *, visible_only: bool = False,
        retain_geometry: Iterable[Widget] = (),
    ) -> ReflowResult:
        """Reflow (layout) widget and its children.

        Args:
            parent: The root widget.
            size: Size of the area to be filled.
            visible_only: Commit viewport geometry and defer offscreen geometry
                until it is queried. Show/hide notifications become viewport-local.
            retain_geometry: Also calculate these widgets' ancestry paths when
                using viewport layout, without traversing unrelated descendants.

        Returns:
            Hidden, shown, and resized widgets.
        """
        previous_map = self._visible_map if visible_only and self._visible_map is not None else self._full_map
        self._cuts = None
        self._layers = None
        self._layers_visible = None
        self._visible_widgets = None
        self._visible_map = None
        self.root = parent
        self.size = size

        # Keep a copy of the old map because we're going to compare it with the update
        old_map = previous_map
        old_widgets = old_map.keys()

        map, widgets = self._arrange_root(
            parent, size, visible_only=visible_only, retain_geometry=retain_geometry,
        )

        new_widgets = map.keys()

        # Newly visible widgets
        shown_widgets = new_widgets - old_widgets

        # Newly hidden widgets
        hidden_widgets = old_widgets - new_widgets if visible_only else self.widgets - widgets

        # Replace map and widgets
        if visible_only:
            self._visible_map = map
        else:
            self._full_map = map
        self._full_map_invalidated = visible_only
        # Measuring widgets may inspect geometry and populate presentation
        # caches from the previous committed map. Publish only the new map.
        self._visible_widgets = None
        self._layers = None
        self._layers_visible = None
        self._cuts = None
        self.widgets = widgets

        # Contains widgets + geometry for every widget that changed (added, removed, or updated)
        changes = map.items() ^ old_map.items()

        # Widgets in both new and old
        common_widgets = old_widgets & new_widgets

        self._damage_geometry(changes, parent)

        resized_widgets = {
            widget
            for widget, (region, *_) in changes
            if (widget in common_widgets and old_map[widget].region.size != region.size)
        }
        return ReflowResult(
            hidden=hidden_widgets,
            shown=shown_widgets,
            resized=resized_widgets,
        )

    def reflow_visible(
        self, parent: Widget, size: Size, *, retain_geometry: Iterable[Widget],
    ) -> set[Widget]:
        """Reflow only the visible children.

        This is a fast-path for scrolling.

        Args:
            parent: The root widget.
            size: Size of the area to be filled.
            retain_geometry: Original transaction's required geometry targets.

        Returns:
            Set of widgets that were exposed by the scroll.
        """
        self._cuts = None
        self._layers = None
        self._layers_visible = None
        self._visible_widgets = None
        self._full_map_invalidated = True
        self.root = parent
        self.size = size

        # Keep a copy of the old map because we're going to compare it with the update
        old_map = self._visible_map or {}
        map, widgets = self._arrange_root(
            parent, size, visible_only=True, retain_geometry=retain_geometry,
        )

        # Replace map and widgets
        self._visible_map = map
        self._visible_widgets = None
        self._layers = None
        self._layers_visible = None
        self._cuts = None
        self.widgets = widgets

        exposed_widgets = map.keys() - old_map.keys()

        # Contains widgets + geometry for every widget that changed (added, removed, or updated)
        changes = map.items() ^ old_map.items()

        self._damage_geometry(changes, parent)

        return exposed_widgets

    def _damage_geometry(self, changes: Iterable[tuple[Widget, MapGeometry]], owner: Widget) -> None:
        """Retain scene damage and admit its original owner to native idle."""
        if self.size.region not in self._dirty_regions:
            self._dirty_regions.update(
                region for _, geometry in changes
                if (region := geometry.clip.intersection(geometry.region))
            )
        if self._dirty_regions:
            owner.check_idle()

    @property
    def full_map(self) -> CompositorMap:
        """Lazily built compositor map that covers all widgets."""

        if self.root is None:
            return {}
        if self._full_map_invalidated and not self._arranging:
            map, _widgets = self._arrange_root(self.root, self.size, visible_only=False)
            # A geometry query also publishes this scene. Retain the damage
            # from its original visible coordinates before replacing the map;
            # a later reflow can no longer recover that previous geometry.
            previous = self._visible_map if self._visible_map is not None else self._full_map
            self._damage_geometry(map.items() ^ previous.items(), self.root)
            self._full_map = map
            self._full_map_invalidated = False
            self._visible_widgets = None
            self._visible_map = None
            self._layers = None
            self._layers_visible = None
            self._cuts = None

        return self._full_map

    @property
    def visible_widgets(self) -> dict[Widget, tuple[Region, Region]]:
        """Get a mapping of widgets on to region and clip.

        Returns:
            Visible widget mapping.
        """

        if self._visible_widgets is None:
            map = (
                self._visible_map
                if self._visible_map is not None
                else (self._full_map or {})
            )
            self._visible_widgets = self._paint_regions(map, self.size.region)
        return self._visible_widgets

    @staticmethod
    def _paint_regions(geometry: Mapping[Widget, MapGeometry], bounds: Region
                       ) -> dict[Widget, tuple[Region, Region]]:
        """The same native front-to-back order for a screen or intrinsic body."""
        regions = [(entry.order, widget, entry.region, entry.clip)
                   for widget, entry in geometry.items()
                   if bounds.overlaps(entry.region) and entry.clip.overlaps(entry.region)]
        regions.sort(key=itemgetter(0), reverse=True)
        return {widget: (region, clip) for _, widget, region, clip in regions}

    def _arrange_root(
        self, root: Widget, size: Size, visible_only: bool = True,
        retain_geometry: Iterable[Widget] = (),
        *, root_geometry: MapGeometry | None = None,
    ) -> tuple[CompositorMap, set[Widget]]:
        """Arrange a widget's children based on its layout attribute.

        Args:
            root: Top level widget.
            size: Size of visible area (screen).
            visible_only: Only update visible widgets (used in scrolling).
            root_geometry: Original placement when arranging a complete body.

        Returns:
            Compositor map and set of widgets.
        """

        map: CompositorMap = {}
        # Transient declaration paths manufacture the one retained resource.
        # The published MapGeometry continues to own the actual clipped scene.
        clips: dict[Widget, SceneClip] = {}
        screen_coordinates: set[Widget] = set()

        def store_geometry(node: Widget, geometry: MapGeometry, clip: SceneClip) -> None:
            map[node] = geometry
            clips[node] = clip

        widgets: set[Widget] = set()
        invisible_widgets: set[Widget] = set()
        if root_geometry is None:
            root_geometry = MapGeometry(
                size.region, ((0, 0, 0),), size.region,
                size, size, size.region, NULL_SPACING,
            )
        layer_order = root_geometry.order[-1][2]
        no_clip = RootSceneClip(root_geometry.region)
        # Layer names normally inherit from the outermost declaring ancestor.
        # Resolve that once per node for this reflow, instead of rebuilding an
        # ancestors list and a layer dictionary for every nested widget.
        inherited_layers: dict[Widget, dict[str, int] | None] = {}
        default_layers = {"default": 0}
        retained_paths: set[Widget] = set()
        if visible_only:
            for target in retain_geometry:
                path: list[Widget] = []
                node = target
                # Existing members already own a path to this same root.
                # Shared ancestors need admission once, not per target.
                while (
                    isinstance(node, Widget)
                    and node is not root
                    and node not in retained_paths
                ):
                    path.append(node)
                    node = node.parent
                if node is root or node in retained_paths:
                    retained_paths.update(path)

        def get_layers(widget: Widget) -> dict[str, int] | None:
            if widget in inherited_layers:
                return inherited_layers[widget]
            parent = widget.parent
            layers = get_layers(parent) if isinstance(parent, Widget) else None  # noqa: F821 -- closure cleared only after traversal
            if layers is None and widget.styles.has_rule("layers"):
                layers = {name: index for index, name in enumerate(widget.styles.layers)}
            inherited_layers[widget] = layers
            return layers

        def arrange_widget(
            widget: Widget,
            virtual_region: Region,
            region: Region,
            order: tuple[tuple[int, int, int], ...],
            layer_order: int,
            clip: SceneClip,
            visible: bool,
            dock_gutter: Spacing,
            complete: bool,
            _MapGeometry: type[MapGeometry] = MapGeometry,
        ) -> None:
            """Called recursively to place a widget and its children in the map.

            Args:
                widget: The widget to add.
                virtual_region: The Widget region relative to its container.
                region: The region the widget will occupy.
                order: Painting order information.
                layer_order: The order of the widget in its layer.
                clip: The clipping region (i.e. the viewport which contains it).
                visible: Whether the widget should be visible by default.
                    This may be overridden by the CSS rule `visibility`.
            """
            if not widget._is_mounted:
                return
            styles = widget.styles

            if (visibility := styles.get_rule("visibility")) is not None:
                visible = visibility == "visible"

            if visible:
                widgets.add(widget)
            else:
                invisible_widgets.add(widget)

            # Container region is minus border
            container_region = region.shrink(styles.gutter)
            container_size = container_region.size

            # Widgets with scrollbars (containers or scroll view) require additional processing
            if widget.is_scrollable:
                # The region that contains the content (container region minus scrollbars)
                child_region = (
                    container_region
                    if widget.loading
                    else widget._get_scrollable_region(container_region)
                )

                # The region covered by children relative to parent widget
                total_region = child_region.reset_offset

                if widget.is_container:
                    # Arrange the layout
                    arrange_result = widget.arrange(child_region.size)

                    # Original arrangement ordinals survive spatial admission.
                    # Do not rebuild ranks for every offscreen child on scroll.
                    first_layer_order = layer_order - len(arrange_result.placements) + 1

                    arranged_widgets = arrange_result.widgets
                    widgets.update(arranged_widgets)

                    # Get the region that will be updated
                    sub_clip = clip.intersect(child_region)

                    if widget._anchored and not widget._anchor_released:
                        new_scroll_y = (
                            arrange_result.spatial_map.total_region.bottom
                            - (
                                widget.container_size.height
                                - widget.scrollbar_size_horizontal
                            )
                        )
                        widget.set_reactive(Widget.scroll_y, new_scroll_y)
                        widget.set_reactive(Widget.scroll_target_y, new_scroll_y)
                        widget.vertical_scrollbar._reactive_position = new_scroll_y

                    if visible_only and not complete:
                        placements = arrange_result.get_visible_placements(
                            sub_clip.region - child_region.offset + widget.scroll_offset,
                            retain=retained_paths,
                        )
                    else:
                        placements = arrange_result.placements
                    total_region = total_region.union(arrange_result.total_region)

                    # An offset added to all placements
                    placement_offset = container_region.offset
                    placement_scroll_offset = placement_offset - widget.scroll_offset

                    screen_coordinates.update(placement.widget for _, placement in placements
                                              if placement.widget.uses_screen_coordinates)
                    placements = [
                        (ordinal, placement.process_offset(size.region, placement_scroll_offset))
                        for ordinal, placement in placements
                    ]

                    if type(widget).layers is Widget.layers:
                        resolved_layers = get_layers(widget)  # noqa: F821 -- closure cleared only after traversal
                        layers_to_index = default_layers if resolved_layers is None else resolved_layers
                    else:
                        # Preserve custom widget layer policies.
                        layers_to_index = {
                            layer_name: index
                            for index, layer_name in enumerate(widget.layers)
                        }

                    get_layer_index = layers_to_index.get

                    if widget._cover_widget is not None:
                        store_geometry(widget._cover_widget, _MapGeometry(
                            region.shrink(widget.styles.gutter),
                            order,
                            clip.region,
                            region.size,
                            container_size,
                            virtual_region,
                            dock_gutter,
                        ), clip)

                    # Add all the widgets
                    for ordinal, (
                        sub_region,
                        sub_region_offset,
                        _,
                        sub_widget,
                        z,
                        fixed,
                        overlay,
                        absolute,
                    ) in reversed(placements):
                        layer_index = get_layer_index(sub_widget.layer, 0)
                        # Combine regions with children to calculate the "virtual size"
                        if fixed:
                            widget_region = (
                                sub_region + sub_region_offset + placement_offset
                            )
                        else:
                            widget_region = (
                                sub_region + sub_region_offset + placement_scroll_offset
                            )

                        child_layer_order = first_layer_order + ordinal
                        widget_order = order + ((layer_index, z, child_layer_order),)

                        if widget._cover_widget is None:
                            add_widget(  # noqa: F821 -- closure cleared only after traversal
                                sub_widget,
                                sub_region,
                                widget_region,
                                ((1, 0, 0),) if overlay else widget_order,
                                child_layer_order,
                                no_clip if overlay else sub_clip,
                                visible,
                                arrange_result.scroll_spacing,
                                complete,
                            )
                else:
                    if widget._anchored and not widget._anchor_released:
                        new_scroll_y = widget.virtual_size.height - (
                            widget.container_size.height
                            - widget.scrollbar_size_horizontal
                        )
                        widget.scroll_y = new_scroll_y
                        widget.scroll_target_y = new_scroll_y
                        widget.vertical_scrollbar.position = new_scroll_y

                if visible:
                    # Add any scrollbars
                    if (
                        widget.show_vertical_scrollbar
                        or widget.show_horizontal_scrollbar
                    ) and styles.scrollbar_visibility == "visible":
                        for chrome_widget, chrome_region in widget._arrange_scrollbars(
                            container_region
                        ):
                            store_geometry(chrome_widget, _MapGeometry(
                                chrome_region,
                                order,
                                clip.region,
                                container_size,
                                container_size,
                                chrome_region - container_region.offset,
                                dock_gutter,
                            ), clip)

                    store_geometry(widget._render_widget, _MapGeometry(
                        region,
                        order,
                        clip.region,
                        total_region.size,
                        container_size,
                        virtual_region,
                        dock_gutter,
                    ), clip)

            elif visible:
                # Add the widget to the map
                store_geometry(widget._render_widget, _MapGeometry(
                    region,
                    order,
                    clip.region,
                    region.size,
                    container_size,
                    virtual_region,
                    dock_gutter,
                ), clip)

        def add_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter, complete):
            nonlocal map, widgets, invisible_widgets
            if (not self.max_subtree_geometry_entries or not widget.CACHE_SUBTREE_GEOMETRY
                    or not widget._is_mounted):
                arrange_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter, complete)  # noqa: F821 -- closure cleared after traversal
                return
            inherited = get_layers(widget)  # noqa: F821 -- closure cleared after traversal
            resource_type = widget.subtree_geometry_resource()
            complete = resource_type.complete_arrangement(complete)
            # Retention requires an uncropped path only for partial resources.
            # Complete native arrangements already own every descendant box.
            if widget in retained_paths and not complete:
                arrange_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter,
                               complete)  # noqa: F821 -- closure cleared after traversal
                return
            key = SubtreeGeometryKey.from_widget(widget,
                   virtual_region, region, order, layer_order, clip.region, visible, dock_gutter,
                   size, visible_only and not complete,
                   tuple(inherited.items()) if inherited is not None else ())
            cached = self._subtree_geometry.get(widget)
            if cached is not None and cached.matches(key):
                cached.restore_into(map, widgets, invisible_widgets, key, clip, clips, widget._render_widget)
                return
            # A body needs its complete native arrangement to reveal new rows.
            # A scroll-owning viewport changes its own arrangement inputs and
            # must continue culling; it cannot demand the entire prepared buffer
            # merely to retain an exact-coordinate scene.
            # Construct only this native subtree, then publish it into its
            # enclosing scene. Copying and subtracting the already-built whole
            # scene for each body makes admission depend on unrelated bodies.
            parent_map, parent_widgets, parent_invisible = map, widgets, invisible_widgets
            map, widgets, invisible_widgets = {}, set(), set()
            try:
                arrange_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter,
                               complete)  # noqa: F821 -- closure cleared after traversal
                geometry = map
                added_widgets, added_invisible = frozenset(widgets), frozenset(invisible_widgets)
            finally:
                map, widgets, invisible_widgets = parent_map, parent_widgets, parent_invisible
            map.update(geometry)
            widgets.update(added_widgets)
            invisible_widgets.update(added_invisible)
            if (widget not in self._subtree_geometry
                    and len(self._subtree_geometry) >= self.max_subtree_geometry_entries):
                self._subtree_geometry.pop(next(iter(self._subtree_geometry)))
            self._subtree_geometry[widget] = resource_type.capture(
                key, geometry, added_widgets, added_invisible, clips, clip, screen_coordinates)

        # Add top level (root) widget
        self._arranging = True
        try:
            add_widget(
                root,
                root_geometry.virtual_region,
                root_geometry.region,
                root_geometry.order,
                layer_order,
                no_clip,
                True,
                root_geometry.dock_gutter,
                False,
            )
        finally:
            self._arranging = False
            # Both recursive closures otherwise retain themselves through
            # their closure cells, keeping old maps and entire widget trees
            # alive until cyclic GC. Reflow is finished, so break those local
            # recursion links before returning the authoritative scene map.
            del add_widget, arrange_widget, get_layers
        widgets -= invisible_widgets
        return map, widgets

    @property
    def layers(self) -> list[tuple[Widget, MapGeometry]]:
        """Get widgets and geometry in layer order."""
        map = self._visible_map if self._visible_map is not None else self._full_map
        if self._layers is None:
            self._layers = sorted(
                map.items(), key=lambda item: item[1].order, reverse=True
            )
        return self._layers

    @property
    def layers_visible(self) -> list[list[tuple[Widget, Region, Region]]]:
        """Visible widgets and regions in layers order.

        Returns:
            Lists visible widgets per layer. Widgets are give as a tuple of
            (WIDGET, CROPPED_REGION, REGION). CROPPED_REGION is clipped by
            the container.

        """

        if self._layers_visible is None:
            layers_visible: list[list[tuple[Widget, Region, Region]]]
            layers_visible = [[] for y in range(self.size.height)]
            layers_visible_appends = [layer.append for layer in layers_visible]
            intersection = Region.intersection
            _range = range
            for widget, (region, clip) in self.visible_widgets.items():
                cropped_region = intersection(region, clip)
                _x, region_y, _width, region_height = cropped_region
                if region_height:
                    widget_location = (widget, cropped_region, region)
                    for y in _range(region_y, region_y + region_height):
                        layers_visible_appends[y](widget_location)
            self._layers_visible = layers_visible
        return self._layers_visible

    def __contains__(self, widget: Widget) -> bool:
        """Check if the widget was included in the last update.

        Args:
            widget: A widget.

        Returns:
            `True` if the widget was in the last refresh, or `False` if it wasn't.
        """
        # Try to avoid a recalculation of full_map if possible.
        return (
            widget in self.widgets
            or (self._visible_map is not None and widget in self._visible_map)
            or widget in self.full_map
        )

    def get_offset(self, widget: Widget) -> Offset:
        """Get the offset of a widget.

        Args:
            widget: Widget to query.

        Returns:
            Offset of widget.
        """
        try:
            if self._visible_map is not None:
                try:
                    return self._visible_map[widget].region.offset
                except KeyError:
                    pass
            return self.full_map[widget].region.offset
        except KeyError:
            raise errors.NoWidget("Widget is not in layout")

    def get_widget_at(self, x: int, y: int) -> tuple[Widget, Region]:
        """Get the widget under a given coordinate.

        Args:
            x: X Coordinate.
            y: Y Coordinate.

        Raises:
            errors.NoWidget: If there is not widget underneath (x, y).

        Returns:
            A tuple of the widget and its region.
        """

        contains = Region.contains
        if len(self.layers_visible) > y >= 0:
            for widget, cropped_region, region in self.layers_visible[int(y)]:
                if contains(cropped_region, x, y) and widget.visible:
                    return widget, region
        raise errors.NoWidget(f"No widget under screen coordinate ({x}, {y})")

    def get_widgets_at(self, x: int, y: int) -> Iterable[tuple[Widget, Region]]:
        """Get all widgets under a given coordinate.

        Args:
            x: X coordinate.
            y: Y coordinate.

        Returns:
            Sequence of (WIDGET, REGION) tuples.
        """
        contains = Region.contains
        if len(self.layers_visible) > y >= 0:
            for widget, cropped_region, region in self.layers_visible[y]:
                if contains(cropped_region, x, y) and widget.visible:
                    yield widget, region

    def get_style_at(self, x: int, y: int) -> Style:
        """Get the Style at the given cell or Style.null()

        Args:
            x: X position within the Layout.
            y: Y position within the Layout.

        Returns:
            The Style at the cell (x, y) within the Layout.
        """
        try:
            widget, region = self.get_widget_at(x, y)
        except errors.NoWidget:
            return Style.null()
        if widget not in self.visible_widgets:
            return Style.null()

        x -= region.x
        y -= region.y

        visible_screen_stack.set(widget.app._background_screens)
        lines = widget.render_lines(Region(0, y, region.width, 1))

        if not lines:
            return Style.null()
        end = 0

        for segment in lines[0]:
            end += segment.cell_length
            if x < end:
                return segment.style or Style.null()

        return Style.null()

    def get_widget_and_offset_at(
        self, x: int, y: int
    ) -> tuple[Widget | None, Offset | None]:
        """Get the Style at the given cell, the offset within the content.

        Args:
            x: X position within the Layout.
            y: Y position within the Layout.

        Returns:
            A tuple of the widget at (x, y) and the offset within the widget.
        """
        try:
            widget, region = self.get_widget_at(x, y)
        except errors.NoWidget:
            return None, None
        if widget not in self.visible_widgets:
            return None, None

        if y >= widget.content_region.bottom:
            x, y = widget.content_region.bottom_right_inclusive

        gutter_left, gutter_right = widget.gutter.top_left
        x -= region.x + gutter_left
        y -= region.y + gutter_right

        if x < 0 or y < 0:
            return widget, Offset(max(0, x), max(0, y))

        visible_screen_stack.set(widget.app._background_screens)
        line = widget.render_line(y)

        end = 0
        start = 0
        offset_y: int | None = None
        offset_x = 0
        offset_x2 = 0

        from rich.cells import get_character_cell_size

        offset: Offset | None = None
        for segment in line:
            end += segment.cell_length
            style = segment.style
            if style is not None and style._meta is not None:
                meta = style.meta
                if "offset" in meta:
                    offset_x, offset_y = meta["offset"]
                    if offset_y is None:
                        continue
                    offset_x2 = offset_x + len(segment.text)

                    if x < end and x >= start:
                        segment_cell_length = 0
                        cell_cut = x - start
                        segment_offset = 0
                        for character in segment.text:
                            if segment_cell_length >= cell_cut:
                                break
                            segment_cell_length += get_character_cell_size(character)
                            segment_offset += 1

                        offset = Offset(offset_x + segment_offset, offset_y)
                        break
            start = end

        if offset is None and offset_y is not None:
            offset = Offset(offset_x2, offset_y)
        return widget, offset

    def find_widget(self, widget: Widget) -> MapGeometry:
        """Get information regarding the relative position of a widget in the Compositor.

        Args:
            widget: The Widget in this layout you wish to know the Region of.

        Raises:
            NoWidget: If the Widget is not contained in this Layout.

        Returns:
            Widget's composition information.
        """
        geometry = self._get_geometry(widget)
        if geometry is None:
            geometry = self.full_map.get(widget)
        if geometry is None:
            raise errors.NoWidget("Widget is not in layout")
        return geometry

    def _get_geometry(self, widget: Widget) -> MapGeometry | None:
        """Select geometry from its original current publication.

        Capture consumes this publication; ordinary find_widget may arrange
        missing geometry. An invalidated full map cannot override the viewport.
        A missing capture descendant cannot escape to another scene.
        """
        if self._render_geometry is not None:
            root, geometry = self._render_geometry
            if root in widget.ancestors_with_self:
                placement = geometry.get(widget)
                if placement is None:
                    raise errors.NoWidget("Widget is not in layout")
                return placement
        return self._get_published_geometry(widget)

    def _get_published_geometry(self, widget: Widget) -> MapGeometry | None:
        """Read the original scene placement without arranging or copying it."""
        if self.root is None:
            return None
        if not self._full_map_invalidated:
            geometry = self._full_map.get(widget)
            if geometry is not None:
                return geometry
        if self._visible_map is not None:
            geometry = self._visible_map.get(widget)
            if geometry is not None:
                return geometry
        return None

    @contextmanager
    def _using_geometry(self, root: Widget, geometry: CompositorMap) -> Iterator[None]:
        """Bind descendant queries to the same original capture arrangement.

        Rendering is synchronous. Keep only references to its existing root and
        map; never replace a published map or retain this resource after paint.
        Nested capture and failed renderers restore the previous selection.
        """
        previous = self._render_geometry
        self._render_geometry = root, geometry
        try:
            yield
        finally:
            self._render_geometry = previous

    @property
    def cuts(self) -> list[list[int]]:
        """Get vertical cuts.

        A cut is every point on a line where a widget starts or ends.

        Returns:
            A list of cuts for every line.
        """
        if self._cuts is not None:
            return self._cuts
        self._cuts = self._cuts_for_regions(self.size.region, self.visible_widgets)
        return self._cuts

    @staticmethod
    def _cuts_for_regions(bounds: Region, widgets: Mapping[Widget, tuple[Region, Region]]
                          ) -> list[list[int]]:
        """Derive chop boundaries from the original ordered paint regions."""
        cuts = [[bounds.x, bounds.right] for _ in range(bounds.height)]

        intersection = Region.intersection
        extend = list.extend

        for region, clip in widgets.values():
            x, y, region_width, region_height = intersection(intersection(region, clip), bounds)
            if region_width and region_height:
                region_cuts = (x, x + region_width)
                for cut in cuts[y - bounds.y : y - bounds.y + region_height]:
                    extend(cut, region_cuts)

        # Sort the cuts for each line
        return [sorted(set(line_cuts)) for line_cuts in cuts]

    def _get_renders(
        self, crop: Region | None = None,
        render_regions: Callable[[Region], Iterable[Region]] | None = None,
        *, widgets: Mapping[Widget, tuple[Region, Region]],
    ) -> Iterable[tuple[Region, Region, list[Strip]]]:
        """Get rendered widgets (lists of segments) in the composition.

        Args:
            crop: Region to crop to, or `None` for entire screen.
            render_regions: Select still-exposed damaged rows within each widget.

        Returns:
            An iterable of <region>, <clip region>, and <strips>
        """
        # If a renderable throws an error while rendering, the user likely doesn't care about the traceback
        # up to this point.
        _rich_traceback_guard = True

        _Region = Region

        if crop:
            crop_overlaps = crop.overlaps
            widget_regions = [
                (widget, region, clip)
                for widget, (region, clip) in widgets.items()
                if crop_overlaps(clip)
            ]
        else:
            widget_regions = [
                (widget, region, clip)
                for widget, (region, clip) in widgets.items()
            ]

        intersection = _Region.intersection
        for widget, region, clip in widget_regions:
            if crop is not None:
                # Partial updates only need the damaged rows. Keep horizontal
                # clip boundaries intact: compositor chops are aligned to those
                # cuts and may extend past the narrower dirty x span.
                clip = intersection(clip, _Region(clip.x, crop.y, clip.width, crop.height))
            visible_region = intersection(region, clip)
            if visible_region:
                regions = (
                    (visible_region,) if render_regions is None
                    else render_regions(visible_region)
                )
                for render_region in regions:
                    new_x, new_y, new_width, new_height = render_region
                    yield (
                        region,
                        render_region,
                        widget.render_lines(
                            _Region(
                                new_x - region.x,
                                new_y - region.y,
                                new_width,
                                new_height,
                            )
                        ),
                    )

    def render_update(
        self,
        full: bool = False,
        screen_stack: list[Screen] | None = None,
        simplify: bool = False,
    ) -> RenderableType | None:
        """Render an update renderable.

        Args:
            full: Perform a full update if `True`, otherwise a partial update.
            screen_stack: Screen stack list. Defaults to None.
            simplify: Simplify segments.

        Returns:
            A renderable for the update, or `None` if no update was required.
        """

        visible_screen_stack.set([] if screen_stack is None else screen_stack)
        screen_region = self.size.region
        if full or screen_region in self._dirty_regions:
            return self.render_full_update(simplify=simplify)
        else:
            return self.render_partial_update()

    def render_inline(
        self,
        size: Size,
        screen_stack: list[Screen] | None = None,
        clear: bool = False,
    ) -> RenderableType:
        """Render an inline update.

        Args:
            size: Inline size.
            screen_stack: Screen stack list. Defaults to None.
            clear: Also clear below the inline update (set when size decreases).

        Returns:
            A renderable.
        """
        visible_screen_stack.set([] if screen_stack is None else screen_stack)
        strips = self.render_strips(size)
        return InlineUpdate(strips, clear=clear)

    def render_full_update(self, simplify: bool = False) -> LayoutUpdate:
        """Render a full update.

        Args:
            simplify: Simplify the segments (combine contiguous segments).

        Returns:
            A LayoutUpdate renderable.
        """
        screen_region = self.size.region
        self._dirty_regions.clear()
        crop = screen_region
        chops = self._render_chops(crop, lambda y: True,
                                  widgets=self.visible_widgets, cuts=self.cuts,
                                  bounds=screen_region)
        render_strips: list[Iterable[Strip]]
        if simplify:
            # Simplify is done when exporting to SVG
            # It doesn't make things faster
            render_strips = [
                [Strip.join(chop.values()).simplify().discard_meta()] for chop in chops
            ]
        else:
            render_strips = [chop.values() for chop in chops]

        return LayoutUpdate(render_strips, screen_region)

    def render_partial_update(self) -> ChopsUpdate | None:
        """Render a partial update.

        Returns:
            A ChopsUpdate if there is anything to update, otherwise `None`.
        """
        screen_region = self.size.region
        update_regions = {
            damage for region in self._dirty_regions if (damage := region.intersection(screen_region))
        }
        self._dirty_regions.clear()
        if not update_regions:
            return None
        crop = Region.from_union(update_regions)
        spans = list(self._regions_to_spans(update_regions))
        is_rendered_line = {y for y, _, _ in spans}.__contains__
        chops = self._render_chops(crop, is_rendered_line,
                                  widgets=self.visible_widgets, cuts=self.cuts,
                                  bounds=screen_region)
        chop_ends = [cut_set[1:] for cut_set in self.cuts]
        return ChopsUpdate(chops, spans, chop_ends)

    def render_strips(self, size: Size | None = None) -> list[Strip]:
        """Render to a list of strips.

        Args:
            size: Size of render.

        Returns:
            A list of strips with the screen content.
        """
        if size is None:
            size = self.size
        chops = self._render_chops(size.region, lambda y: True,
                                  widgets=self.visible_widgets, cuts=self.cuts,
                                  bounds=self.size.region)
        render_strips = [Strip.join(chop.values()) for chop in chops[: size.height]]
        return render_strips

    def published_geometry(
        self, roots: Iterable[Widget],
    ) -> Iterator[tuple[Widget, MapGeometry]]:
        """Borrow the roots' original current placements without arranging.

        Unmounted or unpublished roots have no capture resource. Consume each
        placement synchronously before asynchronous preparation or pruning can
        change the scene; mounted custody alone does not establish layout.
        """
        for root in roots:
            if not root.is_mounted:
                continue
            geometry = self._get_published_geometry(root)
            if geometry is not None:
                yield root, geometry

    def render_subtree_strips(
        self, root: Widget, root_geometry: MapGeometry,
    ) -> tuple[Size, list[Strip]]:
        """Paint a body using its borrowed original published placement.

        The caller acquires the placement from published_geometry and consumes
        it before any await or DOM mutation. Capture never reacquires eligibility
        or manufactures a scene to decide whether a body can be retired. The
        same original arrangement/line/chop algorithm supplies complete rows
        without replacing any published map or constructing another compositor.
        """
        bounds = root_geometry.region
        geometry, _ = self._arrange_root(
            root, self.size, visible_only=False, root_geometry=root_geometry,
        )
        widgets = self._paint_regions(geometry, bounds)
        cuts = self._cuts_for_regions(bounds, widgets)
        with self._using_geometry(root, geometry):
            chops = self._render_chops(bounds, lambda y: True,
                                      widgets=widgets, cuts=cuts, bounds=bounds)
        return bounds.size, [Strip.join(chop.values()) for chop in chops]

    def _render_chops(
        self,
        crop: Region,
        is_rendered_line: Callable[[int], bool],
        *, widgets: Mapping[Widget, tuple[Region, Region]], cuts: list[list[int]],
        bounds: Region,
    ) -> Sequence[Mapping[int, Strip]]:
        """Render update 'chops'.

        Args:
            crop: Region to crop to.
            is_rendered_line: Callable to check if line should be rendered.
            bounds: Original screen or body bounds represented by the chops.

        Returns:
            Chops structure.
        """
        fromkeys = cast("Callable[[list[int]], dict[int, Strip | None]]", dict.fromkeys)
        chops: list[dict[int, Strip | None]]
        chops = [fromkeys(cut_set[:-1]) for cut_set in cuts]
        remaining = [len(line) for line in chops]

        def render_regions(region: Region) -> Iterable[Region]:
            """Request exposed chop spans, coalesced across adjacent rows.

            Parent backgrounds often have narrow margins beside foreground
            children. Dividing their whole width materializes and discards the
            covered segments. Resolve exposure before asking widgets to paint.
            """
            first, last = region.column_span
            runs: dict[tuple[int, int], int] = {}
            for y in region.line_range:
                row = y - bounds.y
                spans: set[tuple[int, int]] = set()
                if remaining[row] and is_rendered_line(y):
                    start_x = None
                    for x, value in chops[row].items():
                        if x < first:
                            continue
                        if x >= last:
                            break
                        if value is None:
                            if start_x is None:
                                start_x = x
                        elif start_x is not None:
                            spans.add((start_x, x))
                            start_x = None
                    if start_x is not None:
                        spans.add((start_x, last))
                for span in tuple(runs):
                    if span not in spans:
                        start_y = runs.pop(span)
                        left, right = span
                        yield Region(left, start_y, right - left, y - start_y)
                for span in spans:
                    runs.setdefault(span, y)
            for (left, right), start_y in runs.items():
                yield Region(left, start_y, right - left, region.bottom - start_y)

        cut_strips: Iterable[Strip]

        # Go through all the renders in reverse order and fill buckets with no render
        renders = self._get_renders(crop, render_regions, widgets=widgets)
        intersection = Region.intersection

        for region, clip, strips in renders:
            render_region = intersection(region, clip)
            render_x = render_region.x
            first_cut, last_cut = render_region.column_span

            for y, strip in zip(render_region.line_range, strips):
                if not is_rendered_line(y):
                    continue

                row = y - bounds.y
                chops_line = chops[row]
                final_cuts = [cut for cut in cuts[row] if (last_cut >= cut >= first_cut)]
                cut_strips = strip.divide([cut - render_x for cut in final_cuts[1:]])

                # Since we are painting front to back, the first segments for a cut "wins"
                get_chops_line = chops_line.get
                for cut, strip in zip(final_cuts, cut_strips):
                    if get_chops_line(cut) is None:
                        chops_line[cut] = strip
                        remaining[row] -= 1
        return cast("Sequence[Mapping[int, Strip]]", chops)

    def __rich__(self) -> StripRenderable:
        return StripRenderable(self.render_strips())

    def update_widgets(self, widgets: set[Widget]) -> None:
        """Update the given widgets in the composition.

        Args:
            widgets: Set of Widgets to update.
        """

        # If there are any *new* widgets we need to invalidate the full map
        if not self._full_map_invalidated and not widgets.issubset(
            self.visible_widgets.keys()
        ):
            self._full_map_invalidated = True

        regions: list[Region] = []
        add_region = regions.append
        get_widget = self.visible_widgets.__getitem__
        for widget in self.visible_widgets.keys() & widgets:
            region, clip = get_widget(widget)
            offset = region.offset
            intersection = clip.intersection
            for dirty_region in widget._exchange_repaint_regions():
                if update_region := intersection(dirty_region.translate(offset)):
                    add_region(update_region)

        self._dirty_regions.update(regions)
