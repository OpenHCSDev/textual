# Native arrangement dependency ownership

Normally integrated merged main Text39 `2d1e2efa`; its receipt and installed
artifact remain frozen. Same isolated checkout, no new environment or recording.

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

## Working source checkpoint

Two production files: 23 added /16 deleted. Existing Widget now acquires its
original _height_arrangement_cache once per child-list, geometry and layout
epoch. NativeLayoutHeight.depends and Widget.arrange both consume that answer.
The standalone arrangement_depends_on_available_height algorithm and import
are deleted. The original presentation-retirement path still releases this
resource. Flow/Grid/Stream and custom hook declarations keep their existing
polymorphic algorithms; the separate box-dependency question is not collapsed
into arrangement dependency.

The before/after AST uses existing Package/ParsedModule across 249 native and
288 Toad production modules, zero parse omissions. The former free algorithm
has no remaining declaration/import/call; one Widget acquisition method and
one original resource write remain. AST does not establish dynamic receiver or
MRO resolution. Instance monkeypatches are outside the existing class-bound
measurement contract; no new compatibility path was introduced.

One affected final native sanity batch: 68 passed in4.97s. It exercises native
height/box/arrangement equivalence, grid tracks/extrema, inherited and structural
invalidations, unknown/custom hooks and cache retirement. Initial invocation
named a nonexistent test file, ran zero tests and is retained separately; this
was a command error, not a source behavior failure. No assertions were weakened,
no test harness or environment was created, no UI/provider run repeated.

Qualification remains pending Heisenberg's next changed installed workflow.
The original384 profile is partial and proves a matching source path, not a CPU
share or measured performance gain. Text39's scoped Ready receipt and frozen
installed source remain unchanged. End, discrete motion and channel first paint
remain open; this draft does not claim their closure.

Normal main integration298cbe3e9 retained production byte equality with d1bae228c.
No semantic conflict or affected source change; no repeated checks or recording.
The two-file follow-up is now based on main rather than the closed Text39 branch.
