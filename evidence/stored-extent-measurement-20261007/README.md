# Native line-surface measurement inputs

ScrollView measures its authored virtual_size, whose original Reactive writes
already request layout. Its two methods now declare that source through the
existing HeightDependency family. Computed or replaced virtual_size access and
undeclared method overrides remain context-sensitive.

Original ScrollBarRender changes colors without changing cell extent. ScrollBar
and its Blank corner now supply that fact through the existing renderer hook.
The live instance renderer is checked; custom renderers/wrappers stay opaque.
This completes the virtual-child supply which made the earlier ScrollView-only
candidate ineffective. No descendant traversal, style epoch, placement update,
refresh callback, size mutation or arrangement fence is bypassed.

Source checkpoint; affected App and custom-source checks have not run yet.
No package/public operation or latency claim. The actual recorded mount cost
remains unresolved until measured through its affected application.
