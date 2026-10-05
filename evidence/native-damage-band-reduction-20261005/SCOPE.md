# Reduce original damage intervals once per vertical band

Base: merged Text68 dd625069e50cc0b909832b549a485abc55067149.

The existing `Compositor._regions_to_spans` expands every damaged rectangle
into one interval per row, then sorts and merges the same active intervals
again on each row. Output rows are necessary; repeated interval acquisition
and union inside a band without rectangle edges is unnecessary work.

Keep that original reducer and its exact ordered output. Use rectangle start
and end edges to reduce active horizontal intervals once per changing vertical
band, then emit those original spans on each required row. Preserve overlap
multiplicity, touching intervals, gaps, negative origins and complete bounds.
No new retained resource, cache, map, timer, flag, type, API or Toad caller.

The complete Package AST before/after from Text68 is retained as caller
source evidence: native249/tests460 and Toad288/tests397/tools41 with0parse
omissions. The current reducer has four native callers and seven test callers;
all render paths continue to use the same owner. Dynamic private-method
rebinding and unregistered external callers remain unproved.

Source reasoning and coherent implementation first; final proportionate
interval and affected native App controls last. Native68 original14+2 controls
and negative are immutable, not rerun. No build/installed prefix/SDK/provider/
media purpose; no measured gain or physical cadence claim.
