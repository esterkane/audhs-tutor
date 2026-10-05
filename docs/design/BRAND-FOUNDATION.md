# Brand foundation and design-system assessment

Owner request: analyze the authoritative design system and include colors, fonts and a logo. This extends the uploaded system; it does not replace its workspace/navigation direction.

## Assessment and implementation

The existing runtime already matched the uploaded core light/dark palette. It lacked eleven supporting semantic colors, bundled typefaces, a product mark and a product browser-tab identity. Added the missing accent/status tints, operational danger colors, code colors and scrim in light, explicit dark and system-dark themes. These are reusable tokens, not scattered component hex values. Evidence-state aliases remain deferred because color must not invent mastery or verified capability.

| Role | Light | Dark | Use |
| --- | --- | --- | --- |
| Page | #f7f8fc | #1d1e24 | Quiet ground |
| Panel | #ffffff | #25262e | Grouped content |
| Primary text | #343741 | #dfe5ef | Reading and headings |
| Secondary text | #5e6673 | #a1a8b5 | Supporting information |
| Accent | #0b64dd | #5aa5f0 | Primary action, links, focus, logo |
| Success | #0f7a5a | #5fc2a0 | Confirmed saved/ready state with words |
| Attention | #9a5f00 | #e5b046 | Reconsideration, uncertainty with words |
| Danger | #bd271e | #f08682 | System failure, never learner mistakes |

Decorative borders are not control boundaries. Faint text remains restricted to disabled/placeholder presentation; it must not carry instructional content. Color never replaces text status. This slice does not claim every existing screen has migrated to all tokens.

## Typography

Inter is the interface and reading family; Roboto Mono is the code family, matching the uploaded family specification. Upright and italic Inter plus upright variable Roboto Mono are bundled locally, unchanged, with SIL OFL licenses and commit-pinned source URLs/SHA-256 hashes in frontend/public/fonts/provenance.json. No Google Fonts/CDN request is introduced at runtime. font-display:swap retains immediate fallback text; system fallbacks remain available if files fail. Fonts total about924KB before transport compression and load on use.

Keep the existing16px reading base and large-text preference. The upload contradicts itself by specifying11px labels while declaring a12px floor; do not adopt11px instructional labels. Do not shrink all existing controls to14px as a collateral change. Page/panel type tokens already exist; complete their adoption per screen after usability verification. Roboto Mono italic is not bundled, so italic code may use browser synthesis.

## Logo

Original vector mark: an open book with two paths converging on a shared idea. It represents connecting knowledge and exploring alternatives without medical symbolism or an achievement claim. The wordmark reads AuDHS Tutor. Header SVG uses the theme accent and card tokens, is decorative beside the accessible wordmark, and has no animation. The matching favicon replaces the generic starter asset and adapts to browser light/dark preference. Browser title is AuDHS Tutor before route-specific updates.

Minimum mark size32px in the header; preserve its square aspect ratio and at least one stroke-width of clear space. Keep the wordmark for navigation clarity. The mark is a new project asset, not an asset claimed to originate in the upload; owner aesthetic acceptance remains open.

## Verification and boundaries

Eleven original browser journeys passed: light/dark at390/1280, local font loading, computed family/background, no external font/image requests, brand keyboard Home link, and existing search/menu/recovery journeys. Lint/types/production build passed with inherited bundle/worker warnings. Theme tests set the root theme directly to isolate rendering; they do not certify the preferences flow. Full-site accessibility,200% zoom, screen-reader and human aesthetic/readability acceptance remain separate gates. Learning logic and model routing are unchanged.

Final sanitized4 brand journeys also pass. Dark narrow and light desktop screenshots inspected; read-only review found no blockers/majors. Upstream Roboto Mono license retains its original trailing whitespace to preserve the pinned asset bytes.


2026-10-05 accessibility follow-up:320px with200% root text enlargement exposed the quick-menu Close button scrolling away. Dialog heading/Close now sit outside its scrolling content. Final enlarged-text and font-failure journeys pass in both checkouts; screenshot inspected. Original six-brand baseline passed; final relevant two rerun after layout refinement. Lint/types/build pass with inherited warnings. This is text enlargement, not browser zoom or complete accessibility certification. No learning logic changes.


2026-10-05 Library typography: Search, Sources and saved-answer list/detail h1 now use existing22/30 page-title token; Search panels use16/24 heading token. No semantic, prose or behavior changes. Original13 search/brand journeys, lint/types pass; sanitized6 source/answer journeys pass using8011/5175 because8010 was occupied. Dark narrow screenshot inspected; read-only review clear. Other screen headings remain a separate adoption step.
