"""

The compositor handles combining widgets into a single screen (i.e. compositing).

It also stores the results of that process, so that Textual knows the widgets on
the screen and their locations. The compositor uses this information to answer
queries regarding the widget under an offset, or the style under an offset.

Additionally, the compositor can render portions of the screen which may have updated,
without having to render the entire screen.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from abc import ABC, abstractmethod
from bisect import bisect_left, bisect_right
from collections import Counter
from contextlib import contextmanager
from functools import cached_property
from fractions import Fraction
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    AbstractSet,
    Callable,
    Iterable,
    Iterator,
    Mapping,
    NamedTuple,
    Sequence,
    cast,
)

import rich.repr
from rich.console import Console, ConsoleOptions, RenderableType, RenderResult
from rich.control import Control
from rich.segment import Segment
from rich.style import Style

from textual import errors
from textual.box_model import BoxModel
from textual._context import visible_screen_stack
from textual._loop import loop_last
from textual._spatial_map import SpatialMap
from textual.geometry import NULL_OFFSET, NULL_SPACING, Offset, Region, Size, Spacing
from textual.map_geometry import MapGeometry
from textual.strip import Strip, StripRenderable
from textual.widget import Widget

if TYPE_CHECKING:
    from typing_extensions import TypeAlias

    from textual.screen import Screen


class ReflowResult(NamedTuple):
    """Logical show and hide membership after reflow."""

    hidden: set[Widget]  # Widgets that are hidden
    shown: set[Widget]  # Widgets that are shown


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
    parent: Widget | None
    """Original rendered parent within this capture, not the mutating DOM."""

    @property
    def region(self) -> Region:
        """The original placement bounds, before any destination projection."""
        return self.geometry.region

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


@dataclass(frozen=True)
class SubtreeGeometryPlacement:
    """A borrowed child source at its original acquired parent placement.

    The source retains its own geometry and lifetime. This edge owns only the
    placement, clip declaration and captured parent in the containing source.
    """

    source: SubtreeGeometry
    key: SubtreeGeometryKey
    clip: SceneClip
    parent: Widget | None = None
    clip_bounds: tuple[Region, ...] = ()
    source_held: bool = False
    """This edge borrows mutation-owned participation for one publication."""

    @property
    def region(self) -> Region:
        """All child bounds, including overflow outside the root rectangle."""
        return self.source._spatial_map.total_region + (
            self.key.region.offset - self.source.key.region.offset
        )


@dataclass(frozen=True)
class SubtreeGeometry(ABC):
    """One immutable native arrangement resource in the compositor's cache."""

    key: SubtreeGeometryKey
    geometry: Mapping[Widget, tuple[int, SubtreeMapGeometry | SubtreeGeometryPlacement]]
    """Ordered local placements and borrowed child sources, without flattening."""
    widgets: frozenset[Widget]
    invisible_widgets: frozenset[Widget]

    @classmethod
    def capture(cls, key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates):
        routes = cls._route_geometry(geometry)
        captured = {}
        for ordinal, (node, entry) in enumerate(geometry.items()):
            parent = node.parent
            parent = parent._render_widget if isinstance(parent, Widget) else None
            parent = parent if parent is not node and parent in routes else None
            if isinstance(entry, MapGeometry):
                entry = SubtreeMapGeometry(entry, (), parent)
            else:
                entry = (replace(entry, parent=parent) if isinstance(entry, SubtreeGeometryPlacement)
                         else entry._replace(parent=parent))
            captured[node] = ordinal, entry
        return cls(key, MappingProxyType(captured), widgets, invisible_widgets)

    @staticmethod
    def _route_geometry(geometry) -> Mapping[Widget, tuple[Widget, ...]]:
        """Index original geometry membership by its ordered borrowed edges.

        Logical and invisible membership do not imply a geometry placement.
        A widget may belong to multiple child sources; every edge remains in
        original order so projection keeps its last-assignment semantics.
        """
        routes: dict[Widget, list[Widget]] = {node: [] for node in geometry}
        for child, entry in geometry.items():
            if isinstance(entry, SubtreeGeometryPlacement):
                for node in entry.source._geometry_routes:
                    routes.setdefault(node, []).append(child)
        return MappingProxyType({node: tuple(children) for node, children in routes.items()})

    @cached_property
    def _geometry_routes(self) -> Mapping[Widget, tuple[Widget, ...]]:
        """Geometry routing belongs to this immutable source, not the DOM."""
        return self._route_geometry({node: entry for node, (_, entry) in self.geometry.items()})

    def contains(self, node: Widget) -> bool:
        """Membership in this acquired geometry, including borrowed children."""
        return node in self._geometry_routes

    def captured_parent(self, node: Widget) -> Widget | None:
        """The original parent edge, independent of the live child tree."""
        if (indexed := self.geometry.get(node)) is not None:
            entry = indexed[1]
            return (entry.parent if isinstance(entry, (SubtreeMapGeometry, SubtreeGeometryPlacement))
                    else None)
        if children := self._geometry_routes.get(node):
            entry = self.geometry[children[0]][1]
            return entry.source.captured_parent(node)
        raise errors.NoWidget("Widget is not in captured subtree")

    def members(self, *, invisible: bool = False) -> Iterator[Widget]:
        """Logical membership stays with each original source."""
        yield from self.invisible_widgets if invisible else self.widgets
        for _, entry in self.geometry.values():
            if isinstance(entry, SubtreeGeometryPlacement):
                yield from entry.source.members(invisible=invisible)

    @cached_property
    def reusable(self) -> bool:
        """Whether this immutable source can supply ordinary reuse.

        A captured loan needs fresh acquisition unless the containing mutation
        owner explicitly lends that original whole-source snapshot.
        """
        return all(
            not entry.source_held and entry.source.reusable
            for _, entry in self.geometry.values()
            if isinstance(entry, SubtreeGeometryPlacement)
        )

    @cached_property
    def complete(self) -> bool:
        """Complete acquisition includes the scope of every borrowed source."""
        return not self.key.visible_only and all(
            entry.source.complete for _, entry in self.geometry.values()
            if isinstance(entry, SubtreeGeometryPlacement)
        )

    @cached_property
    def _spatial_map(self) -> SpatialMap[tuple[int, Widget]]:
        """Derive spatial admission from this immutable arrangement, once."""
        spatial_map: SpatialMap[tuple[int, Widget]] = SpatialMap()
        spatial_map.insert(
            (entry.region, NULL_OFFSET, False, False, (ordinal, node))
            for node, (ordinal, entry) in self.geometry.items()
        )
        return spatial_map

    def matches(self, key: SubtreeGeometryKey, *, require_complete: bool = False,
                source_held: bool = False,
                required_geometry: Iterable[Widget] = ()) -> bool:
        if not self.reusable and not source_held:
            return False
        if require_complete and not self.complete:
            return False
        if source_held:
            # Original source custody owns revisions during the write. Size,
            # internal scrolling, layers and destination placement still agree.
            key = key._replace(geometry_revision=self.key.geometry_revision,
                               nodes_revision=self.key.nodes_revision)
        if self.complete and key.visible_only:
            key = key._replace(visible_only=False)
        if not self._matches_placement(key):
            return False
        # A position demand needs its original placed answer, not every
        # offscreen descendant. A complete source also owns absent answers;
        # an incomplete source must contain each explicitly requested target.
        return self.complete or all(self.contains(node) for node in required_geometry)

    @abstractmethod
    def _matches_placement(self, key: SubtreeGeometryKey) -> bool: ...

    def restore_into(
        self, geometry: CompositorMap, widgets: set[Widget], invisible_widgets: set[Widget],
        key: SubtreeGeometryKey, clip: SceneClip, clips: dict[Widget, SceneClip],
        root: Widget, *, visible_only: bool, retained: AbstractSet[Widget], bounds: Region,
        source_held: bool = False,
    ) -> None:
        self.project_into(geometry, key, clip, clips, root,
                          visible_only=visible_only, retained=retained, bounds=bounds,
                          source_held=source_held)
        widgets.update(node for node in self.members() if not node._pruning)
        invisible_widgets.update(node for node in self.members(invisible=True) if not node._pruning)

    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
                     clip: SceneClip, clips: dict[Widget, SceneClip], root: Widget,
                     *, visible_only: bool, retained: AbstractSet[Widget], bounds: Region,
                     source_held: bool = False, require_root: bool = True) -> None:
        """Publish the requested scene without retiring complete source geometry.

        A viewport needs exposed descendants and its explicit geometry targets.
        Complete capture and ordinary full-map acquisition still consume every
        entry. Both newly captured and reused resources publish through here.
        """
        source_bounds = bounds - (key.region.offset - self.key.region.offset)
        child_demands: dict[Widget, set[Widget]] = {}
        if visible_only:
            candidates = dict(self._spatial_map.get_values_in_region(source_bounds))
            if (indexed_root := self.geometry.get(root)) is not None:
                candidates[indexed_root[0]] = root
            # Captured membership scopes this source's demands. Unrelated
            # retained paths must not be rediscovered in every borrowed child.
            for node in (retained & self._geometry_routes.keys() if retained else ()):
                if (indexed := self.geometry.get(node)) is not None:
                    candidates[indexed[0]] = node
                    if isinstance(indexed[1], SubtreeGeometryPlacement):
                        child_demands.setdefault(node, set()).add(node)
                else:
                    # Route once through captured membership. Children receive
                    # their own demands, never the unrelated global path set.
                    # More than one edge may contain an original widget; keep
                    # source order and its original last-assignment semantics.
                    for child in self._geometry_routes.get(node, ()):
                        ordinal = self.geometry[child][0]
                        candidates[ordinal] = child
                        child_demands.setdefault(child, set()).add(node)
            entries = ((node, self.geometry[node][1])
                       for _, node in sorted(candidates.items()))
        else:
            entries = ((node, entry) for node, (_, entry) in self.geometry.items())
        no_demand: set[Widget] = set()
        for node, entry in self._paint_entries(entries, source_held=source_held):
            # The source can outlive its cache entry. Original prune admission
            # still retires native participation before pump teardown.
            if node._pruning:
                continue
            required = not visible_only or (node is root and require_root) or node in retained
            if isinstance(entry, SubtreeGeometryPlacement):
                child_key, child_clip = self._project_child(entry, key, clip)
                entry.source.project_into(
                    geometry, child_key, child_clip, clips, node,
                    visible_only=visible_only, retained=child_demands.get(node, no_demand), bounds=bounds,
                    source_held=source_held or entry.source_held, require_root=required,
                )
                continue
            # Clip intersection can only reduce these original rectangle bounds.
            # Reject an offscreen, unrequired entry before resolving its clip
            # chain, descendant rank and destination MapGeometry allocation.
            if not required and not entry.region.overlaps(source_bounds):
                continue
            placement, node_clip = self._project_entry(entry, key, clip, root=node is root)
            if required or placement.visible_region.overlaps(bounds):
                geometry[node] = placement
                clips[node] = node_clip

    def _paint_entries(self, entries, *, source_held: bool):
        """Retained self-paint follows the source's original captured ancestry."""
        if not source_held:
            return entries
        participation: dict[Widget, bool] = {}

        def participates(node: Widget) -> bool:
            if node not in participation:
                parent = self.captured_parent(node)
                participation[node] = node._render_widget is node and (
                    parent is None or (parent.is_container and participates(parent))
                )
            return participation[node]

        return ((node, entry) for node, entry in entries if participates(node))

    def _project_child(self, entry: SubtreeGeometryPlacement, key: SubtreeGeometryKey,
                       clip: SceneClip) -> tuple[SubtreeGeometryKey, SceneClip]:
        """Opaque sources retain the original exact child placement."""
        return entry.key, entry.clip

    @abstractmethod
    def _project_entry(self, entry: SubtreeMapGeometry, key: SubtreeGeometryKey,
                       clip: SceneClip, *, root: bool) -> tuple[MapGeometry, SceneClip]:
        ...

    def references_retired(self, owner: Widget, retired: set[Widget]) -> bool:
        return (owner in retired or not self.geometry.keys().isdisjoint(retired)
                or not self.widgets.isdisjoint(retired)
                or not self.invisible_widgets.isdisjoint(retired)
                or any(isinstance(entry, SubtreeGeometryPlacement)
                       and entry.source.references_retired(node, retired)
                       for node, (_, entry) in self.geometry.items()))


@dataclass(frozen=True)
class PlacedSubtreeGeometry(SubtreeGeometry):
    """A culled or screen-dependent arrangement keeps its exact placement."""

    def _matches_placement(self, key: SubtreeGeometryKey) -> bool:
        return self.key == key

    def _project_entry(self, entry: SubtreeMapGeometry, key: SubtreeGeometryKey,
                       clip: SceneClip, *, root: bool) -> tuple[MapGeometry, SceneClip]:
        return entry.geometry, RootSceneClip(entry.geometry.clip)

@dataclass(frozen=True)
class IntrinsicSubtreeGeometry(SubtreeGeometry):
    """The same bounded resource, reusable under a new original outer clip."""

    @classmethod
    def capture(cls, key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates):
        if key.visible_only or not (widgets | invisible_widgets).isdisjoint(screen_coordinates):
            return PlacedSubtreeGeometry.capture(
                key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates)
        intrinsic = {}
        origin = key.region.offset
        for node, entry in geometry.items():
            child = isinstance(entry, SubtreeGeometryPlacement)
            scope, bounds = (entry.clip if child else clips[node]).relative_bounds(clip, origin)
            if child and not isinstance(entry.source, IntrinsicSubtreeGeometry):
                # A child whose source retains exact screen placement cannot
                # authorize translation of its containing resource.
                return PlacedSubtreeGeometry.capture(
                    key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates)
            if scope is not clip:
                return PlacedSubtreeGeometry.capture(
                    key, geometry, widgets, invisible_widgets, clips, clip, screen_coordinates)
            intrinsic[node] = (
                replace(entry, clip_bounds=bounds) if child
                else SubtreeMapGeometry(entry, bounds, None)
            )
        return super().capture(key, intrinsic, widgets, invisible_widgets,
                               clips, clip, screen_coordinates)

    def _matches_placement(self, key: SubtreeGeometryKey) -> bool:
        return self.key.intrinsic() == key.intrinsic()

    def _project_entry(self, entry: SubtreeMapGeometry, key: SubtreeGeometryKey,
                       clip: SceneClip, *, root: bool) -> tuple[MapGeometry, SceneClip]:
        return entry.project(self.key, key, clip, root=root)

    def _project_child(self, entry, key, clip):
        for bound in entry.clip_bounds:
            clip = clip.intersect(bound + key.region.offset)
        offset = key.region.offset - self.key.region.offset
        return entry.key._replace(
            region=entry.key.region + offset,
            order=self.key.project_order(entry.key.order, key),
            layer_order=entry.key.layer_order + key.layer_order - self.key.layer_order,
            clip=clip.region,
        ), clip

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

    @classmethod
    def from_chops(cls, update: ChopsUpdate, height: int) -> InlineUpdate:
        """Use inline-relative cursor movement for the original admitted cells."""
        rows: list[list[Segment]] = [[] for _ in range(height)]
        cursors = [0] * height
        for y, x1, x2 in update.spans:
            for x, strip in update._get_line_chops(y, x1, x2):
                rows[y].append(Control.move(x - cursors[y]).segment)
                rows[y].extend(strip)
                cursors[y] = x + strip.cell_length
        return cls([Strip(row) for row in rows])

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
        cuts: list[list[int]],
    ) -> None:
        """A renderable which updates chops (fragments of lines).

        Args:
            chops: A mapping of offsets to list of segments, per line.
            spans: Original damaged screen spans.
            cuts: Original compositor cut boundaries for each line.
        """
        self.chops = chops
        self.spans = spans
        self.cuts = cuts

    @staticmethod
    def _span_cuts(
        spans: Iterable[tuple[int, int, int]], cuts: list[list[int]], y_origin: int,
    ) -> Iterator[tuple[int, int, int]]:
        """Select original cut cells touched by damage, including wide edges.

        Paint admission and both publication formats use the same cells. A
        span inside a cell still requires that whole strip before final crop.
        """
        for y, x1, x2 in spans:
            line_cuts = cuts[y - y_origin]
            first = max(0, bisect_right(line_cuts, x1) - 1)
            last = bisect_left(line_cuts, x2)
            for index in range(first, last):
                yield y, line_cuts[index], line_cuts[index + 1]

    def _get_line_chops(self, y: int, x1: int, x2: int) -> Iterator[tuple[int, Strip]]:
        """Clip the original painted chops once for either publication format.

        Strip owns cell splitting, including wide characters and metadata.
        Borrow the original cuts instead of copying ends for every screen row.
        """
        for _, x, end in self._span_cuts(((y, x1, x2),), self.cuts, 0):
            strip = self.chops[y].get(x)
            if strip is None:
                continue
            left, right = max(x, x1), min(end, x2)
            if left < right:
                yield left, strip.crop(left - x, right - x)

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        move_to = Control.move_to
        new_line = Segment.line()
        last_y = self.spans[-1][0]
        for y, x1, x2 in self.spans:
            for x, strip in self._get_line_chops(y, x1, x2):
                yield move_to(x, y).segment
                yield from strip

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
        last_y = self.spans[-1][0]

        for y, x1, x2 in self.spans:
            for x, strip in self._get_line_chops(y, x1, x2):
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
        self._layout_geometry: Mapping[Widget, MapGeometry | None] = {}
        """Borrowed mutation placements, only during synchronous arrangement."""
        self._render_exclusions: tuple[Region, ...] = ()
        """The acquired frame bounds, borrowed by translucent backdrop rendering."""
        self._render_geometry: tuple[Widget, CompositorMap] | None = None
        """The original arrangement selected by a synchronous body capture."""
        self._visible_map: CompositorMap | None = None
        self._layers: list[tuple[Widget, MapGeometry]] | None = None

        # All widgets considered in the arrangement
        # Note this may be a superset of self.full_map.keys() as some widgets may be invisible for various reasons
        self.widgets: set[Widget] = set()

        # Original widget origins and their bounded positive paint rectangles.
        self._visible_widgets: dict[Widget, tuple[Region, Region]] | None = None

        # The top level widget
        self.root: Widget | None = None

        # Dimensions of the arrangement
        self.size = Size(0, 0)

        # The points in each line where the line bisects the left and right edges of the widget
        self._cuts: list[list[int]] | None = None

        # Regions that require an update
        self._dirty_regions: set[Region] = set()

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

    def _invalidate_render_projection(self) -> None:
        """Retire layer and line projections of the original scene map."""
        self._visible_widgets = None
        self._layers = None
        self._cuts = None

    def clear(self) -> None:
        """Remove all references to widgets (used when the screen closes)."""
        self.root = None
        self._full_map.clear()
        self._full_map_invalidated = True
        self._visible_map = None
        self._invalidate_render_projection()
        self.widgets.clear()
        self._dirty_regions.clear()
        self._subtree_geometry.clear()

    def discard_widgets(self, widgets: set[Widget]) -> set[Widget]:
        """Retire original widgets, their covers and chrome, retaining damage.

        Maps and captured arrangements release paint before native teardown.
        """
        widgets = {
            member
            for owner in widgets
            for member in (owner, owner._render_widget, *owner._get_virtual_dom())
        }
        for owner, resource in tuple(self._subtree_geometry.items()):
            if resource.references_retired(owner, widgets):
                del self._subtree_geometry[owner]
        changed = False
        for mapping in (self._full_map, self._visible_map):
            if mapping is None:
                continue
            for widget in widgets:
                if (geometry := mapping.pop(widget, None)) is not None:
                    changed = True
                    if region := geometry.visible_region:
                        self._dirty_regions.add(region)
        self.widgets.difference_update(widgets)
        if changed:
            self._full_map_invalidated = True
            self._invalidate_render_projection()
        return widgets

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
        edges: dict[int, Counter[tuple[int, int]]] = {}
        for region_x, region_y, width, height in regions:
            if height > 0:
                span = (region_x, region_x + width)
                edges.setdefault(region_y, Counter())[span] += 1
                edges.setdefault(region_y + height, Counter())[span] -= 1

        active: Counter[tuple[int, int]] = Counter()
        spans: list[tuple[int, int]] = []
        previous_y = 0
        for y, changes in sorted(edges.items()):
            if spans:
                for row in range(previous_y, y):
                    for span in spans:
                        yield (row, *span)
            active.update(changes)
            spans = []
            for x1, x2 in sorted(active.elements()):
                if spans and x1 <= spans[-1][1]:
                    spans[-1] = (spans[-1][0], max(x2, spans[-1][1]))
                else:
                    spans.append((x1, x2))
            previous_y = y

    def __rich_repr__(self) -> rich.repr.Result:
        yield "size", self.size
        yield "widgets", self.widgets

    @property
    def _published_map(self) -> CompositorMap:
        """Last committed scene, including a legitimately empty viewport."""
        return self._visible_map if self._visible_map is not None else self._full_map

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
            Hidden and shown widgets.
        """
        previous_scene = self._published_map
        previous_map = previous_scene if visible_only else self._full_map
        self._invalidate_render_projection()
        self.root = parent
        self.size = size

        # Keep a copy of the old map because we're going to compare it with the update
        old_map = previous_map
        old_widgets = old_map.keys()

        map, widgets, _ = self._arrange_root(
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
            self._visible_map = None
        self._full_map_invalidated = visible_only
        # Measuring widgets may inspect geometry and populate presentation
        # caches from the previous committed map. Publish only the new map.
        self._invalidate_render_projection()
        self.widgets = widgets

        self._damage_geometry(previous_scene, map, parent)
        return ReflowResult(hidden=hidden_widgets, shown=shown_widgets)

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
        self._invalidate_render_projection()
        previous_scene = self._published_map
        self._full_map_invalidated = True
        self.root = parent
        self.size = size

        # Keep a copy of the old map because we're going to compare it with the update
        old_map = self._visible_map or {}
        map, widgets, _ = self._arrange_root(
            parent, size, visible_only=True, retain_geometry=retain_geometry,
        )

        # Replace map and widgets
        self._visible_map = map
        self._invalidate_render_projection()
        self.widgets = widgets

        exposed_widgets = map.keys() - old_map.keys()

        self._damage_geometry(previous_scene, map, parent)

        return exposed_widgets

    def _damage_geometry(
        self, before: Mapping[Widget, MapGeometry], after: Mapping[Widget, MapGeometry],
        owner: Widget,
    ) -> None:
        """Retain both paint rectangles from the original scene change.

        Compare each new placement with its previous one. Retain both clipped
        rectangles without hashing complete geometry records into temporary
        sets. Widget size publication owns resize notification separately.
        """
        if self.size.region in self._dirty_regions:
            owner.check_idle()
            return
        for widget, geometry in after.items():
            previous = before.get(widget)
            if previous == geometry:
                continue
            if previous is not None:
                if region := previous.visible_region:
                    self._dirty_regions.add(region)
            if region := geometry.visible_region:
                self._dirty_regions.add(region)
        for widget, geometry in before.items():
            if widget not in after and (region := geometry.visible_region):
                self._dirty_regions.add(region)
        if self._dirty_regions:
            owner.check_idle()

    @property
    def full_map(self) -> CompositorMap:
        """Lazily built compositor map that covers all widgets."""

        if self.root is None:
            return {}
        if self._full_map_invalidated and not self._arranging:
            map, _widgets, _ = self._arrange_root(self.root, self.size, visible_only=False)
            # A geometry query also publishes this scene. Retain the damage
            # from its original visible coordinates before replacing the map;
            # a later reflow can no longer recover that previous geometry.
            previous = self._published_map
            self._damage_geometry(previous, map, self.root)
            self._full_map = map
            self._full_map_invalidated = False
            self._visible_map = None
            self._invalidate_render_projection()

        return self._full_map

    @property
    def visible_widgets(self) -> dict[Widget, tuple[Region, Region]]:
        """Get widget origins and rectangles admitted to this original scene.

        Returns:
            Visible widget mapping.
        """

        if self._visible_widgets is None:
            self._visible_widgets = self._paint_regions(self.layers, self.size.region)
        return self._visible_widgets

    @staticmethod
    def _ordered_geometry(geometry: Mapping[Widget, MapGeometry]
                          ) -> list[tuple[Widget, MapGeometry]]:
        """Order the original screen or captured geometry front to back once."""
        return sorted(geometry.items(), key=lambda item: item[1].order, reverse=True)

    @staticmethod
    def _paint_regions(layers: Iterable[tuple[Widget, MapGeometry]], bounds: Region
                       ) -> dict[Widget, tuple[Region, Region]]:
        """Own each positive paint rectangle within the original scene bounds."""
        return {widget: (entry.region, paint_region)
                for widget, entry in layers
                if (paint_region := entry.visible_region.intersection(bounds))}

    def _arrange_root(
        self, root: Widget, size: Size, visible_only: bool = True,
        retain_geometry: Iterable[Widget] = (),
        *, root_geometry: MapGeometry | None = None,
        root_clip: SceneClip | None = None,
    ) -> tuple[CompositorMap, set[Widget], SubtreeGeometryPlacement | None]:
        """Arrange a widget's children based on its layout attribute.

        Args:
            root: Top level widget.
            size: Size of visible area (screen).
            visible_only: Only update visible widgets (used in scrolling).
            root_geometry: Original placement for explicit subtree acquisition.
            root_clip: Original outer clip, or complete body bounds for painting.

        Returns:
            Compositor map, logical members, and the explicitly acquired source.
        """

        mutation_sources = root.screen._layout_mutation_roots()
        mutation_roots = set(mutation_sources)
        previous = self._published_map
        held: dict[Widget, CompositorMap] = {owner: {} for owner in mutation_roots}
        mutation_paths: set[Widget] = set()
        for owner in mutation_roots:
            mutation_paths.update(owner.walk_ancestors(with_self=True))
        if mutation_roots:
            for node, geometry, owners in self._geometry_for_roots(mutation_roots):
                for owner in owners:
                    held[owner][node] = geometry
        for owner in mutation_paths - mutation_roots:
            self._subtree_geometry.pop(owner, None)
        map: dict[Widget, MapGeometry | SubtreeGeometryPlacement] = {}
        capturing_source = False
        capture_root = root_geometry is not None
        acquired: SubtreeGeometryPlacement | None = None
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
        # Screen overlays retain their original screen clip, even when a body
        # is acquired with expanded paint bounds or its own incoming clip.
        no_clip = RootSceneClip(size.region)
        incoming_clip = (root_clip if root_clip is not None else
                         RootSceneClip(root_geometry.region) if capture_root else no_clip)
        # Widget owns layer inheritance. Acquire external ancestry only at the
        # root, then carry that original declaration through this traversal.
        root_layers = root._get_layer_order(root.walk_ancestors(with_self=True))
        root_layer_order = (
            None if root_layers is None
            else {name: index for index, name in enumerate(root_layers)}
        )
        default_layers = {"default": 0}
        retained_paths: dict[Widget, set[Widget]] = {}
        if visible_only:
            # A held root still needs its new outer placement when scrolling
            # takes it offscreen. Its resource owns descendants; this acquires
            # only the ancestor path, not the mutating subtree's arrangement.
            for target in (*retain_geometry, *mutation_roots):
                path: list[Widget] = []
                node = target
                while isinstance(node, Widget) and node is not root:
                    path.append(node)
                    node = node.parent
                if node is root:
                    # The same acquired relation supplies path admission and
                    # the targets required within each source. Keys are routing
                    # ancestors, values are original requested positions.
                    for member in path:
                        retained_paths.setdefault(member, set()).add(target)

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
            inherited_layers: Mapping[str, int] | None,
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
                            retain=retained_paths.keys(),
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
                        layers_to_index = default_layers if inherited_layers is None else inherited_layers
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
                                inherited_layers,
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

        def add_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter, complete,
                       inherited_layers):
            nonlocal map, widgets, invisible_widgets, capturing_source, acquired
            if inherited_layers is None and (order_names := widget._get_layer_order((widget,))) is not None:
                inherited_layers = {name: index for index, name in enumerate(order_names)}
            if widget in held:
                placement = mutation_sources[widget]
                resource = placement.source if placement is not None else None
                key = SubtreeGeometryKey.from_widget(
                    widget, virtual_region, region, order, layer_order, clip.region,
                    visible, dock_gutter, size, False,
                    tuple(inherited_layers.items()) if inherited_layers is not None else (),
                )
                if resource is not None and resource.contains(widget._render_widget) and resource.matches(
                    key, require_complete=True, source_held=True,
                ):
                    if capture_root and widget is root:
                        acquired = SubtreeGeometryPlacement(resource, key, clip, source_held=True)
                    # Complete intrinsic geometry retains original descendants
                    # and clip declarations. Ancestor scrolling changes only
                    # their placement; no mutating DOM arrangement is read.
                    if capturing_source:
                        map[widget._render_widget] = SubtreeGeometryPlacement(
                            resource, key, clip, source_held=True
                        )
                    else:
                        resource.restore_into(
                            map, widgets, invisible_widgets, key, clip, clips,
                            widget._render_widget, visible_only=visible_only and not complete,
                            retained=retained_paths.keys(), bounds=root_geometry.region,
                            source_held=True,
                        )
                    # The complete resource has replaced these old viewport
                    # entries, including nested holds. Do not merge them back
                    # after projection and resurrect stale absolute placement.
                    for owner in held:
                        if resource.contains(owner):
                            held[owner].clear()
                else:
                    # Placed, resized or missing sources cannot authorize a
                    # projection. Keep their exact committed hit/paint bounds.
                    snapshot = held[widget]
                    if resource is not None and resource.complete:
                        # A changed destination refuses translation, not the
                        # original source's membership and self-paint lifetime.
                        # Filter the committed rectangles along captured parent
                        # edges; never infer ancestry from the changing DOM.
                        snapshot = dict(
                            resource._paint_entries(
                                ((node, geometry) for node, geometry in snapshot.items()
                                 if resource.contains(node)),
                                source_held=True,
                            )
                        )
                    if capturing_source:
                        # The published fallback is a partial placed source,
                        # not an invented complete or translatable subtree.
                        # Keep that lending scope on the same child edge.
                        partial_key = SubtreeGeometryKey.from_widget(
                            widget, virtual_region, region, order, layer_order,
                            clip.region, visible, dock_gutter, size, True,
                            tuple(inherited_layers.items()) if inherited_layers is not None else (),
                        )
                        source = PlacedSubtreeGeometry.capture(
                            partial_key, snapshot, frozenset(snapshot), frozenset(),
                            clips, clip, screen_coordinates,
                        )
                        map[widget._render_widget] = SubtreeGeometryPlacement(
                            source, partial_key, clip, source_held=True
                        )
                    else:
                        for node, geometry in snapshot.items():
                            store_geometry(node, geometry, RootSceneClip(geometry.clip))
                        widgets.update(snapshot)
                    # The filtered original membership replaces this held
                    # fallback; the outer merge must not resurrect old children.
                    held[widget].clear()
                return
            explicit_root = capture_root and widget is root
            cache_source = bool(self.max_subtree_geometry_entries and widget.CACHE_SUBTREE_GEOMETRY)
            if not explicit_root and (widget in mutation_paths or not cache_source or not widget._is_mounted):
                arrange_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter,
                               complete, inherited_layers)  # noqa: F821 -- closure cleared after traversal
                return
            resource_type = widget.subtree_geometry_resource()
            enclosing_complete = complete
            key = SubtreeGeometryKey.from_widget(widget,
                   virtual_region, region, order, layer_order, clip.region, visible, dock_gutter,
                   size, visible_only and not complete,
                   tuple(inherited_layers.items()) if inherited_layers is not None else ())
            resource = self._subtree_geometry.get(widget)
            matches = resource is not None and resource.matches(
                key, require_complete=explicit_root and not visible_only,
                required_geometry=retained_paths.get(widget, ()),
            )
            if not matches:
                # Capture this acquisition before its viewport publication.
                # Enclosing captures borrow the original child sources;
                # viewport acquisition includes exposed and requested boxes.
                parent_map, parent_widgets, parent_invisible, parent_capture = (
                    map, widgets, invisible_widgets, capturing_source
                )
                map, widgets, invisible_widgets = {}, set(), set()
                capturing_source = True
                try:
                    arrange_widget(widget, virtual_region, region, order, layer_order, clip, visible, dock_gutter,
                                   complete, inherited_layers)  # noqa: F821 -- closure cleared after traversal
                    geometry = map
                    added_widgets, added_invisible = frozenset(widgets), frozenset(invisible_widgets)
                finally:
                    map, widgets, invisible_widgets = parent_map, parent_widgets, parent_invisible
                    capturing_source = parent_capture
                resource = resource_type.capture(
                    key, geometry, added_widgets, added_invisible, clips, clip, screen_coordinates)
                if cache_source:
                    if (widget not in self._subtree_geometry
                            and len(self._subtree_geometry) >= self.max_subtree_geometry_entries):
                        self._subtree_geometry.pop(next(iter(self._subtree_geometry)))
                    self._subtree_geometry[widget] = resource
            if explicit_root:
                acquired = SubtreeGeometryPlacement(resource, key, clip)
            if capturing_source:
                # Retain the child source and its placement. A containing
                # capture does not consume a second flat copy of descendants.
                map[widget._render_widget] = SubtreeGeometryPlacement(resource, key, clip)
            else:
                resource.restore_into(map, widgets, invisible_widgets, key, clip, clips, widget._render_widget,
                                      visible_only=visible_only and not enclosing_complete,
                                      retained=retained_paths.keys(), bounds=root_geometry.region)

        # Add top level (root) widget
        previous_layout_geometry = self._layout_geometry
        self._layout_geometry = {
            owner: previous.get(owner._render_widget) for owner in mutation_roots
        }
        previous_arranging = self._arranging
        self._arranging = True
        try:
            add_widget(
                root,
                root_geometry.virtual_region,
                root_geometry.region,
                root_geometry.order,
                layer_order,
                incoming_clip,
                True,
                root_geometry.dock_gutter,
                False,
                root_layer_order,
            )
        finally:
            self._arranging = previous_arranging
            self._layout_geometry = previous_layout_geometry
            # Both recursive closures otherwise retain themselves through
            # their closure cells, keeping old maps and entire widget trees
            # alive until cyclic GC. Reflow is finished, so break those local
            # recursion links before returning the authoritative scene map.
            del add_widget, arrange_widget
        for geometry in held.values():
            map.update(geometry)
            widgets.update(geometry)
        widgets -= invisible_widgets
        return cast(CompositorMap, map), widgets, acquired

    @property
    def layers(self) -> list[tuple[Widget, MapGeometry]]:
        """Get widgets and geometry in layer order."""
        if self._layers is None:
            self._layers = self._ordered_geometry(self._published_map)
        return self._layers

    def __contains__(self, widget: Widget) -> bool:
        """Check if the widget was included in the last update.

        Args:
            widget: A widget.

        Returns:
            `True` if the widget was in the last refresh, or `False` if it wasn't.
        """
        if widget in self.widgets:
            return True
        try:
            self.find_widget(widget)
        except errors.NoWidget:
            return False
        return True

    def get_offset(self, widget: Widget) -> Offset:
        """Get the offset of a widget.

        Args:
            widget: Widget to query.

        Returns:
            Offset of widget.
        """
        return self.find_widget(widget).region.offset

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

        for hit in self.get_widgets_at(x, y):
            return hit
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
        held = () if self.root is None else tuple(
            root for root in self.root.screen._layout_mutation_roots()
            if any(region.contains(x, y) for region in self.deferred_regions((root,)))
        )
        if self.size.height > y >= 0:
            for widget, (region, clip) in self.visible_widgets.items():
                if contains(region, x, y) and contains(clip, x, y) and widget.visible:
                    if held and not (
                        set(widget.walk_ancestors(with_self=True)).intersection(held)
                        or any(widget in root.walk_ancestors(with_self=True) for root in held)
                    ):
                        continue
                    yield widget, region

    def _interaction_deferred(self, x: int, y: int) -> bool:
        """A geometry query cannot render held source to acquire metadata."""
        regions = self._render_exclusions
        if self.root is not None:
            regions += self.deferred_regions(self.root.screen._layout_mutation_roots())
        return any(region.contains(x, y) for region in regions)

    def get_style_at(self, x: int, y: int) -> Style:
        """Get the Style at the given cell or Style.null()

        Args:
            x: X position within the Layout.
            y: Y position within the Layout.

        Returns:
            The Style at the cell (x, y) within the Layout.
        """
        if self._interaction_deferred(x, y):
            return Style.null()
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
        if widget not in self.visible_widgets or self._interaction_deferred(x, y):
            return widget, None

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
            if self.acquire_geometry((widget,)):
                geometry = self._get_geometry(widget)
            else:
                # Measurement inside arrangement must not recursively arrange;
                # the original complete map remains its available prior scope.
                geometry = self.full_map.get(widget)
        if geometry is None:
            raise errors.NoWidget("Widget is not in layout")
        return geometry

    def acquire_subtree_geometry(self, root: Widget) -> SubtreeGeometryPlacement | None:
        """Acquire the complete original source before a mutation begins.

        The transaction retains this placement, independently of cache eviction.
        Nested acquisition lends existing held sources while arranging only the
        unmodified remainder. It never publishes or paints a replacement scene.
        An absent root or incomplete held source supplies no complete resource.
        """
        geometry = self._get_published_geometry(root)
        if geometry is None or self._arranging:
            return None
        # An enclosing held source owns this original member. Acquiring a new
        # descendant scope would read its changing DOM; the containing source
        # does not retain every descendant's independent arrangement inputs.
        # Expansion to an unmodified ancestor remains a complete acquisition.
        if any(
            owner is not root and placement is not None and placement.source.contains(root)
            for owner, placement in root.screen._layout_mutation_roots().items()
        ):
            return None
        _, _, placement = self._arrange_root(
            root, self.size, visible_only=False, root_geometry=geometry,
            root_clip=RootSceneClip(geometry.clip),
        )
        return placement if (placement is not None and placement.source.complete
                             and placement.source.contains(root._render_widget)) else None

    def acquire_geometry(self, widgets: Iterable[Widget]) -> bool:
        """Acquire missing reader paths in one original scene publication.

        A focus query requires offscreen ordering paths as well as visible
        placements. Keep the committed scene's readers and add the complete
        demand together, instead of reflowing for each missing position.
        Captured descendants retain their strict original arrangement boundary.
        Returns whether a viewport arrangement was performed.
        """
        if self.root is None or not self._full_map_invalidated or self._arranging:
            return False
        missing = []
        for widget in widgets:
            try:
                geometry = self._get_geometry(widget)
            except errors.NoWidget:
                # The ordinary reader still refuses an omitted descendant of
                # the active capture; this acquisition cannot widen its scope.
                continue
            if geometry is None:
                missing.append(widget)
        if not missing:
            return False
        self.reflow_visible(
            self.root, self.size, retain_geometry=(*self._published_map, *missing),
        )
        return True

    def _get_geometry(self, widget: Widget) -> MapGeometry | None:
        """Select geometry from its original current publication.

        Capture consumes this publication; ordinary find_widget may arrange
        missing geometry. An invalidated full map cannot override the viewport.
        A missing capture descendant cannot escape to another scene.
        """
        if self._render_geometry is not None:
            root, geometry = self._render_geometry
            # The original arrangement already admits its members, including
            # cover and scrollbar resources. Only a missing query needs its
            # ancestry to distinguish an omitted descendant from another scene.
            placement = geometry.get(widget)
            if placement is not None:
                return placement
            if root in widget.walk_ancestors(with_self=True):
                raise errors.NoWidget("Widget is not in layout")
        return self._get_published_geometry(widget)

    def _get_published_geometry(self, widget: Widget) -> MapGeometry | None:
        """Read the original scene placement without arranging or copying it."""
        if self.root is None:
            return None
        # Completeness invalidation does not retire committed coordinates.
        # Paint and hit readers already consume this exact scene; positions and
        # capture eligibility must not independently choose another map.
        return self._published_map.get(widget)

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
        """Derive cuts from the positive rectangles owned by paint admission."""
        cuts = [[bounds.x, bounds.right] for _ in range(bounds.height)]

        extend = list.extend

        for _, (x, y, region_width, region_height) in widgets.values():
            region_cuts = (x, x + region_width)
            for cut in cuts[y - bounds.y : y - bounds.y + region_height]:
                extend(cut, region_cuts)

        # Sort the cuts for each line
        return [sorted(set(line_cuts)) for line_cuts in cuts]

    def _get_renders(
        self, crop: Region | None = None,
        render_regions: Callable[[Region], Iterable[Region]] | None = None,
        *, widgets: Mapping[Widget, tuple[Region, Region]],
    ) -> Iterable[tuple[Region, list[Strip]]]:
        """Get rendered widgets (lists of segments) in the composition.

        Args:
            crop: Region to crop to, or `None` for entire screen.
            render_regions: Select still-exposed damaged rows within each widget.

        Returns:
            An iterable of original selected paint rectangles and their strips.
        """
        # If a renderable throws an error while rendering, the user likely doesn't care about the traceback
        # up to this point.
        _rich_traceback_guard = True

        _Region = Region
        intersection = _Region.intersection
        # The supplied paint mapping owns this synchronous ordered cohort.
        # Screen invalidation replaces that resource; it does not mutate it.
        # Capture supplies its own detached cohort. Neither needs another list
        # of all scene members before the first exposed row can be rendered.
        for widget, (region, clip) in widgets.items():
            if crop and not crop.overlaps(clip):
                continue
            if crop is not None:
                # Partial updates only need the damaged rows. Keep horizontal
                # clip boundaries intact: compositor chops are aligned to those
                # cuts and may extend past the narrower dirty x span.
                clip = intersection(clip, _Region(clip.x, crop.y, clip.width, crop.height))
            if clip:
                regions = (
                    (clip,) if render_regions is None
                    else render_regions(clip)
                )
                for render_region in regions:
                    new_x, new_y, new_width, new_height = render_region
                    yield (
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

    def _geometry_for_roots(
        self, roots: Iterable[Widget],
    ) -> Iterator[tuple[Widget, MapGeometry, frozenset[Widget]]]:
        """Read committed placements with their original current root membership.

        Share parent answers only during this synchronous traversal. Reading
        children instead would omit covers and native virtual widgets.
        """
        roots = set(roots)
        if not roots:
            return
        membership = {}
        for widget, geometry in self._published_map.items():
            path = []
            for ancestor in widget.walk_ancestors(with_self=True):
                if ancestor in membership:
                    held = membership[ancestor]
                    break
                path.append(ancestor)
            else:
                held = frozenset()
            for ancestor in reversed(path):
                if ancestor in roots:
                    held = held | {ancestor}
                membership[ancestor] = held
            if held:
                yield widget, geometry, held

    def deferred_regions(self, roots: Iterable[Widget]) -> tuple[Region, ...]:
        """Derive held paint bounds from committed geometry, never lazy layout.

        A mounted root without a placement holds its nearest placed ancestor:
        an unknown destination cannot authorize painting through that subtree.
        Overflowing descendants retain their own original clipped bounds.
        """
        roots = set(roots)
        if not roots:
            return ()
        regions: set[Region] = set()
        placed: set[Widget] = set()
        for _, geometry, owners in self._geometry_for_roots(roots):
            placed.update(owners)
            if region := geometry.visible_region.intersection(self.size.region):
                regions.add(region)
        for root in roots - placed:
            if not root.is_attached:
                continue
            for ancestor in root.walk_ancestors():
                if (geometry := self._published_map.get(ancestor)) is not None:
                    if region := geometry.visible_region.intersection(self.size.region):
                        regions.add(region)
                    break
            else:
                regions.add(self.size.region)
        return tuple(regions)

    @staticmethod
    def _exclude_regions(regions: Iterable[Region], exclusions: Iterable[Region]) -> set[Region]:
        """Partition original positive rectangles without changing cell coordinates."""
        result = set(regions)
        for exclusion in exclusions:
            remaining: set[Region] = set()
            for region in result:
                overlap = region.intersection(exclusion)
                if not overlap:
                    remaining.add(region)
                    continue
                for part in (
                    Region(region.x, region.y, region.width, overlap.y - region.y),
                    Region(region.x, overlap.bottom, region.width, region.bottom - overlap.bottom),
                    Region(region.x, overlap.y, overlap.x - region.x, overlap.height),
                    Region(overlap.right, overlap.y, region.right - overlap.right, overlap.height),
                ):
                    if part:
                        remaining.add(part)
            result = remaining
        return result

    @contextmanager
    def _using_exclusions(self, regions: tuple[Region, ...]) -> Iterator[None]:
        """Borrow the same frame admission for nested BackgroundScreen renders."""
        previous = self._render_exclusions
        self._render_exclusions = regions
        try:
            yield
        finally:
            self._render_exclusions = previous

    def _publication_cuts(self, exclusions: Iterable[Region]) -> list[list[int]]:
        """Held boundaries split cut cells before damage expands to native strips."""
        cuts = [line.copy() for line in self.cuts]
        for region in exclusions:
            region = region.intersection(self.size.region)
            for row in range(region.y, region.bottom):
                cuts[row] = sorted(set((*cuts[row], region.x, region.right)))
        return cuts

    def mutation_box(self, widget: Widget) -> BoxModel | None:
        """Borrow the committed root box; an unplaced mutation has no size yet."""
        if widget not in self._layout_geometry or not widget.is_attached:
            return None
        geometry = self._layout_geometry[widget]
        size = Size() if geometry is None else geometry.region.size
        return BoxModel(Fraction(size.width), Fraction(size.height), widget.styles.margin)

    def pending_for(self, widget: Widget) -> bool:
        """Whether this sender still owns damage in the original committed scene."""
        if not self._dirty_regions:
            return False
        regions = widget.screen._compositor.deferred_regions((widget,))
        return any(damage.overlaps(region) for damage in self._dirty_regions for region in regions)

    def render_update(
        self,
        full: bool = False,
        screen_stack: list[Screen] | None = None,
        simplify: bool = False,
        excluded_regions: tuple[Region, ...] = (),
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
        if full:
            self._dirty_regions.add(screen_region)
        if excluded_regions:
            return self.render_partial_update(excluded_regions=excluded_regions)
        if full or screen_region in self._dirty_regions:
            return self.render_full_update(simplify=simplify)
        return self.render_partial_update()

    def render_inline(
        self,
        size: Size,
        screen_stack: list[Screen] | None = None,
        clear: bool = False,
        excluded_regions: tuple[Region, ...] = (),
    ) -> RenderableType | None:
        """Render an inline update.

        Args:
            size: Inline size.
            screen_stack: Screen stack list. Defaults to None.
            clear: Also clear below the inline update (set when size decreases).

        Returns:
            A renderable.
        """
        visible_screen_stack.set([] if screen_stack is None else screen_stack)
        if excluded_regions:
            self._dirty_regions.add(self.size.region)
            update = self.render_partial_update(excluded_regions=excluded_regions)
            return None if update is None else InlineUpdate.from_chops(update, size.height)
        strips = self.render_strips(size)
        self._dirty_regions.clear()
        return InlineUpdate(strips, clear=clear)

    def render_full_update(self, simplify: bool = False) -> LayoutUpdate:
        """Render a full update.

        Args:
            simplify: Simplify the segments (combine contiguous segments).

        Returns:
            A LayoutUpdate renderable.
        """
        screen_region = self.size.region
        crop = screen_region
        chops = self._render_chops(crop, self._regions_to_spans((screen_region,)),
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

        self._dirty_regions.clear()
        return LayoutUpdate(render_strips, screen_region)

    def render_partial_update(self, *, excluded_regions: tuple[Region, ...] = ()) -> ChopsUpdate | None:
        """Render a partial update.

        Returns:
            A ChopsUpdate if there is anything to update, otherwise `None`.
        """
        screen_region = self.size.region
        update_regions = {
            damage for region in self._dirty_regions if (damage := region.intersection(screen_region))
        }
        ready_regions = self._exclude_regions(update_regions, excluded_regions)
        if not ready_regions:
            return None
        crop = Region.from_union(ready_regions)
        spans = list(self._regions_to_spans(ready_regions))
        cuts = self._publication_cuts(excluded_regions) if excluded_regions else self.cuts
        chops = self._render_chops(crop, spans,
                                  widgets=self.visible_widgets, cuts=cuts,
                                  bounds=screen_region)
        self._dirty_regions = self._exclude_regions(update_regions, ready_regions)
        return ChopsUpdate(chops, spans, cuts)

    def render_strips(self, size: Size | None = None) -> list[Strip]:
        """Render to a list of strips.

        Args:
            size: Size of render.

        Returns:
            A list of strips with the screen content.
        """
        if size is None:
            size = self.size
        rows = Region(0, 0, self.size.width, min(size.height, self.size.height))
        admitted = self._exclude_regions((rows,), self._render_exclusions)
        cuts = self._publication_cuts(self._render_exclusions) if self._render_exclusions else self.cuts
        chops = self._render_chops(size.region, self._regions_to_spans(admitted),
                                  widgets=self.visible_widgets, cuts=cuts,
                                  bounds=self.size.region)
        render_strips = [Strip.join(
            chop.get(x) or Strip.blank(end - x)
            for x, end in zip(cuts[y], cuts[y][1:])
        ) for y, chop in enumerate(chops[: size.height])]
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
        self, root: Widget, root_geometry: MapGeometry, *,
        admit: Callable[[Mapping[Widget, tuple[Region, Region]]], bool],
    ) -> tuple[Size, Iterator[list[Strip]]] | None:
        """Paint a body using its borrowed original published placement.

        The caller acquires the placement from published_geometry and consumes
        it before any await or DOM mutation. Capture never reacquires eligibility
        or manufactures a scene to decide whether a body can be retired. The
        same original arrangement/line/chop algorithm supplies complete rows
        without replacing any published map or constructing another compositor.

        The synchronous admission callback receives the exact complete paint
        mapping, including offscreen participants and excluding hidden or clipped
        children. It may refuse capture when those participants' resources are
        unavailable. Admission and painting borrow the same geometry; no second
        DOM walk or arrangement chooses another capture cohort.

        The returned iterator paints viewport-height bands. A preceding-source
        writer may drain it synchronously; a retirement task may yield between
        bands. The caller retains and validates its original source witness
        before advancing and before committing the complete result. Geometry
        lending ends before each band is returned, so ordinary input and frame
        publication never borrow a suspended capture's private arrangement.
        """
        bounds = root_geometry.region
        geometry, _, _ = self._arrange_root(
            root, self.size, visible_only=False, root_geometry=root_geometry,
        )
        widgets = MappingProxyType(self._paint_regions(self._ordered_geometry(geometry), bounds))
        with self._using_geometry(root, geometry):
            if not admit(widgets):
                return None
        band_height = max(1, self.size.height)

        def render_bands() -> Iterator[list[Strip]]:
            for y in range(bounds.y, bounds.bottom, band_height):
                band = Region(bounds.x, y, bounds.width, min(band_height, bounds.bottom - y))
                participants = {
                    widget: (region, paint)
                    for widget, (region, original_paint) in widgets.items()
                    if (paint := original_paint.intersection(band))
                }
                with self._using_geometry(root, geometry):
                    cuts = self._cuts_for_regions(band, participants)
                    chops = self._render_chops(band, self._regions_to_spans((band,)),
                                              widgets=participants, cuts=cuts, bounds=band)
                    strips = [Strip.join(chop.values()) for chop in chops]
                yield strips

        return bounds.size, render_bands()

    def _render_chops(
        self,
        crop: Region,
        spans: Iterable[tuple[int, int, int]],
        *, widgets: Mapping[Widget, tuple[Region, Region]], cuts: list[list[int]],
        bounds: Region,
    ) -> Sequence[Mapping[int, Strip]]:
        """Render update 'chops'.

        Args:
            crop: Region to crop to.
            spans: Original damaged horizontal spans to admit before painting.
            bounds: Original screen or body bounds represented by the chops.

        Returns:
            Chops structure.
        """
        chops: list[dict[int, Strip | None]] = [{} for _ in cuts]
        for y, x, _end in ChopsUpdate._span_cuts(spans, cuts, bounds.y):
            chops[y - bounds.y][x] = None
        remaining = {row: len(line) for row, line in enumerate(chops) if line}
        if not remaining:
            return cast("Sequence[Mapping[int, Strip]]", chops)

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
                if row in remaining:
                    start_x = None
                    row_cuts = cuts[row]
                    for index in range(bisect_left(row_cuts, first), bisect_left(row_cuts, last)):
                        x = row_cuts[index]
                        if x in chops[row] and chops[row][x] is None:
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

        for render_region, strips in renders:
            render_x = render_region.x
            first_cut, last_cut = render_region.column_span

            for y, strip in zip(render_region.line_range, strips):
                row = y - bounds.y
                chops_line = chops[row]
                if not chops_line:
                    continue
                row_cuts = cuts[row]
                final_cuts = row_cuts[bisect_left(row_cuts, first_cut):bisect_right(row_cuts, last_cut)]
                cut_strips = strip.divide([cut - render_x for cut in final_cuts[1:]])

                # Since we are painting front to back, the first segments for a cut "wins"
                for cut, strip in zip(final_cuts, cut_strips):
                    if cut in chops_line and chops_line[cut] is None:
                        chops_line[cut] = strip
                        count = remaining[row] - 1
                        if count:
                            remaining[row] = count
                        else:
                            del remaining[row]
            # These are the original pending chop rows, not widget readiness.
            # Once foreground paint has supplied every requested cut, no lower
            # widget can contribute. Do not scan its covered exposure again.
            if not remaining:
                break
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
