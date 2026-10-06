# Pilot pointer delivery

Pilot now queues raw pointer packets on App and borrows the existing dispatch completion. App alone matches a press/release and supplies the final Click receipt and chain. Screen fills the original MouseEvent recipient when it actually routes through capture/current geometry; Pilot no longer keeps the first hit or authors Clicks. The gesture's screen coordinates are acquired after initial layout settlement and stay fixed across the press/release.

The existing completion future now carries the final message. Its release still occurs after dispatch and call-next work on the owning pump. Screen uses an offset event for its own delivery as it already does for child delivery, retaining the raw App packet's completion. A release consumes its press even if no click is admitted.

Current consumer/source evidence is in before.json (native production/tests and read-only Toad production/tests/tools; zero parse omissions). Arbitrary external subclasses/dynamic getattr are not resolved by lexical AST. The existing overridden test on_event now returns the original owner's result.

Source checkpoint; changed-path application checks are pending. Batch05 is preserved: its Shift click reported true but selected only batch-a. No click-time geometry was retained, so this source defect does not identify its sole cause. No Batch05 replay, installed pin change, provider or physical run.
