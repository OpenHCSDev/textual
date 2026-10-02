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

Extend the existing DockArrangeResult spatial resource to retain original list
indices. Its existing visible-placement operation supplies indexed original
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
