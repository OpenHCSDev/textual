# Textual fork: Toad terminal presentation WIP (2026-09-23)

**Document-only WIP, not a performance implementation PR.** This isolated
branch is based on `OpenHCSDev/textual` `main` at
`06dbeef4bb70fb718236aa418ed658ef4667a126`. It adds **only this new
evidence file**; no dirty Textual compositor, style, selection, writer or test
source from `/tmp/opencode/toad-textual-perf` has been copied, committed, or
reviewed here. Do not merge, mark ready, deploy, or claim the **worst <16 ms**
terminal-emulator-presentation gate has passed.

This performance PR is separate from the [agent-comms core evidence draft][core]
and Toad's own UI/recovery WIP PR. At document preparation no Toad draft PR
URL was available; add its actual URL when created. `trissim/textual-window` is
neither this Textual fork nor a Toad runtime/package dependency: a Toad menu
docstring credits its interaction pattern only. No fourth PR is proposed.

[core]: https://github.com/OpenHCSDev/agent-comms/pull/1

## Owner intent, not an included diff

The Toad terminal UI is expensive under busy streaming conversations, focus
changes, selection, right-sidebar tabs, and cold channel/Recovery opens.
Maintenance's separate **dirty**, uncommitted Textual candidate at
`/tmp/opencode/toad-textual-perf`, branch `perf/strip-cache-allocation` rooted
at `06dbeef…`, had **24 status entries** at 18:48 UTC: 20 tracked modifications
and four untracked tests. The observed touched areas include compositor strip
and cache allocation, NodeList, CSS stylesheet/app-focus dependencies, styles,
selection rendering, Linux writer-thread and driver paths. Tracked diff stats
exclude the four new tests. These are inventory observations, **not** reviewed
source in this document's PR, upstream `Textualize/textual` changes, or an
authority to stage all dirty paths.

Owner-reported development evidence: a 60-second active multitab/focus profile
sampled 5,164 frames with no recorded errors and found app-focus restyling a
large inclusive cost. Interleaved same-scene **headless** focus transitions
were reported to improve ~245.46 ms median / 271.3 ms worst to 14.05 ms median
/ **17.61 ms worst** after candidate focus/dependency changes; 3,035 Textual
tests were reported passing on an owner-local candidate. These are not
independent stopped-byte PR results, and **even the headless worst is above
16 ms**. Historical Toad cold useful terminal pixels roughly 197–366 ms and
streaming/GC spikes remain above 16 ms. A successful trivial scene, `_display`
timing, PTY writes/queues, median, or headless rendering never proves the
strict terminal-presented worst-frame requirement.

## Honest source/performance gates

1. Owner `opencode-toad-maintenance` must stop current source/test edits,
   identify the complete exact attributable Textual subset against remote
   `main`, freeze hashes and scope, and authorize a separate isolated writable
   branch. Independently review compositor/style/focus/selection/writer
   semantics and all new tests before importing any code. Do not stage moving
   `perf/strip-cache-allocation` or the 24 dirty paths wholesale.
2. Re-run focused cache/focus/CSS/compositor/selection/strip/writer regression
   tests and representative Textual suite on those frozen bytes. Check
   rendering/pixel parity, selection, clipboard/history/input, writer fault
   handling and any OS-dependent behavior. Passing tests alone do not prove a
   terminal timing target.
3. In a separately reviewed compatible pinned Toad, collect repeatable
   **worst completed semantic frames actually presented as pixels by a real
   terminal emulator** over busy streaming, scrolling, selection, tab/sidebar,
   channel opens, and Recovery. Record per-scene maxima, instrumentation,
   emulator/machine and failures. Strict **worst <16 ms is currently FAIL /
   unproven**. If still above threshold, keep Draft and report bottlenecks
   rather than declaring success from the headless 17.61 ms observation.
4. Keep protocol correctness and UI responsibilities in their own repositories.
   Do not weaken agent-comms durable claims, add per-paint bus scans/fsync, or
   turn on publication/monitoring/retry/`SILENT` to improve a benchmark.

This draft does not change Toad's dependency pin, ship the Textual fork,
provide a production rollout, or authorize a merge. The current 24-path
candidate remains owner-controlled and outside this diff.
