# Publish native style mutations from their existing owner

Reuse the finished native checkout; Text29 and Text30 remain frozen independently.

Styles owns its rule dictionary and mutation notification. Detached parse/serialization rule resources currently invalidate every native inherited-paint cache despite having no linked DOM node. reset/merge/merge_rules also publish a mutation when the original dictionary has not changed. RenderStyles delegates inline mutation to Styles but repeats bookkeeping for reset/merge_rules.

Read the existing style family and all callers first. Extend Styles to publish only actual changes through its original node relation; merge delegates the original rules merge algorithm. Keep real linked rule writes and their epochs immediate, including inside batch_update. Preserve refresh, animation, layout, ancestry and original subtree resource contracts. No new cache, epoch, type, deferred mutation or Toad change.

The 05 physical movie shows mounting/style/layout during discrete movement. It does not establish which work dominates a stall. This change removes confirmed unrelated invalidation, not a measured speed claim. Changed installed qualification belongs to Heisenberg's next combined workflow; no extra capture/provider/environment or unchanged gate.

Source/caller closure and deleted lines will be recorded with the implementation checkpoint. Proportionate affected sanity comes after coherent implementation, then the joined real application path.
