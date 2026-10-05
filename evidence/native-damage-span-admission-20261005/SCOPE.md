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
