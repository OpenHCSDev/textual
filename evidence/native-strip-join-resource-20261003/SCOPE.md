# Keep the original immutable strip when joining one row

Stack after frozen Text47c264; do not hold its407 installed gate. Reuse this
checkout; no environment, capture, native copy, map, cache or type. Own existing
Strip.join only; no Compositor/Toad edits or overlapping body/frame ownership.

Existing immutable Strip owns segments, metadata, cell width and bounded render/
transformation resources. Compositor render_subtree_strips and render_strips
join original chop values. A single original row currently gets flattened and
copied into another Strip, even though joining one immutable value cannot change
its contents. The existing crop/divide identity transforms already borrow the
original value; join should carry the same value/resource behavior.

Read all native/Toad direct callers, Strip transformations/factory, prepared
capture/row resource lifetime and metadata. Extend existing Strip.join: consume
and filter the same iterable, reuse the sole nonempty member only when its exact
type matches the requested cls factory. Empty/multiple members and subclass
conversion retain original factory construction. No retained state or alternate
paint authority. Old/new rows share Segment metadata already; no geometry or
widget lifetime is supplied by a Strip. The value is immutable, caches remain
owned by that same existing resource. All joins derive behavior from this owner.

This removes per-row reconstruction and resets of original bounded resources.
It is source-supported allocation work, not a CPU dominance/gain claim. AST
covers complete native/dependency roots; dynamic plugin resolution stays outside
proof. Implement first, then batch concrete cell/metadata/factory/value checks
with the next changed native family. One later meaningful installed workflow,
not an unchanged47 or405 capture, supplies physical acceptance.
