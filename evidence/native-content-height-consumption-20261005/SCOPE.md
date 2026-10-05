# Bound native Content formatting at its original render height

Base: Text68/69 merged c1bcc8d33164553432f2a718eeddec1a1ffa4a5f.

Existing Content.render_strips calls its original _wrap_and_format owner for
ALL paragraphs / _FormattedLine resources before slicing that result to the
requested height. Visual's render height already declares which prefix is
needed; RichVisual bounds its own segment stream with islice, while Content
constructs the unused suffix first.

Make the existing Content formatting algorithm an iterator. Migrate its entire
consumer family: complete wrap and height measurement consume all; bounded
strip rendering consumes its required prefix; original negative slicing stays
complete before slicing. Public Visual/render_strips/list and wrap/list
contracts, source selection/link/wide-cell metadata and original Content.split
resource remain unchanged. Delete the unused complete formatted-result list.
No new class, cache, map, timer, flag, alternate renderer or Toad implementation.

Published native source: 71e8c7fd4486b772252dafe7556b91e23a08fab9.
The complete formatting list is deleted (7 additions / 10 deletions in the
production source at that checkpoint). Later unrequested paragraphs no longer
construct formatting resources. Original Content.split still acquires all
logical source lines, and a requested paragraph still formats its wrapped
lines together; neither is claimed eliminated.

The before AST covers 249 native production files / 460 native test files and
288 Toad production files / 397 test files / 41 tools with zero parse omissions.
It identifies one formatter declaration, three native production readers,
two native test count readers plus one monkeypatch, and ONE extra Toad private
reader: PathContent.render_strips in path_search.py. That reader slices the
formatter result and must migrate before qualification. Heisenberg owns this
Toad change, preserving original path shortening, nowrap/clip/tab8/left/zero
padding and RenderOptions through Content.render_strips. PreparedDiffLine
inherits the original rendering implementation without an override.

Native controls are authored, not executed: original height-measurement
expected counts consume the iterator; public bounded/full/negative render
comparisons retain strip cells, links, wide characters, selection and post
styles. The family remains unqualified until the PathContent closure and final
batched controls. Unregistered external private readers and runtime rebinding
are not proved by the AST.

The original recorded59.605 RichVisual stack does NOT identify Content or its
widget/invalidation cause. This independent unused-resource source finding is
not an attribution of that sample, a CPU share or a measured speedup.

AST complete production/dependency/test caller and override evidence precedes
editing; coherent source change then one affected control batch and joined
installed meaningful frame check. No App/build/installed/SDK/provider/media
purpose exists now. Text68/69 wheel a0c2 and qualification stay frozen.
