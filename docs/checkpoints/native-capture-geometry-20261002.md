# Native geometry during retained strip capture

Continue merged Textual24 using the existing Compositor capture and geometry
owners. Heisenberg grants render_subtree_strips, renderer geometry consumers,
StylesCache and Widget geometry within capture. He owns early registration,
viewport/layout timing and the Toad integration.

The original installed319/Text24 profile records:
render_subtree_strips -> _render_chops -> _get_renders -> StylesCache.render_widget
-> Widget.region -> find_widget -> _get_geometry -> full_map -> _arrange_root.
The strip renderer already has the body's complete native arrangement, but
descendant geometry queries independently select the screen-wide map.

Make the existing native geometry owner select the original arrangement used
by the active capture. Preserve absolute screen-coordinate Widget geometry,
original strip coordinates, invalidation and nested/failed capture lifetimes.
Reuse the existing arrangement resource; no second map, store, fake Screen,
copied widths, renderer or geometry cache. Migrate the complete shared lookup
family rather than special-casing StylesCache.

Read existing geometry/projection/lifetime owners and AST consumers first;
implement the coherent family and delete replaced decisions. Validate once at
the end using the existing native body family. Heisenberg owns the later changed
installed recording; no new environment, provider input or duplicate capture.

Ready checkpoint24 remains qualified and unchanged. Remaining discrete motion,
full-layout work and overall CPU targets are not closed by that checkpoint.
