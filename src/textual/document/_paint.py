"""Native document geometry and paint, without scene or message-pump admission."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, replace
from fractions import Fraction
from typing import TYPE_CHECKING, Callable, Iterable
from weakref import ref

from rich.style import Style as RichStyle
from rich.palette import Palette

from textual._arrange import arrange
from textual._compositor import Compositor, RootSceneClip
from textual._extrema import Extrema
from textual._styles_cache import StylesCache
from textual.box_model import BoxModel
from textual.content import Content
from textual.css.styles import RenderStyles, Styles
from textual.css.stylesheet import Stylesheet
from textual.dom import DOMNode
from textual.geometry import NULL_OFFSET, NULL_SPACING, Offset, Region, Size, Spacing
from textual.layout import WidgetPlacement
from textual.map_geometry import MapGeometry
from textual.layouts.vertical import VerticalLayout
from textual.strip import Strip, StripRenderable
from textual.visual import RenderOptions, Visual

if TYPE_CHECKING:
    from rich.terminal_theme import TerminalTheme
    from textual.filter import LineFilter
    from textual.layout import DockArrangeResult, Layout


class StyleContext(DOMNode):
    """An acquired declaration and selector state, separate from live custody."""

    def __init__(self, declaration, *, pseudo_classes=frozenset(), **kwargs):
        self.declaration = declaration
        self._document_pseudo_classes = pseudo_classes
        super().__init__(**kwargs)
        # Original detached Styles already own validation without scene
        # notification when node=None. RenderStyles still owns inheritance.
        self._css_styles = Styles()
        self._inline_styles = Styles()
        self.styles = RenderStyles(self, self._css_styles, self._inline_styles)

    @property
    def _parent(self):
        reference = self.__dict__.get("_document_parent")
        return None if reference is None else reference()

    @_parent.setter
    def _parent(self, parent):
        # Source ancestry is independent of message-pump custody and its epoch.
        self._document_parent = None if parent is None else ref(parent)

    def _make_component_node(self, component):
        return StyleContext(DOMNode, classes=component)

    @property
    def style_type(self):
        return self.declaration

    def bind_declaration(self, declaration):
        self._document_declaration = declaration
        self._css_types = declaration.selector_names

    def _is_style_type(self, declaration):
        captured = self.__dict__.get("_document_declaration")
        return (
            declaration in captured.python_bases
            if captured is not None
            else issubclass(self.declaration, declaration)
        )

    @property
    def _component_style_scope(self):
        captured = self.__dict__.get("_document_declaration")
        return (
            self.declaration._component_style_scope
            if captured is None
            else captured.component_scope
        )

    @property
    def css_type_names(self):
        captured = self.__dict__.get("_document_declaration")
        return (
            self.declaration._css_type_names
            if captured is None
            else captured.type_names
        )

    @property
    def css_type_name(self):
        captured = self.__dict__.get("_document_declaration")
        return (
            self.declaration._css_type_name if captured is None else captured.type_name
        )

    def _selector_type_names(self):
        return self.declaration._selector_type_names()

    @property
    def _node_bases(self):
        captured = self.__dict__.get("_document_declaration")
        return (
            self.declaration._css_bases(self.declaration)
            if captured is None
            else captured.bases
        )

    def _get_component_classes(self):
        captured = self.__dict__.get("_document_declaration")
        return (
            self.declaration._get_component_classes()
            if captured is None
            else captured.component_classes
        )

    def has_pseudo_classes(self, class_names):
        return class_names <= self.get_pseudo_classes()

    def has_pseudo_class(self, class_name):
        return class_name in self.get_pseudo_classes()

    def get_pseudo_classes(self):
        return set(self._document_pseudo_classes)

    @property
    def _pseudo_classes_cache_key(self):
        return frozenset(self.get_pseudo_classes())


class DocumentNode(StyleContext):
    """One acquired native declaration in an immutable document.

    These nodes have native CSS ancestry and use native layouts, box resolution
    and paint. They never register with an App, start a message pump, mount a
    widget, or read scene geometry. A declaration supplies content and children;
    arbitrary widget methods are not invoked on this different resource.
    """

    _component_style_scope = True

    def __init__(
        self,
        declaration: type[DOMNode],
        content: Content | None = None,
        *,
        children: Iterable[DocumentNode] = (),
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        expand: bool = False,
        shrink: bool = False,
        pseudo_classes: frozenset[str] = frozenset(),
        scroll_offset: Offset = NULL_OFFSET,
        source_range: tuple[int, int] | None = None,
        source_index: int | None = None,
        pre_layout: Callable | None = None,
        process_layout: Callable | None = None,
        inline_rules: dict | None = None,
        auto_links: bool = True,
        selection: Callable = Visual.selected_text,
    ) -> None:
        self.content = content
        self.expand = expand
        self.shrink = shrink
        self.scroll_offset = scroll_offset
        self.source_range = source_range
        self.source_index = source_index
        self._prepare_layout = pre_layout
        self._process_layout = process_layout
        self.auto_links = auto_links
        self.selection = selection
        self.text_selection = None
        self._document_selection_style = None
        self.selecting = False
        self._extrema = Extrema()
        self._region = Region()
        self._default_layout = VerticalLayout()
        self._styles_cache = StylesCache()
        super().__init__(
            declaration,
            pseudo_classes=pseudo_classes,
            name=name,
            id=id,
            classes=classes,
        )
        if inline_rules:
            self._inline_styles = Styles(_rules=deepcopy(inline_rules))
            self.styles = RenderStyles(self, self._css_styles, self._inline_styles)
        for child in children:
            self.add(child)

    def add(self, child: DocumentNode) -> None:
        child._attach(self)
        self._nodes._append(child)

    def get_pseudo_classes(self) -> set[str]:
        # Ordered and empty state belongs to this complete source cohort, not
        # the preceding mounted scene. Other state is explicitly acquired.
        result = set(self._document_pseudo_classes)
        result.discard("empty")
        if self.is_empty:
            result.add("empty")
        if not isinstance(self.parent, DocumentNode):
            return result
        positions = {
            "first-of-type": self.first_of_type,
            "last-of-type": self.last_of_type,
            "first-child": self.first_child,
            "last-child": self.last_child,
            "odd": self.is_odd,
            "even": self.is_even,
            "empty": self.is_empty,
        }
        result.difference_update(positions)
        result.update(name for name, present in positions.items() if present)
        return result

    @property
    def layout_viewport(self) -> Size:
        return self.presentation.viewport

    @property
    def layout_screen_size(self) -> Size:
        return self.presentation.screen_size

    @property
    def is_container(self) -> bool:
        return bool(self._nodes) or self.styles.layout is not None

    @property
    def layout(self) -> Layout:
        return self.styles.layout or self._default_layout

    @property
    def layer(self) -> str:
        return self.styles.layer or "default"

    def _get_document_layer_order(self):
        order = None
        for node in self.walk_ancestors(with_self=True):
            if not node._component_style_scope:
                break
            if node.styles.has_rule("layers"):
                order = node.styles.layers
        return order

    absolute_offset = None

    @property
    def uses_screen_coordinates(self) -> bool:
        return self.styles.has_any_rules("constrain_x", "constrain_y")

    @property
    def show_vertical_scrollbar(self) -> bool:
        return False

    @property
    def show_horizontal_scrollbar(self) -> bool:
        return False

    @property
    def _has_relative_children_height(self) -> bool:
        return self._scan_relative_children_height(False)[0]

    def pre_layout(self, layout: Layout) -> None:
        """Declarations with preparation effects override this source method."""
        if self._prepare_layout is not None:
            self._prepare_layout(self, layout)

    def process_layout(self, placements):
        return (
            placements
            if self._process_layout is None
            else self._process_layout(placements)
        )

    @property
    def layout_invalidated_widgets(self):
        # This is a fresh immutable source, never a partially updated scene.
        return self.children

    @property
    def scrollable_content_region(self):
        return (
            self.content_region if self.region else Size(self._layout_width, 0).region
        )

    def arrange(self, size: Size, optimal: bool = False) -> DockArrangeResult:
        self._layout_width = size.width
        return arrange(self, self.children, size, self.layout_viewport, optimal)

    def _resolve_extrema(self, container, viewport, width_fraction, height_fraction):
        return Extrema.resolve(
            self.styles,
            container,
            viewport,
            width_fraction,
            height_fraction,
        )

    def _get_box_model(
        self,
        container,
        viewport,
        width_fraction,
        height_fraction,
        constrain_width=False,
        greedy=True,
    ) -> BoxModel:
        model, self._extrema = BoxModel.resolve(
            self,
            container,
            viewport,
            width_fraction,
            height_fraction,
            constrain_width,
            greedy,
        )
        return model

    def get_content_width(self, container: Size, viewport: Size) -> int:
        self._layout_width = container.width
        return self._measure_content_width(container, viewport)

    def get_content_height(self, container: Size, viewport: Size, width: int) -> int:
        self._layout_width = width
        return self._measure_content_height(container, viewport, width)

    def _render(self):
        return self.content if self.content is not None else self._render_container()

    def render(self):
        return self._render()

    @property
    def region(self) -> Region:
        return self._region

    @property
    def content_region(self) -> Region:
        return self.region.shrink(self.styles.gutter)

    def render_lines(self, crop: Region) -> list[Strip]:
        content_size = self.content_region.size
        visual = self._render()
        if isinstance(visual, StripRenderable):
            # Native Canvas already owns these complete keyline rows. No Rich
            # console or scene widget is required to render them a second time.
            lines = list(visual._strips)
        else:
            lines = visual.render_strips(
                content_size.width,
                content_size.height,
                self.visual_style,
                RenderOptions(
                    self._get_style,
                    self.styles,
                    self.text_selection,
                    self._document_selection_style,
                ),
            )
        lines = Visual.format_strips(
            lines,
            *content_size,
            self.visual_style,
            link_style=(
                self.link_style
                if self.auto_links and not self.is_container and not self.selecting
                else None
            ),
            content_align=self.styles.content_align,
        )
        blank = Strip.blank(content_size.width, self.visual_style.rich_style)
        base_background, background = self.background_colors
        strips = self._styles_cache.render(
            self.styles,
            self.region.size,
            base_background,
            background,
            lambda y: lines[y] if y < len(lines) else blank,
            self.presentation.filters,
            None,
            None,
            content_size=content_size,
            crop=crop,
            opacity=self._resolved_paint_state().opacity,
            ansi_theme=self.presentation.ansi_theme,
            native_ansi=self.presentation.native_ansi,
        )
        if not self.is_container:
            identity = RichStyle.from_meta({"document_leaf": self.paint_leaf_index})
            strips = [strip.apply_style(identity) for strip in strips]
        return strips


def _input_value(value):
    """Freeze actual native value inputs, never scene epochs or CSS guesses."""
    from rich.terminal_theme import TerminalTheme
    from textual.layout import Layout

    if isinstance(value, Layout):
        return value.document_key()
    if isinstance(value, TerminalTheme):
        return (type(value), _input_value(vars(value)))
    if isinstance(value, Palette):
        return (type(value), _input_value(value._colors))
    if isinstance(value, dict):
        return tuple((key, _input_value(item)) for key, item in sorted(value.items()))
    if isinstance(value, (list, tuple)):
        return tuple(_input_value(item) for item in value)
    if isinstance(value, (set, frozenset)):
        return frozenset(_input_value(item) for item in value)
    return deepcopy(value)


@dataclass(frozen=True)
class StyleInput:
    declaration: type[DOMNode]
    type_names: frozenset[str]
    type_name: str
    selector_names: frozenset[str]
    bases: tuple[type[DOMNode], ...]
    python_bases: tuple[type, ...]
    component_classes: frozenset[str]
    component_scope: bool
    name: str | None
    id: str | None
    classes: str
    pseudo_classes: frozenset[str]
    base_rules: dict
    inline_rules: dict
    components: tuple
    key: tuple

    @classmethod
    def acquire(cls, node: DOMNode):
        base, inline = node.styles.base.get_rules(), node.styles.inline.get_rules()
        components = tuple(
            (name, style.base.get_rules(), style.inline.get_rules())
            for name, style in sorted(node._component_styles.items())
        )
        values = (
            node.style_type,
            node.css_type_names,
            node.css_type_name,
            node._css_types,
            tuple(node._node_bases),
            tuple(node.style_type.__mro__),
            node._get_component_classes(),
            node._component_style_scope,
            node.name,
            node.id,
            " ".join(sorted(node.classes)),
            frozenset(node.get_pseudo_classes()),
            _input_value(base),
            _input_value(inline),
            _input_value(components),
        )
        return cls(
            *values[:12], deepcopy(base), deepcopy(inline), deepcopy(components), values
        )

    def make(self):
        node = StyleContext(
            self.declaration,
            name=self.name,
            id=self.id,
            classes=self.classes,
            pseudo_classes=self.pseudo_classes,
        )
        node.bind_declaration(self)
        node._css_styles = Styles(_rules=deepcopy(self.base_rules))
        node._inline_styles = Styles(_rules=deepcopy(self.inline_rules))
        node.styles = RenderStyles(node, node._css_styles, node._inline_styles)
        # Component styles retain their original attached virtual-node meaning.
        from textual.css.stylesheet import _ComponentStyles

        for name, base, inline in self.components:
            component = node._make_component_node(name)
            component._attach(node)
            component._css_styles = Styles(_rules=deepcopy(base))
            component._inline_styles = Styles(_rules=deepcopy(inline))
            component.styles = RenderStyles(
                component, component._css_styles, component._inline_styles
            )
            node._component_styles[name] = _ComponentStyles(component)
        return node


@dataclass(frozen=True)
class DocumentPresentation:
    """Exact acquired style and terminal inputs, independent of widget lifetime."""

    ancestors: tuple[StyleInput, ...]
    root: StyleInput
    declarations: tuple[StyleInput, ...]
    stylesheet: Stylesheet
    viewport: Size
    screen_size: Size
    ansi_theme: TerminalTheme
    native_ansi: bool
    filters: tuple[LineFilter, ...]
    key: tuple
    admission: tuple

    @staticmethod
    def current_admission(owner) -> tuple:
        """Original invalidation facts for this actual publication participant.

        These facts qualify repeated queries only on the same admitted scene
        lifetime. A replacement widget requires value comparison at publication;
        an equal new counter never certifies retained document paint.
        """
        app = owner.app
        stylesheet = app.stylesheet
        return (
            tuple(
                (
                    id(node),
                    type(node),
                    node._parent_revision,
                    node.styles._cache_key,
                    node.id,
                    node.name,
                    node.classes,
                    frozenset(node.get_pseudo_classes()),
                )
                for node in owner.css_path_nodes
            ),
            owner._subtree_style_revision,
            id(stylesheet),
            id(stylesheet._rules),
            stylesheet._require_parse,
            app.viewport_size,
            app.size,
            app.theme,
            app.native_ansi_color,
            _input_value(app.ansi_theme),
            tuple(
                (type(filter), type(filter).apply, _input_value(vars(filter)))
                for filter in owner.get_line_filters()
            ),
        )

    def current_for(self, owner) -> bool:
        return self.admission == self.current_admission(owner)

    @classmethod
    def acquire(cls, owner, declarations) -> DocumentPresentation:
        css_path = owner.css_path_nodes
        if css_path != list(reversed(owner.ancestors_with_self)):
            raise TypeError(
                "Custom CSS and paint ancestry require an acquired document presentation"
            )
        ancestors = tuple(StyleInput.acquire(node) for node in css_path[:-1])
        root = StyleInput.acquire(owner)
        declarations = tuple(
            StyleInput.acquire(StyleContext(declaration))
            for declaration in sorted(
                declarations, key=lambda item: (item.__module__, item.__qualname__)
            )
        )
        stylesheet = owner.app.stylesheet.copy()
        for declaration in declarations:
            context = declaration.make()
            for path, source, specificity, scope in context._get_default_css():
                stylesheet.add_source(
                    source,
                    read_from=path,
                    is_default_css=True,
                    tie_breaker=specificity,
                    scope=scope,
                )
        filters = tuple(
            filter.acquire_document() for filter in owner.get_line_filters()
        )
        ansi_theme = deepcopy(owner.app.ansi_theme)
        key = (
            tuple(item.key for item in ancestors),
            root.key,
            tuple(item.key for item in declarations),
            tuple(stylesheet.source.items()),
            _input_value(stylesheet._variables),
            owner.app.viewport_size,
            owner.app.size,
            _input_value(ansi_theme),
            owner.app.native_ansi_color,
            tuple(
                (type(filter), type(filter).apply, _input_value(vars(filter)))
                for filter in filters
            ),
        )
        return cls(
            ancestors,
            root,
            declarations,
            stylesheet,
            owner.app.viewport_size,
            owner.app.size,
            ansi_theme,
            owner.app.native_ansi_color,
            filters,
            key,
            cls.current_admission(owner),
        )

    def prepare(
        self,
        root: DocumentNode,
        width: int,
        *,
        document,
        blocks,
        headings,
        selections=None,
        selection_style=None,
    ) -> DocumentPaint:
        # Every preparation owns its mutable CSS/geometry workspace. The
        # retained result owns only strips, literal provenance and source boxes.
        stylesheet = self.stylesheet.copy()
        stylesheet.parse()
        ancestors = [item.make() for item in self.ancestors]
        for parent, child in zip(ancestors, ancestors[1:]):
            child._attach(parent)
        if ancestors:
            root._attach(ancestors[-1])
        declarations = {item.declaration: item for item in self.declarations}
        nodes = list(root.walk_children(with_self=True))
        for node in nodes:
            node.presentation = self
            node.bind_declaration(declarations[node.declaration])
            stylesheet.apply(node)
            if node.styles.layout is not None:
                node.styles.layout.document_key()
                node.styles.layout = deepcopy(node.styles.layout)
        gutter = root.styles.gutter
        content_width = max(0, width - gutter.width)
        height = root.get_content_height(
            Size(content_width, 0), self.viewport, content_width
        )
        size = Size(width, height + gutter.height)
        geometry = {}
        leaves = []
        no_clip = RootSceneClip(size.region)

        def place(
            node,
            virtual_region,
            region,
            order,
            layer_order,
            clip,
            visible,
            dock_gutter,
            inherited_layers,
            source_index,
        ):
            if not node.display:
                return
            if (visibility := node.styles.get_rule("visibility")) is not None:
                visible = visibility == "visible"
            if node.source_index is not None:
                source_index = node.source_index
            node.paint_source_index = source_index
            node._region = region
            content_region = region.shrink(node.styles.gutter)
            total_region = content_region.reset_offset
            layers = inherited_layers
            if layers is None:
                if (names := node._get_document_layer_order()) is not None:
                    layers = {name: index for index, name in enumerate(names)}
            if node.is_container:
                if (
                    node.styles.scrollbar_gutter == "stable"
                    and node.styles.scrollbar_size_vertical
                ):
                    content_region, _ = content_region.split_vertical(
                        -node.styles.scrollbar_size_vertical
                    )
                result = node.arrange(content_region.size)
                total_region = content_region.reset_offset.union(result.total_region)
                sub_clip = clip.intersect(content_region)
                placements = WidgetPlacement.process_offsets(
                    result.placements,
                    size.region,
                    content_region.offset - node.scroll_offset,
                )
                for (
                    child,
                    local,
                    placed,
                    rank,
                    ordinal,
                    child_clip,
                ) in Compositor._place_children(
                    placements,
                    len(result.placements),
                    content_region,
                    node.scroll_offset,
                    order,
                    layer_order,
                    sub_clip,
                    no_clip,
                    layers or {"default": 0},
                ):
                    place(
                        child,
                        local,
                        placed,
                        rank,
                        ordinal,
                        child_clip,
                        visible,
                        result.scroll_spacing,
                        layers,
                        source_index,
                    )
            if visible:
                geometry[node] = MapGeometry(
                    region,
                    order,
                    clip.region,
                    total_region.size,
                    content_region.size,
                    virtual_region,
                    dock_gutter,
                )
                if not node.is_container:
                    node.paint_leaf_index = len(leaves)
                    node.selecting = selections is not None
                    node.text_selection = (
                        None
                        if selections is None
                        else selections.get(node.paint_leaf_index)
                    )
                    node._document_selection_style = selection_style
                    leaves.append(
                        DocumentLeaf(
                            source_index,
                            node.declaration,
                            node.content,
                            region,
                            content_region,
                            clip.region,
                            node.selection,
                            node.link_style,
                            node.link_style_hover,
                        )
                    )

        inherited_layers = None
        for node in reversed(ancestors):
            if node._component_style_scope and node.styles.has_rule("layers"):
                inherited_layers = {
                    name: index for index, name in enumerate(node.styles.layers)
                }
        place(
            root,
            size.region,
            size.region,
            ((0, 0, 0),),
            0,
            no_clip,
            True,
            NULL_SPACING,
            inherited_layers,
            None,
        )
        compositor = Compositor()
        mapping = compositor._paint_regions(
            compositor._ordered_geometry(geometry), size.region
        )
        chops = compositor._render_chops(
            size.region,
            compositor._regions_to_spans((size.region,)),
            widgets=mapping,
            cuts=compositor._cuts_for_regions(size.region, mapping),
            bounds=size.region,
        )
        lines = tuple(Strip.join(line.values()) for line in chops)
        placements = tuple(
            DocumentBlockPlacement(
                node.source_index,
                node.declaration,
                node.source_range,
                entry.region,
                entry.clip,
                node.id,
            )
            for node, entry in compositor._ordered_geometry(geometry)
            if node.source_index is not None
        )
        placements_by_id = {
            placement.id: placement
            for placement in placements
            if placement.id is not None
        }
        return DocumentPaint(
            size,
            lines,
            placements,
            tuple(leaves),
            document,
            self.key,
            width,
            gutter,
            root.content_region.size,
            tuple(
                DocumentHeading(entry, placements_by_id.get(entry[2]))
                for entry in headings
            ),
        )


@dataclass(frozen=True)
class DocumentBlockPlacement:
    source_index: int
    declaration: type[DOMNode]
    source_range: tuple[int, int]
    region: Region
    clip: Region
    id: str | None

    def source_text(self, document) -> str:
        from textual.widgets._markdown import MarkdownBlock

        return MarkdownBlock.source_text(document.source, self.source_range)


@dataclass(frozen=True)
class DocumentHeading:
    """One original heading entry and its actual optional native placement."""

    entry: tuple[int, str, str | None]
    placement: DocumentBlockPlacement | None


@dataclass(frozen=True)
class DocumentLeaf:
    source_index: int | None
    declaration: type[DOMNode]
    content: Content
    region: Region
    content_region: Region
    clip: Region
    selection: Callable
    link_style: RichStyle
    link_style_hover: RichStyle

    def selected_text(self, selection):
        """Use original leaf coordinates and its native copy delimiter."""
        return self.selection(self.content, selection)


@dataclass(frozen=True)
class DocumentPaint:
    """Native paint/extents and source identity, with no retained scene nodes.

    Leaf logical offsets and block regions remain separate from document paint
    rows. Interaction owners use these facts; rows aren't raw Markdown offsets.
    """

    size: Size
    lines: tuple[Strip, ...]
    blocks: tuple[DocumentBlockPlacement, ...]
    leaves: tuple[DocumentLeaf, ...]
    document: object
    presentation_key: tuple
    width: int
    """Acquired outer width, including the original root gutter."""
    gutter: Spacing
    """Actual worker-resolved native root padding and border."""
    content_size: Size
    """Intrinsic inner extent; scene allocation does not replace this answer."""
    headings: tuple[DocumentHeading, ...]

    @property
    def table_of_contents(self):
        return [heading.entry for heading in self.headings]

    def anchor_region(self, anchor: str) -> Region | None:
        """Use the original duplicate-aware heading slug decision."""
        from textual.widgets._markdown import Markdown

        block_id = Markdown.anchor_id_for(self.table_of_contents, anchor)
        for heading in self.headings:
            if heading.entry[2] == block_id and heading.placement is not None:
                return heading.placement.region
        return None

    def matches(self, document, width: int) -> bool:
        return (
            width == self.width
            and document.same_source(self.document)
            and document.presentation.key == self.presentation_key
        )

    def is_current(self, owner, width: int) -> bool:
        """Compare current declared presentation without reading any descendants.

        The source owner must still hold this exact acquired document. A source
        replacement acquires a new MarkdownDocument; style refresh uses its
        with_presentation(). Scene eviction cannot certify different source.
        """
        return width == self.width and self.document.presentation.current_for(owner)

    def with_presentation(self, document) -> DocumentPaint:
        """Admit retained paint after actual source/presentation value equality.

        Call at publication, including after eviction. Rows are reused only if
        their source, width and effective inputs agree. The resulting resource
        owns the new participant's original invalidation witness.
        """
        if not self.matches(document, self.width):
            raise ValueError(
                "Retained document paint has different source or presentation"
            )
        return replace(self, document=document)

    def render_lines(self, crop: Region) -> list[Strip]:
        """Borrow native rows; retain leaf logical-offset and link metadata."""
        return [
            (
                self.lines[y] if 0 <= y < self.size.height else Strip.blank(self.width)
            ).crop(crop.x, crop.right)
            for y in crop.line_range
        ]

    def get_leaf_and_offset_at(self, x: int, y: int):
        """Hit actual composed metadata; offsets belong to that original leaf."""
        if not self.size.region.contains(x, y):
            return None, None
        line = self.lines[y]
        index = line.get_style_at(x).meta.get("document_leaf")
        if index is None:
            return None, None
        return index, line.get_content_offset(x, scope=("document_leaf", index))

    def prepare_selection(self, selections, selection_style):
        """Worker-side native selection styling, retaining original leaf offsets.

        Use the same source/content/CSS owners, including native tab expansion
        and wrapping. The interaction owner supplies leaf Selection values and
        the Screen's original selection style; paint rows aren't source offsets.
        """
        return self.document.prepare(
            self.width, selections=selections, selection_style=selection_style
        )
