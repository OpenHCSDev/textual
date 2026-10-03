# Native damage-row and chop publication

Reuse the existing Compositor and ChopsUpdate. Select damage rows once when
constructing their transient paint resource. Avoid allocating cut buckets and
copying row ends for undamaged screen rows. Make ChopsUpdate consume the original
cuts and have both Rich and terminal publication use Strip's existing cell crop.
Delete the separate segment clipping algorithms and repeated row admission.

This is independent of Heisenberg's Toad399 BodyMeasurement work. No new map,
cache, state flag, type, threshold, runtime, or provider input is required.

## Working checkpoint

Source `0efe0803cc043a8155e367f63e2398738e1cf678` implements the family:

- Compositor applies its existing row predicate only during chop admission.
  Undamaged rows have no cut buckets; both exposure and fill use those original
  resources instead of re-deciding row selection for each widget.
- Sorted original cuts bound exposure, strip division and publication. Each
  consumer visits only its intersecting cut interval.
- ChopsUpdate borrows the original cuts. Both output formats call its one
  `_get_line_chops` implementation and Strip.crop owns cell/metadata splitting.
  The deleted Rich segment walker and terminal crop differed at the left edge;
  both formats now move to the actual clipped start, including wide cells.
- Partial publication no longer copies end lists for every screen row. The
  original cuts remain immutable during this synchronous publication; later
  compositor invalidation replaces its reference rather than mutating them.

New production change: `_compositor.py` 42 added / 73 deleted lines. The existing
frame-damage test's removed `chop_ends` reader now consumes the same native cuts.
After evidence parses all 249 native modules without omissions: zero
`chop_ends` references, one shared clipping declaration and its two writer calls.
Before evidence also parses all 289 Toad modules without omissions. Native body
capture, full, partial, inline, SVG and terminal consumers share the same chop
algorithm; body capture retains its nonzero original coordinate bounds.

### Exact prerequisite graph and main landing

GitHub42 merged `14baa381` into the retained41 feature branch, not main. Remote
main is `067a652041` (merged41). This branch normally integrated that main and
preserves qualified42 unchanged. Therefore the full main diff additionally
contains42's accepted App registration change (28 added /14 deleted), its test
and original evidence. No App work was added by43. Parent owns landing that
accepted prerequisite; it must not silently be discarded or counted as new43
implementation.

Parent authorized the existing42 owner to correct that graph. A normal merge
of14baa into main produced `0246a97fe062f156deee683bfb3f67e51cd485b8`.
`git diff14baa0246` is empty for the ENTIRE tree. Main now contains the exact
qualified42 source without43. Schrodinger received this receipt;397's qualified
14baa pin needs no build, repin or rerun. This43 branch normally merged that
main; its production tree did not change. Current full-main and new43 production
deltas are therefore both `_compositor.py`42 added /73 deleted. The earlier
70 added /87 deleted union remains the historical pre-landing comparison.

## Final bounded native sanity

Parent authorized the final proportionate batch after source closure. Existing
system Python and native source were reused; no environment, provider or film
was created. Resource check reported warnings (home8.3GiB, RAM18.3GiB available,
swap9.3GiB used). The run was bounded by45 seconds:

```sh
PYTHONPATH=src PYTHONDONTWRITEBYTECODE=1 timeout45s python -m pytest -q -p no:cacheprovider tests/test_compositor_frame_damage.py
```

Actual command uses `timeout 45s`. The preserved native-sanity.log reports
**7 passed in0.69 seconds**, exit0. The batch covers:

- Resize damage remains within the newly published native frame (three cases).
- Original lazy geometry retains old and new caption damage.
- Both writers clip a partially selected wide cell without overwriting its
  untouched half; original segment metadata survives.
- Actual native App sparse damage borrows the original cuts, leaves unrelated
  row buckets empty, and publishes the known content only at the selected rows.
- Actual native App body capture retains nonzero original row coordinates.

No UI or protocol mock was introduced. Production is unchanged from0efe0803.
These checks do not establish installed readiness or performance. The remaining
boundary is Heisenberg399's ONE changed paired saved-session physical journey;
43 does not create another film or hold accepted397/14baa shipping. Neither
source closure nor old396/42 footage qualifies changed43 output.

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
