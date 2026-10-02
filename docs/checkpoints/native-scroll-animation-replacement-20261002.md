# Scroll requests replace a curve without painting its old destination

Heisenberg owns this native Widget/Animator change, directly granted by Kepler.
Same finishedText22 checkout, normally advanced to actualmain6405228; no new
worktree, dependency environment or native package. Joined Toad body/frame scope
remains with Heisenberg342; Kepler338 owns channel source controller hooks.

Read existing native Widget scroll_to/_scroll_to and all callers, Animator
animate/_animate/force_stop_animation, SimpleAnimation and ScalarAnimation. The
new destination already belongs to Animator._animate, which starts from the
current value and completes the replaced resource. Widget currently forces the
previous destination first, twice for a deferred animated request; _scroll_to
also cancels an axis the operation did not request. These are extra decisions
before the original animation owner can replace its curve.

Use the existing Animator replacement for animated delivery. Explicit unanimated
requests cancel only requested axes without first assigning the previous end.
Keep native callbacks and deferred after-refresh delivery. Do not reinterpret
reader restoration/geometry compensation as a new user scroll; WindowRestoration
already transforms the existing curve. No new animation store, clock, target,
policy throttle or controller. No change to animation speed/default FPS here.

Existing342 original saved-public recording supplies the source lead: held keys
coincide with active-force-stop events and readable discrete jumps. This is not
proof that every stop is wrong; legitimate new requests and compensation remain
distinct. AST selects all native andToad consumer sites, source determines intent.
Batched native sanity and one changed installed motion/profile check come last.
Source checkpoint WIP, not Ready; no smoothness, CPU gain or144Hz claim.

Full unfinished scope remains joined to Toad: lazy entry without interrupted
animation, CPU/144Hz, firstpaint/raster/warm/cold tabs, bounded3viewport adaptive
runway/reverse/idle/growingEnd/void, editor/draftUndo/focus, busy sidebar/IRC and
TC1/T9/T4. Original339/342 negatives and raw recordings stay protected.

## Published coherent source batch

The branch normally merged qualified native81ecfccd (Text30/31) into main29
6405228. PR30/31 were merged into their feature bases, so actual GitHub main29
alone did not include that qualified source. This branch carries both histories;
no selective reconstruction or source regression.

Three production files:53 lines deleted,42 added against81ec. Widget deletes
the early forced completion and delegates animated delivery to Animator, including
a request whose destination equals the current position. Explicit direct delivery
stops only its requested axes. Animator cancels the original scheduled Timer
when replaced, so an old delayed callback cannot reinstall a replaced curve.
The existing Animation base owns asynchronous stop plus callback invocation;
SimpleAnimation/ScalarAnimation supply their completed-value hook. The concrete
force-stop dispatch and duplicated leaf stop algorithms are deleted.

Existing NRA parsed525 native/Toad modules, matching525 sourcefiles, with zero
parse omissions;66 selected declaration/call sites are retained in the owned
source receipt. Attribute-call resolution remains semantic, not established by
AST alone. Existing native/source hooks and all force-stop callers were read.
This is published working source, not installed validation or smoothness Ready.
