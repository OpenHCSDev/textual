# Keep box constraints with the original cached measurement

Same native checkout, stacked on qualified Text40. Its source0ab, Ready receipt
and installed artifacts remain frozen. No new environment/native build/movie.

Widget._get_box_model retains BoxModel in its existing bounded LRU, but selects
Widget._extrema only on cache misses. A width/height A→B→A cache hit therefore
returns A's model while alignment reads B's constraints through _arrange.
This is a source-supported mismatch; the profile shows this native measurement
path but does not establish its CPU duration or a live observed wrong alignment.

Retain the original model and original Extrema together in the existing cache
resource. Cache hits select the constraints from that exact original resource.
Keep pre-measurement constraint selection on misses: native auto-size measurement
can arrange children before the final box is calculated. Preserve public
BoxModel return/unpacking, custom resolvers, lifetime release and capacity.
No new class, map, cache, constraint algorithm, compatibility reader or geometry
policy. All private cache consumers and downstream alignment/box callers are
included; no Toad files are authored here.

AST/source first, coherent implementation then one affected sanity batch.
Any installed qualification joins Heisenberg's next changed workflow; no repeat
of qualified391/40 and no measured performance/End/FPS claim.
