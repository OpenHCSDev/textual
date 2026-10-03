# Stream native scene changes through the existing damage owner

Stacked after frozen scoped43. Same checkout and installed dependencies; no new
environment, recording, provider, scene map, cache, state flag or type.

Existing Compositor._damage_geometry will compare the original previous and
new scene maps, retain both old and new clipped damage, and derive resized
widgets in that same pass. Full reflow, viewport reflow and lazy full_map must
all consume it. Remove their three MapGeometry symmetric-difference producers
and full reflow's independent common-widget/resize classification. ReflowResult
and Screen's ordinary hide/show/resize behavior remain their existing owners.
MapGeometry.visible_region owns clipped damage rectangles.

NRA Package parses all249 native production modules, no omissions. Read the
existing MapGeometry, all three scene publications, geometry-query consumers,
Screen resize event delivery and damage-to-chop publication before editing.
Dynamic receiver resolution is not proven by AST. Pattern IMPL-12: delete the
repeated change algorithm through its existing owning class.

The original399 trace observes viewport reflow/arrangement during moving keys;
it does not establish this operation's CPU share. Semantic source shows eager
hashing and allocation of both complete maps' geometry records and a second
resize pass. Remove that work without altering legitimate layout/concurrency.
No measured gain claim. Final bounded native sanity and one changed installed
journey follow coherent source closure; do not rerun accepted399/43.
