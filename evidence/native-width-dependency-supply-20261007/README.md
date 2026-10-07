# Native width declaration supply

Layout.get_content_width arranges at zero height: incoming height is unused,
but arrangement styles still matter. Its original HeightDependency declaration
now owns both answers through NativeOptimalWidth. The separate consumer override
in NativeWidgetWidth is deleted; shared NativeWidgetMeasurementHeight selects
container/leaf once and consumes the original compiled layout declaration.

IndependentHeight remains conservative about styles. Undeclared arrangers and
custom width methods still receive ContextHeight from Layout.__init_subclass__;
explicit custom declarations retain their own policies. Box and relative-height
resources, epochs, descendants, placement and raw style publication are unchanged.

Source checkpoint. No package/public operation or latency claim. Affected
source controls and one original loaded App measurement follow implementation.
