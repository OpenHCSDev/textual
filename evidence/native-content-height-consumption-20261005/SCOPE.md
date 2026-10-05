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

The initial published iterator source was
71e8c7fd4486b772252dafe7556b91e23a08fab9 (7 additions / 10 deletions).
The same owner now also yields each wrapped line directly: no complete
per-paragraph formatting list, intermediate truncated-content list, or
throwaway _FormattedLine solely for its content field. Original loop_last
supplies the last-line justification fact at construction instead of mutating
the last member of a completed list. Current production delta is 23 additions /
34 deletions in one file. Unrequested wrapped suffixes no longer construct
formatted lines or apply their truncation/padding. Original Content.split and
divide still acquire source slices and wrapping boundaries; neither is claimed
eliminated or height bounded.

The before AST covers 249 native production files / 460 native test files and
288 Toad production files / 397 test files / 41 tools with zero parse omissions.
It identifies one formatter declaration, three native production readers,
two native test count readers plus one monkeypatch, and ONE extra Toad private
reader: PathContent.render_strips in path_search.py. That reader slices the
formatter result and must migrate before qualification. Heisenberg owns this
Toad change, preserving original path shortening, nowrap/clip/tab8/left/zero
padding and RenderOptions through Content.render_strips. PreparedDiffLine
inherits the original rendering implementation without an override.

ONE final native source batch executed at
81ca92b137e3070b31abb5146b7bae6f8043e228, production tree
90f78e605a8dc1470d1de8c19220ab4b26474706: 348 PASS / 0 FAIL in 0.76s
(pytest), controller 2.499691362027079s, terminal 0. Original Content wrapping,
complete height measurement (including no available width), and public
bounded/full/negative rendering preserve strip cells, link/wide-cell/selection
metadata and post styles. Original log SHA256:
9c92eb8034b308320e4b038c3781be785dd0f3a557acc06d39b237548b1125a4.
Heisenberg has closed PathContent in source by delegating to Content.render_strips
with original leaf policy/options; its published successor and final source
closure evidence remain to bind. No installed App/frame/motion qualification
exists for Text70. Unregistered external private readers and runtime rebinding
are not proved by the AST.

The original recorded59.605 RichVisual stack does NOT identify Content or its
widget/invalidation cause. This independent unused-resource source finding is
not an attribution of that sample, a CPU share or a measured speedup.

AST complete production/dependency/test caller and override evidence precedes
editing; coherent source change then one affected control batch and joined
installed meaningful frame check. No App/build/installed/SDK/provider/media
purpose exists now. Text68/69 wheel a0c2 and qualification stay frozen.
