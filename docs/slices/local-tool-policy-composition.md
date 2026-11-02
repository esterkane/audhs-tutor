# Local tool policy composition

The project adapter now assembles delivery policy separately from tool definitions. Previously a no-quiz directive appended after the definitions defeated suffix-based removal, sending the full tool schemas plus compact descriptions to the local model. The full schema is already supplied through constrained output.

The local path retains tool and field descriptions, safety annotations and validation constraints while removing the redundant structural copy. With the current complete tool catalogue this eliminates 3,771 duplicate characters for the affected request. This is an input-size measurement, not a measured decoding or end-to-end speedup. Hosted calls retain their full tool contracts exactly once.

A regression test reproduced the duplicate before the fix. Both ordinary and no-quiz local requests now preserve complete history, maximum output allowance, constrained tool validation and delivery instructions without duplication. A hosted regression verifies the full tool contract and no-quiz policy coexist. No retrieval evidence, saved history, answer text or factual guard is removed.
