# Current native geometry for body capture

Scope: reuse Compositor's original geometry selection in find_widget and
can_render_subtree. Heisenberg owns the Toad viewport, layout targets and full
application integration. No second scene, geometry cache or body implementation.

The original E03 profile contains this held-scroll path:
retire_native_body -> can_render_subtree -> full_map -> _arrange_root.
Admission currently forces the full scene even though find_widget already accepts
current visible geometry. The fix preserves its selection order and NoWidget
boundary, and gives admission the same original lookup.

Existing NRA Package source mapping parsed all 249 Textual modules with no
omissions. Consumers include Screen, Widget geometry properties, selection and
render_subtree_strips. Their public geometry contracts remain unchanged.

E03 kernel whole-phase CPU was 91.16% and 69.89% during the two held-Up phases,
and 39.27% and 32.65% during the longer midhistory phases. These include settling
and diagnostic work; stack observations do not attribute those percentages.
Late stationary observations mainly select backend read/attestation work, not
whole-tree style/layout. That source finding was handed to Arendt.

Implement the native owner change first, then run one source-native geometry/body
sanity batch. No new physical recording or provider call; original E03 remains
the baseline and is not proof of this follow-up's performance.
