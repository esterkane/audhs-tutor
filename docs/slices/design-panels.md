# Shared panel design adoption

2026-10-04. Shared cards previously lifted every section with a shadow and used the same oversized title for panels and page headings. Cards now use the supplied 6px radius, plain bordered surface and optional theme-aware panel shadow. Home resume alone opts into lift. Shared panel headings use 16/24 and explicit h1 callers use 22/30; rem units preserve font scaling. Heading semantics and caller overrides remain intact.

Original verification: eight theme/width lesson journeys passed, with keyboard input, focus, large text at 390px and pause/resume draft retention; lint/types/build passed. Desktop lesson screenshot inspected, with flat surfaces and retained readable content. Existing bundle/worker warnings remain. No learning logic changed.

Remaining: interface/prose font system and broader shell adoption are unfinished. This does not rewrite arbitrary headings or nested content, and does not certify every page. Four original Home/resume cases passed; sanitized checkout passed all twelve lesson/Home cases.
