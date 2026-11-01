# ADR 0025: Explicit hosted explanations for demonstrated local project gaps

Status: accepted by owner instruction, 2026-11-01

## Context

Local project tutor evaluations found unsupported SQLSTATE names, incomplete concurrency outcomes
and excessive generation latency. Better embeddings and decoding experiments did not qualify those
local answers. The owner authorized OpenAI or Anthropic tutoring when local accuracy is insufficient.
This extends the earlier authoring-only permission; a configured credential alone is not opt-in.

## Decision

Offer local/OpenAI selection for fresh Supabase/PostgreSQL explanations. The choice persists on
the learner, changes atomically, and is visible on the project page. Missing credentials or a missing
shared budget reject setup without changing the previous choice. Missing registry defaults may be
inserted; existing owner-edited values are preserved and verified against model/price/context bounds.
Anthropic transport has the same scope protection, but its UI selection awaits real qualification.

The project adapter remains the only protocol bridge. The normal gateway records every attempt,
reserves budget before transport, and counts failures with unknown billing conservatively. Authoring
and project study share one daily cap, reservation lock and all-provider ledger, not two allowances.
No other task routing changes. Embeddings, accepted reading and reviewed-answer reuse remain local.

A server-created request-local permit binds exact messages, registry identity, provider and expiry.
Only the gateway's bounded schema repair can extend it. A key, provider registration, client metadata,
or model assignment alone grants no transport permission. Raw histories and source provenance stay
stored; opting in permits the project request, retrieved references and session context to be sent to
the selected provider. No transcript deletion or factual rewriting is used to satisfy a schema.

Long-context study has separate conservative registry price ceilings. Its larger request bound is
available only inside the matching active permit; short-context authoring retains its previous bound.
Hosted explanation text must exclude protocol metadata; schema failures use normal logged repair.

Database mechanism retrieval includes version-matched engine-manual evidence alongside framework
context, with original chunk identities, explicit product filters and result limits preserved. A real
framework/manual conflict demonstrated why source scope matters as well as model capability.

Neutral discussion does not initiate quizzes or assessments. Explicit teaching remains available;
its application questions must follow a complete explanation. Snapshot explanations distinguish
per-transaction views from equal observed values using official PostgreSQL documentation.

## Validation and limits

Qualification requires real reference-grounded answers, held-out cases, history preservation,
provider setup/failure/resume browser checks, budget tests and the existing learning workflow.
Transport readiness and passing mocked responses alone do not establish factual quality. Report
measured timings as samples, not latency guarantees. Hosted models can still make mistakes; this
decision does not declare broader local or hosted factual accuracy complete.

The Claude Code review bridge remains separate and requires specific human consultation approval.
No private transcripts, credentials, uploads or runtime configuration may be published.
