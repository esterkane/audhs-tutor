# Named visual connections — Ask renderer prerequisite

Inspection of Ask and the reusable relationship renderer exposed a semantic gap:
the trusted renderer input had no named edge contract or text connection list.
Incoming authored visuals require named relationships; unlabeled arrows alone do
not preserve their meaning. This is a prerequisite, not completed Ask generation.

The shared renderer now requires edge labels, numbers canvas connections and provides
an ordered literal-text list through a native keyboard-accessible disclosure.
The existing synthetic leakage experiment supplies explicit fit/transform relations.
No mathematical values, answers, grading, session state or routing changed. No new
library. Colors use existing tokens; no animation or audio was added.

The new relationship-text test failed before the fix, then passed. Initial desktop
and narrow browser checks passed, but inspecting the narrow screenshot revealed
full canvas labels overlapping. Replaced them with compact numbers tied to the list;
final screenshots and browser checks must be inspected before acceptance.

Code/pedagogy review found no blockers or majors; reviewer did not rerun checks.
Owner comprehension and Ask integration remain open. Next: server-resolved Ask target
preview and explicit local visual generation, then inline draft/review/history using
this renderer. Do not substitute a disabled button or manual editor for generation.

Final evidence: 660 frontend tests pass; make lint and production build pass
(existing bundle-size warning remains). Two sandbox Chromium journeys pass at
390/1280 pixels, including keyboard disclosure, dynamic leakage relation, assessment
regression, reduced motion, axe, no horizontal overflow, dark media and 200% root
text-size reflow. Desktop/narrow and narrow dark/text-zoom screenshots inspected.
These are text-size checks, not a claim of native browser zoom or screen-reader
certification. The fixed canvas scales down on narrow views; the text list remains
readable. Large arbitrary authored graphs and actual Ask integration remain untested.
Backend unchanged: reuse prior 1510-test gate rather than rerun.
