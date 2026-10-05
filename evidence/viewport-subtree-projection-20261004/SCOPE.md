# Complete resources and viewport geometry

The existing `SubtreeGeometry` resource owns complete reusable arrangements.
Its viewport consumer currently publishes every cached descendant before the
compositor sorts and clips that scene. A long live body therefore projects its
offscreen descendants on each scroll even when only a few rows are exposed.

This change will make the original geometry family own viewport projection for
both restored and newly captured resources. Complete capture, ordinary lazy
full-map queries, explicit reader and interaction targets, overlays, covers and
scrollbars retain their original contracts. No second geometry map, cache or
state owner will be introduced. Heisenberg owns the Toad consumers and their
affected installed qualification; the precise body contract is being confirmed
directly before source edits.

Source relationships come first. The whole related native family and consumers
will be migrated together, followed by one proportionate final sanity batch and
the affected installed application under an explicitly granted purpose. This
draft has no runtime, package or provider purpose and claims no measured gain.

The separate callback arity source defect remains independent; it does not hold
this geometry change or imply a frame-time attribution.
