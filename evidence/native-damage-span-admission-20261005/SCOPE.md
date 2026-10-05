# Keep original damage spans through native paint admission

Source base: merged Text67 d7337ee084f6dcda42cbd8a41c7417e87d60ae78.

`Compositor.render_partial_update` already owns exact nonoverlapping damaged
horizontal spans. It passes only row membership into `_render_chops`, which
allocates every cut on each dirty row inside the broad damage union. Separated
horizontal damage therefore asks intervening foreground content to render;
`ChopsUpdate` only removes that work later when publishing exact spans.

Use the existing `ChopsUpdate` cut-boundary owner for both compositor admission
and terminal / Rich publication. Carry original spans through every full,
partial, inline/export and subtree-capture caller. Preserve layer order,
wide-cell splitting, source metadata, clipping and exposure. Delete the
row-only reduction and separate cut-selection calculation. No new map, cache,
flag, timer, class, scene backend or Toad implementation.

NRA/refactor-audit IMPL-12: one damage/cut relation calculated differently at
paint admission and publication. AST before/after will cover all native and
Toad production, test and tool callers, with parsing and dynamic limits explicit.

Source reasoning and complete implementation precede proportionate affected
controls. Installed saved-history motion/CPU improvement is unqualified. No
build, environment, installed package, provider or recording purpose exists.

## Working checkpoint

Production: 68a9755b411819090283f180a362bf7659757b01.
Authored affected App controls: 4b5076efbd4c6f02fa53990e082fee96ed530a07.
One production file: 29 added / 23 deleted lines against merged Text67.

- `ChopsUpdate._span_cuts` is the sole damaged-span/cut-cell selector.
  The original Unicode-aware Strip crop remains at final publication.
- `Compositor._render_chops` admits those original cells before exposure and
  `Widget.render_lines`; both exposure and strip assignment retain membership
  in that same admitted chop resource.
- All four callers migrate: full update, partial update, render_strips (inline /
  export), and nonzero/negative-origin subtree capture. Full capture and ordinary
  full update still admit their complete bounds. render_strips retains the
  original scene row limit when a requested size exceeds the published scene.
- Deleted the damaged-row predicate and the separate terminal cut-selection
  algorithm. The existing geometry/cut maps and front-to-back order are intact.

`before.json` covers native production249/tests460 and Toad
production288/tests397/tools41, all parse omissions0. `after.json` covers the
changed native production249/tests460, omissions0; unmodified dependency
consumer evidence is retained at its original pinned source. Four render-chop
callers, one span-cut declaration, zero old dirty-row predicates. Syntactic AST
queries do not prove arbitrary runtime rebinding or unregistered external
private-method consumers.

## Remaining qualification

Source-only / Draft. The new actual-native App controls are authored but UNRUN.
They check that horizontal damage islands do not render the intervening pane,
with output parity against the same scene's full strips, including mid-wide-cell
edges, links and disjoint / overlapping damaged rows. Existing frame resize,
partial vertical redraw, layered exposure and original subtree-coordinate
controls cover the other changed callers. One final bounded affected family
batch is sufficient; accepted Text67 controls are not part of it.

No installed prefix, wheel, UI movie, provider or public mutation was attempted.
No causal CPU gain, measured cadence, smoothness or whole-workflow readiness is
claimed. All scene members are still walked to select layered candidates, and
full-frame cut construction cost is unmeasured; this removes unnecessary content
painting, not those legitimate traversal/geometry operations.
