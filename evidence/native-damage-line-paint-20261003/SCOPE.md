# Native damage-row and chop publication

Reuse the existing Compositor and ChopsUpdate. Select damage rows once when
constructing their transient paint resource. Avoid allocating cut buckets and
copying row ends for undamaged screen rows. Make ChopsUpdate consume the original
cuts and have both Rich and terminal publication use Strip's existing cell crop.
Delete the separate segment clipping algorithms and repeated row admission.

This is independent of Heisenberg's Toad399 BodyMeasurement work. No new map,
cache, state flag, type, threshold, runtime, or provider input is required.

Source first: owner-before.json uses NRA Package across native production and
Toad production, including declarations and references. Read the original scene
ordering, complete/partial/body capture, damage spans, cuts, Strip.crop, and both
writer consumers. Attribute sites do not prove dynamic dispatch; Heisenberg's
working BodyMeasurement overrides were read separately from the committed AST.
Patterns IMPL-12 and IMPL-13: remove duplicated clipping and admission work at
their existing behavior owners rather than adding another controller.

The existing396/42 profile observes these paths during scrolling. Transition
counts are not CPU time and establish neither dominance nor speed improvement.
No new capture or heavy check is authorized now. After the coherent source
change, bounded checks will cover sparse damage, nonzero body bounds, Unicode
cell clipping, metadata and agreement between both writer formats. A changed
installed saved-session journey remains required before live readiness; reuse
the integration owner's next capture, without rerunning396/42.
