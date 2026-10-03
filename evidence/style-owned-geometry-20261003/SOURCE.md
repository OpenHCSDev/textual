# Style and geometry source checkpoint

Production source: `2e8735a95a98589f036e3776a9cbeca19c0f8db9`, normally
integrated with main `69954eb38` (Text38). Eight production files: **197 added,
70 deleted**. This is a source checkpoint, awaiting the single paired installed
journey with Heisenberg's Toad384. Current default installations are untouched.

## What owns the work

- `Styles._update_rules` owns original rule membership, value mutation, update
  epoch and descriptor publication. Set/clear/reset/merge/compiled replacements
  all use it. Stored CSS `initial` (`None`) is preserved separately from removal.
  Descriptor lookup and geometry classification happen before mutation.
- `StyleProperty.affects_geometry` owns rule effects through the existing
  descriptor family. Color, opacity, hatch and transition changes retain paint
  validity without automatically destroying native Content geometry. Unknown
  descriptors and StringEnums remain conservative: native Content measurement
  reads wrapping/overflow even when the descriptor schedules only repaint.
- The original `_geometry_revision` declaration now lives on the common DOM
  ancestor, replacing Widget's declaration. Existing style publication carries
  the original mutation owner into native measurement hooks. Inherited source
  sensitivity is checked at the changed owner; native ancestors reuse the
  propagated result instead of traversing unrelated siblings again. Unknown
  custom measurements remain sensitive even when independent of available
  height. No cache, registry, second counter or retained policy flag was added.
- Widget arrangement/box/height proofs and `SubtreeGeometryKey` consume that
  original geometry resource. A box key reads its parent's actual auto-width
  and auto-height inputs, not unrelated changes in the parent's whole subtree.
- The existing Static rendering hook narrows only original Static.render,
  original visual getter and an already-retained original Content visual.
  Unknown/custom/unmaterialized visuals stay conservative; classification
  does not invoke render or create a visual. Flow/Grid/Stream share the original
  source-sensitivity operation while preserving their distinct box algorithms.
- The global Styles paint epoch and DOM subtree paint epoch are retained.
  Toad RetainedPaint/PaintState consumers are unchanged: geometry validity
  does not substitute for pixel validity.
- Heisenberg's contribution makes original MessagePump exit cover startup too.
  Widget closes messages/cancels workers before descendant and asynchronous
  Unmount hooks; the duplicate late Unmount cancellation is deleted. Startup
  cancellation still propagates and the original mounted-event finally remains.

## Replaced work

Deleted five competing Styles write/publication paths, duplicate enum/scrollbar
publication, Widget's duplicate geometry declaration/ancestor walk, geometry
consumers of broad paint-only style keys, and the late worker-cancellation
consumer. Pattern references: IMPL-6, IMPL-12 and IDEN-1. Original external CSS
values, renderer contracts and legitimate different layout operations remain.

`owner-consumers.json` uses the existing NRA/refactor-audit Package parser:
249 native modules and 288 Toad modules, zero parse omissions. Its final-source
entry points at the exact production checkpoint. Removed `_mark_updated` and
`SubtreeGeometryKey.styles_key` have no production/test consumers. The sole
geometry declaration is DOMNode; the sole original rule-write boundary is
Styles._update_rules. AST does not prove dynamic MRO resolution. Custom source
hooks were read semantically; their default remains conservative.

## Checks and limits

One affected sanity batch covers raw rule presence/publication, inherited
paint, native color-only geometry reuse, custom renderer measurement, raw
native display projection, structural/box/subtree reuse, mount/unmount and
worker custody. Exact final source: **138 passed in 6.51 seconds** using existing
system Python, with no new environment. The first **135 passed / 3 failed** log
is retained. It exposed a stored-initial/removal distinction and overly broad
parent-key invalidation; source was corrected without weakening assertions.

These checks do not prove visible FPS, CPU improvement, complete End behavior
or the installed Toad lifecycle. Heisenberg owns the single changed normal69
pair and real saved-session motion/profile gate. PR355's old source/failed End
movies remain protected; its limited mount/admission closure is not a speed
or final-End claim. No additional recording/provider run is authorized here.
