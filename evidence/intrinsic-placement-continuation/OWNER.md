# Existing native placement resource continuation

Heisenberg owns the existing native compositor family under Toad284/275 whole viewport integration. Base actual Textual main5fbf5c76. Original18 source and evidence are frozen. No new classes, fields, caches, renderer, clock, semantic state or format compatibility.

## Semantic source relation

SubtreeGeometryKey is the existing fourteen-input native arrangement contract. Its intrinsic form previously normalized screen region and clipping but retained outer document virtual offset and absolute paint prefix/rank. Pure prepend, eviction or host relocation therefore rejected a valid body arrangement. Ignoring these dimensions alone would be wrong: MapGeometry carries the root's parent-relative virtual placement and every descendant's native paint rank.

Extend this existing key's intrinsic normalization and project_order. The existing SubtreeMapGeometry projects native region, clip, order and root virtual_region together. The original compositor dictionary key remains root identity: the sole restore caller passes its current native render widget transiently, never stores another owner field. IntrinsicSubtreeGeometry consumes that identity; PlacedSubtreeGeometry retains exact-coordinate matching and culling. Inherited layers, dimensions, style/custody revisions, coverage, scroll offset, screen dependencies, capacity and selective retirement remain unchanged. Screen-constrained/overlay geometry still uses its existing exact placement policy.

Original paint prefix identifies the subtree; only its descendant suffix receives the root's current rank delta. Child virtual regions remain relative to their original internal containers; the root receives current parent-relative virtual placement. An unchanged projected MapGeometry retains native object identity.

Complete source search before implementation: one declaration per key/resource type; one native restore producer and all three projection consumers migrated. No deprecated API/alias/fallback or outside switch. Patterns IDEN-1/IMPL-13/TIME-9. A new placement still uses Widget/layout's existing declarations, requiring no cache roster edit.

```text
src/textual/_compositor.py:65:class SubtreeGeometryKey(NamedTuple):
src/textual/_compositor.py:88:    def project_order(self, order: tuple, destination: SubtreeGeometryKey) -> tuple:
src/textual/_compositor.py:150:class SubtreeMapGeometry(NamedTuple):
src/textual/_compositor.py:174:            order=original.project_order(self.geometry.order, current),
src/textual/_compositor.py:185:class SubtreeGeometry(ABC, Generic[GeometryEntry]):
src/textual/_compositor.py:205:    def restore_into(
src/textual/_compositor.py:210:        self.project_into(geometry, key, clip, clips, root)
src/textual/_compositor.py:215:    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
src/textual/_compositor.py:224:class PlacedSubtreeGeometry(SubtreeGeometry[MapGeometry]):
src/textual/_compositor.py:230:    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
src/textual/_compositor.py:237:class IntrinsicSubtreeGeometry(SubtreeGeometry[SubtreeMapGeometry]):
src/textual/_compositor.py:257:    def project_into(self, geometry: CompositorMap, key: SubtreeGeometryKey,
src/textual/_compositor.py:260:            geometry[node], clips[node] = entry.project(self.key, key, clip, root=node is root)
src/textual/_compositor.py:1090:                cached.restore_into(map, widgets, invisible_widgets, key, clip, clips, widget._render_widget)
```

## Final validation boundary

Code reasoning and the coherent implementation precede final validation. Reuse existing native scroll/scene/custody control with prepend/reorder/eviction and complete-versus-culled scene equality, then one meaningful normal installed saved-history physical/CPU gate at a package checkpoint. No source or installed speed claim yet. Source profile evidence motivates this scope but does not assign a CPU fraction. Runtime lifecycle Arendt, compaction/T5 Sch,493 borrowed-reader methods retain their existing owners.
