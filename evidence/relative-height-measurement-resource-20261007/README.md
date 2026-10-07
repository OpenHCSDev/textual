# Relative-height measurement source

Widget's original height-dependency resource now holds the separate computed
box and relative-descendant answers under its original structural/layout epoch.
It does not derive relative stretch from content or box independence.
Unchanged native descendants answer through that resource instead of walking
their children again. Paint-only refresh does not retire it.

NodeList publishes membership, display constraints and prune admission to
ancestor epochs. Styles publishes actual geometry-rule changes through the
measurement owner before idle, including raw rule writes. Authored layout
changes propagate through auto-size ancestry; the relative query stops at
fixed-size children. Reparenting invalidates old and new native custody.

The original query remains live for custom container, child-list, display,
relative-height and scalar implementations. Source uncertainty propagates
through the actual auto-child path; it is not inferred from labels or bounds.
Custom content/layout behavior remains governed by its separate HeightDependency
declaration and is not used as a certificate for relative stretch.

Direct message-pump closure also changes native display before detach. The
existing pump now supplies a polymorphic closing hook; DOMNode publishes the
same NodeList update used by prune admission. This completes the native source
lifetime rather than keeping a stale relative answer until physical removal.

The source checkpoint is not yet qualified. Next verification covers original
style/display/reparent/retirement paths, opaque live getters, and the existing
loaded source Toad App. No provider/input, package/public runtime or saved-data
operation is part of this change. Original profile gaps remain correlation,
not duration attribution or a claimed improvement.
