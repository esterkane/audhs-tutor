# Shared Disclosure — 2026-10-11

Design reference: complete design-system PDF pp5/7/11. Native lesson summaries had
no44px hit-area guarantee; reproduced Session plan summary height20px at390px.

Added a shared native details/summary component with a bordered token-based panel,
44px minimum summary target,existing Lucide16px/1.75-stroke chevron and wrapping label.
Open state rotates only its own direct chevron,without animation. Native keyboard,
focus,toggle and mounted child behavior remain; details props are forwarded. No library,
learning state,request or provider change. Adopted only Session plan and More ways to
learn; remaining disclosures are not claimed migrated. Larger targets use more space.

Evidence: before-change target assertion failed20<44. Final7 browser journeys pass:
320/390/1280 in light/dark (computed theme verified),44px targets,Enter toggle and onward
Tab,goal/action/narration order,labels/Undo,checkpoint preservation,Pause and assessment
context.12 Session/SessionControls unit tests,ESLint and production type/build pass;
existing build chunk warnings remain. Narrow dark screenshot inspected. Bounded code/
pedagogy review clear. Reduced motion set by browser harness; no new motion introduced.
Screen-reader,actual browser zoom,human comprehension and broader adoption remain open.
