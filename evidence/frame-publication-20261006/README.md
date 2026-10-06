# Independent frame publication

Native Screen asks its existing preparation owner for deferred Widget roots.
Compositor derives held rectangles from committed geometry, retains their damage,
and publishes other spans through its existing chops and inline formats.
BackgroundScreen borrows the same admission during the synchronous render.
The original callback queue admits senders outside held subtrees; containers of
a held subtree also wait. Screen reports the exact acquired roots only after an
actual non-None display. The application writer remains responsible for flush.

Mutation roots borrow original committed placements during arrangement. Native
box measurement uses those placements rather than descending into changing
children. The existing scene map remains the geometry owner. No second queue,
timer, damage store or compositor is introduced.

The shared Toad contract is `_prepare_compositor_refresh() -> tuple[Widget, ...]`,
`_layout_mutation_roots() -> tuple[Widget, ...]`, and
`_on_frame_published(deferred_roots: tuple[Widget, ...])`. Parent owns Toad #482.

`before.json` uses the existing refactor-audit Package parser over all 249 native
production modules and 461 test modules, with zero omissions. Its 259 lexical
sites identify definitions and references; dynamic subclass and callback
resolution was read semantically, not inferred from absence.

This checkpoint is implementation in progress. Native checks and the matching
Toad application journey have not run. Translucent paint, inline cursor behavior,
held geometry and eventual callbacks remain required verification. The frozen
textual-native-subtree-strips checkout is unchanged.
