# Native paint rectangle custody

Base: actual Textual main06771827eeff2a98c40a41fd2bc6cb6313db7a87.
Merged65 source, e253 wheel and all controls remain untouched.

The existing compositor paint mapping derives ordered widget paint from original
MapGeometry. It currently stores an unbounded clip and each cuts/render/chops
consumer re-intersects the same original region. Make `_paint_regions` own the
positive rectangle within original scene/capture bounds, then consumers borrow
that fact. Damage crop and foreground exposure are distinct later selections.
Raw MapGeometry, source order, geometry lookup, membership and retirement remain
their original owners. Existing layers are already cached per published scene;
complete widget membership remains necessary and is not removed.

Claims: `_paint_regions`, `_cuts_for_regions`, `_get_renders`, `_render_chops` and
related compositor paint-query consumers. No new type, field, map, flag, cache,
timer or alternate scene. Heis owns Toad body/frame consumers. Source only;
no App, package, provider, recording or gain qualification/purpose.

Complete roots and consumer evidence precede changes. Source semantics first,
coherent caller migration, then proportionate validation under an actual later
grant. Pattern IMPL-12: repeated geometry acquisition by related consumers.
