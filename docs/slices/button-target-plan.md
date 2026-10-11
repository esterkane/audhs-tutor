# Button visual size versus interaction target — 2026-10-11

Design-system PDF pp5/7/11 requires40px standard and32px compact visual controls,
with at least44px interaction targets. Existing Button has40/32px minimum heights,
no expanded pseudo target,and compact numeric controls can be narrower than44px.

Read-only sandbox at390px measured Start explanation145.36×40px and Energy1
31.81×32px. Adjacent energy controls start35.81px apart (4px layout gap). The native
button before/after pseudo content is none. One browser probe passed; this proves
measurements,not compliance. Probe/log:/tmp/button-target-scratch.spec.ts and
/tmp/button-target-baseline.log. No live preferences or model calls. Scratch removed.

A blanket negative-inset target can overlap compact neighbors. Do not ship that as
an accessibility fix. A physical44px button footprint with an inset visual surface
can preserve the requested visual sizes without overlapping hit regions,but requires
checking existing backgrounds,borders,pressed rings,disabled state and asChild links.
Documented before implementation because shared Button affects many surfaces.

Bounded next implementation:
- Establish semantic control size/target tokens and a44px layout footprint, retaining
  standard40px and compact32px visual treatment inside it. Preserve wrapping/large text.
- Keep native button/link semantics,form default type,focus,disabled and pressed states.
- Check CSS class overrides and linked Buttons before changing shared styling; avoid
  dropping caller classes or moving event handlers to decorative elements.
- Prove edge clicks activate only the intended control; adjacent energy controls do not
  overlap; keyboard activation and submission stay once-only. Do not change energy
  policy or learning state for visual tests (intercept writes/use disposable sandbox).
- Test all variants/sizes,long labels,asChild links,light/dark,118% text,320/390/1280px,
  reduced motion and focus visibility. Reuse existing dependencies and semantic tokens.
- Review code/pedagogy and publish both variants after the complete bounded slice.

No Button runtime change yet. The latest completed CI for d9b7ad9 passed; later
queued/running heads are not thereby verified. Do not create a status-only CI commit.

## Implemented and verified

Shared Button now owns a real44px minimum layout footprint (large remains48px).
Semantic control tokens define44/40/32px sizes. An inset pointer-transparent decorative
surface preserves standard/compact appearance; native event and focus targets remain
the outer button/link. Text can grow the control; no fixed height clips wrapped labels.
Borders,hover and disabled backgrounds are on the inset surface; pressed ring/native
button defaults and Slot composition remain intact. Existing caller margins retained.

593 frontend tests pass; full lint and production type/build pass.21 browser checks
pass across lesson layout,assessment clarity,companion button/Slot flows and token
specimens (light/dark/system,118% font,320/390/1280,keyboard,reduced motion). Layout
checks measure≥44px dimensions,nonoverlapping adjacent compact controls and native
hit testing in the outer top edge beyond the visual surface. Old computed-background
checks updated to inspect the actual pseudo surface; expected colors unchanged.
A viewport-relative geometry assertion was corrected after scrolling; no app change
was needed for that test issue. Narrow system-dark large-text screenshot inspected.
Bounded code review found no blockers/majors; learning logic and request handlers unchanged.

Limits: this covers shared Button,not every raw button/input/link in the application.
Physical touch,screen readers and human comprehension remain unverified. Larger physical
footprints may add wrapping/height; retain that tradeoff instead of overlapping hit areas.
