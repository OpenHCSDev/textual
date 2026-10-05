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

The original recorded59.605 RichVisual stack does NOT identify Content or its
widget/invalidation cause. This independent unused-resource source finding is
not an attribution of that sample, a CPU share or a measured speedup.

AST complete production/dependency/test caller and override evidence precedes
editing; coherent source change then one affected control batch and joined
installed meaningful frame check. No App/build/installed/SDK/provider/media
purpose exists now. Text68/69 wheel a0c2 and qualification stay frozen.
