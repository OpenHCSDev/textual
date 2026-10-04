# One layer inheritance decision in Widget, one native traversal

Same finished checkout normally joined Text51/main2fac. Source first: Widget.layers
and Compositor._arrange_root.get_layers independently choose the outermost authored
layer declaration. The compositor additionally maintains inherited_layers for every
visited node and recursive resolver custody until the scene completes.

Extend existing Widget behavior to resolve its authored declaration against the
original inherited order. Public layers and native layout traversal use that same
behavior. Carry original resolved order through existing add_widget/arrange_widget,
removing the recursive get_layers algorithm, per-pass inheritance map and duplicate
public selection. Preserve subtree key order, external-root ancestry, explicit empty
and default layer declarations, custom layers property behavior, detached nodes,
placement order, capture/projection lifetime and custom override context.

No new cache/map/type/flag/registry, no Toad edits, WT/env/native copy or film.
NRA Package AST covers entire native/Toad/tools roots before editing; omissions
and dynamic limitations explicit. Original420 ProfileTrace arrangement activation
is source context, not callcounts/CPU time/dominance. Batch affected native sanity
last, then one changed joined installed journey owned by Heisenberg; no unchanged
51 capture or physical speed claim. Full performance remains active.
