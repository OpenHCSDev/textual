# Preserve original placement order through native admission

Continue merged Text27 in the same checkout. Frozen Text27 and its installed
prefix remain unchanged. Heisenberg owns Toad and the one eventual joined
installed recording; this draft owns DockArrangeResult and its Compositor caller.

The original325 GIL trace observes native arrangement and chop painting during
held scrolling. At36.465s it observes reflow_visible -> arrange_widget ->
Screen.layers -> Widget.layers -> ancestors_with_self; other scroll observations
include arrange_widget's full-placement rank construction. These are source leads,
not call counts, durations or CPU attribution. Kernel UI scroll intervals77–83%
include observer overhead. Original recording and failed observer are preserved.

Source shows Compositor builds a placement_order dictionary from every child
before visible culling on every reflow, despite the existing DockArrangeResult
spatial resource already owning admission. It then independently selects retained
offscreen targets. Original placement ordinal belongs to the arrangement.

Extend the existing DockArrangeResult spatial resource to retain the original first-widget ordinal with each original placement. Its existing visible-placement operation supplies indexed original
placements and admits retained targets. Compositor derives rank from that ordinal
and consumes it unchanged through offsets. Delete its whole-list rank dictionary
and duplicated retained selection. No new map, cache, flag, type, registry,
renderer or Toad changes. Preserve layer/z/fixed/overlay/absolute semantics and
ordinary lazy geometry queries. Migrate every related native caller together.

Use existing NRA package parsing for declarations and consumers before editing;
read semantics separately, report omissions. Source implementation first; one
bounded affected native sanity batch and the integration owner's changed actual
saved-UI journey last. No independent capture/environment/provider, broad matrix,
unchanged gate, smoothness or FPS claim. Text27 source/physical qualification
remains separate and frozen.

## Working implementation

DockArrangeResult.iter_placements owns first-widget ordinals, preserving duplicate
widget placement rank. Its temporary construction dictionary is discarded; only
the existing SpatialMap retains indexed original placements. Equal placement
values remain deduplicated by that same spatial query. Complete geometry and
explicit offscreen targets consume original list order, including duplicates.
The compositor carries the admitted ordinal through offsets and derives its
rank relative to its parent. Its per-frame full-placement rank dictionary and
independent retained-target selection are deleted. Generic SpatialMap is unchanged.

Existing NRA parsed249 native and276 Toad modules without omissions. One
get_visible_placements consumer is Compositor; remaining spatial_map consumers
only read total_region. No Toad consumer needs migration. Original arrangement
list mutation and spatial resource lifetime remain unchanged. AST attribute-name
matching does not establish dynamic dispatch; the original owners were read.
Two production files44+/32−. Original source selection and all native callers
are changed together. Not installed-ready; no measured performance gain yet.

## Coherent source sanity and remaining installed boundary

One final affected batch passed6 checks in3.21s using existing native App tests:
original duplicate/fixed/retained admission, four viewport geometry/capture
checks and continuous viewport/full-render equivalence across resizing, scrolling,
source update and exposure. These detect changed rank/dedup, lost offscreen boxes,
wrong absolute capture and stale paint. No environment was created or installed.
This source run is not the changed installed Toad qualification.

Before mapping:249 native +276 Toad modules,0 parse omissions. After:249 native,
0 omissions, no placement_order definition or consumers. DockArrangeResult alone
constructs ordinal membership; Compositor's two full/visible paths consume it.
Only3 remaining spatial_map consumers read total_region or query the original
resource. The generic SpatialMap and original list invalidation contract remain
unchanged. Source artifacts and check log are preserved under
`.artifacts/native-placement-admission28-source01/` in this worktree.

Full arrangements and genuinely missing retained targets still traverse original
placements, since those operations require them. This change removes the eager
whole-list pass from ordinary culled scroll admission; it does not establish
absence of other native layout/paint work or measured CPU/smoothness gains.
Heisenberg owns the next changed installed saved-UI video/profile with his Toad
follow-up; no independent recording/provider or repeated Text27 qualification.
