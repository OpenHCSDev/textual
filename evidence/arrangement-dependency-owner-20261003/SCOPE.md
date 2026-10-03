# Native arrangement dependency ownership

Stacked on qualified Text39 source95d3; its receipt and installed artifact remain
frozen. Same isolated checkout, no new environment or recording.

Widget.arrange currently owns _height_arrangement_cache, while
NativeLayoutHeight.depends calls the same arrangement dependency algorithm
outside that lifetime. Native auto-size and optimal-width measurement can walk
that child's dependency tree before arrange repeats the same question.
The existing Widget resource must own this question for every consumer.

Promote its acquisition to a Widget method; have both arrange and the native
measurement policy derive the answer there. Keep the genuinely different box
question and unknown/custom hooks conservative. Retain the original geometry,
child-list and layout mutation inputs. No second cache, map, class or policy flag.

Original384 profile at21.143s shows native box→content height→arrange→grid box;
this is source-path evidence, not CPU duration or proof of dominance. Reuse the
existing ProfileTrace and NRA Package parser. Source reasoning and whole-family
implementation precede one affected sanity batch; installed qualification joins
Heisenberg's next changed workflow, never a repeat of frozen384.

Heisenberg owns Toad/recording; Kepler owns native Widget/measurement consumers.
Full End, smoothness, channel first paint and CPU closure remain open.
