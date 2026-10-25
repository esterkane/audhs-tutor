# Reference reuse, notebook inspection and CI recovery

## Scope — 2026-10-25

A local-model trial used the normal native structured-output gateway with full evidence and
unchanged target/context. Supplying a broad Python reference corrected one false claim, but
other replies introduced pointer wording or ambiguous tuple-content claims. A narrower trial
still contradicted itself in German. Both strategies were rejected; their raw outputs and
attempt receipts remain in private evaluation records. No general model, sampling, prompt,
context-window or decoding change is shipped, and no general accuracy/speed gain is claimed.

## Accurate local reference reuse

A small, reviewed bilingual answer now handles the explicitly recognized concept question:
does string immutability guarantee a fresh object, optionally distinguishing == and is?
The source is the [Python3.12 language reference](https://docs.python.org/3.12/reference/datamodel.html#objects-values-and-types).
It distinguishes an object's immutable value, a different value requiring a different string
object, and permitted reuse for the same type/value. It does not predict unspecified runtime
identity or invent allocations, internals or a learner mistake's origin.

Admission is deliberately narrow: Python/string context, one supported question, bounded source,
no selected personal memories, unresolved issue, custom class/operator or additional question.
A different explicit request retains the normal model path. No uploaded code is executed and
no context is dropped from the normal path. This is reference reuse, not an entailment classifier
or a calculation. English/German follow the selected response language; unchanged follows the
recognized question language. The answer is neutral reference prose rather than persona fiction.

Exchanges have an optional, versioned reference identity, exactly one of model/calculation/
reference. Old histories deserialize unchanged. Source snapshots retain the full selected
passage and the reference citation; signed exact-request reuse preserves saved replies. The
UI labels reference prose accurately, links the official reference, retains Sources(n), and
keeps paragraph use/edit/save/activation explicit. Broader requests remain editable. No model
call or hosted reservation is needed for an admitted reference answer. This removes generation
from this bounded path, not waiting time from general tutoring. No learning evidence changes.

## Notebook UI and read-only check

The optional Notebook requirements and exercise readiness panel checks the prepared working
copy only on a click. It separately reports standard-location imports not found, possible TODO/
ellipsis exercise cells, installation-command cells and partial static analysis. Cell numbers
count all notebook cells from1; exercise markers are not grades or proof a cell is unfinished.
The last check is labelled; edits require a fresh check. An available Jupyter service is distinct
from completed exercises, and package location is distinct from a successful runtime import.

The local-only, no-store GET/notebooks/check endpoint never prepares files, starts Jupyter,
installs dependencies or imports/runs course code. Bounded JSON/AST reads have file/cell/code/
import limits and reject path escapes/symlinks. An isolated -I/-S/-B Python metadata probe uses
the venv scheme explicitly (including Debian), locates module specs without importing them,
accepts only validated top-level names and is time-bounded. Local helper files are detected,
not executed. Raw source, outputs, paths, environment values and stderr are not returned.

Tests include executable-looking course code and a poisonous installed module: neither runs.
A real prepared copy remains byte-identical. A separate synthetic kernel imports scientific
libraries, computes a small fixture, saves/reloads a notebook and is shut down; no course cell,
installation, dataset training, HTML export or learner exercise is executed or auto-completed.

## CI failures addressed

Incoming f2b14d1: backend/frontend/migrations/bridge green; browser486passed/4failed.
Two authored-reading failures exposed stale session GETs replacing a confirmed sub-phase.
Checkpoint writes now cancel reads for both session caches without reverting later block
advances, and update only matching session/block identities. A controlled stale-read regression
retains assessment phase for live UI and resume. Histories and server ownership are unchanged.

A layout test compared a clock-dependent due-review count while a review became due. It now
compares the persisted identity, plan, mode, energy, checkpoint and complete block state.
The map keeps the accessible list, uses unique drawing-attempt IDs, ignores retired renders,
bounds drawing and offers Retry diagram after failure. Tests still require an actual SVG;
a retry is not accepted as a substitute for success. Reproduction coverage includes old/new
render ordering, failure/retry, cached-data recovery and keyboard navigation. The exact CI
map failure cause cannot be proven from the initial log alone; the new recovery is explicit.

## Verification

Backend full regression: 2,367 passed / 1 skipped, plus 89 affected tests after the final reference
wording/admission refinement. Ruff, format and strict mypy pass. Final frontend: 796 tests across
158 files pass; full ESLint, TypeScript and production build pass. Public schema/types are
generated from OpenAPI. Browser acceptance includes English/German research → paragraph → Write →
save/reload → Review, authored lesson → assessment → feedback → recap, notebook readiness and
map recovery. The initial broad browser run ended with 488 passed / 23 opt-in skipped / 3 failed:
an area-dialog focus-return timing assumption, a missing local Pyodide installation in the isolated
worktree, and an interrupted review transition while UI modules were being edited. The area test
now waits for the dialog's actual focus return before moving keyboard focus; it still requires
the correct URL and zero writes. The worktree uses the existing installed runtime, never a CDN.
The review transition did not reproduce on the stable final snapshot; no speculative transition
rewrite was retained. The final 24 affected browser journeys all pass, including all three failed
journeys, all four incoming CI failures, both design layouts and the complete learning flow.
This is a broad run plus an affected final rerun, not a claim of a second full-suite pass. Fresh
remote CI remains the separate release-snapshot regression gate.
Main data, keys, authoring cap and private archive are preserved.

## Optional quiet designs

The owner also requested changeable, removable interactive designs. The standalone Working
alongside page offers original Frost and Liquid SVG patterns, Off by default and saved only on
this device. A keyboard button changes a still pattern; there is no continuous animation, GPU
framework, package addition or new sound. One design loads on demand, and unmounts while tracked
tutor requests generate or when the page is inactive/embedded. Unit coverage exercises the
generation gate, off/device choice and input-driven changes. Browser coverage checks both
390/1280 layouts, reduced motion, choice/reload, keyboard input, Off, axe and horizontal reflow.
No tokens/sec comparison or cross-browser result is implied. See the authoritative
[comfort alignment](../design/COMFORT-LEARNING-ALIGNMENT.md#optional-quiet-designs--owner-request-2026-10-25).

## Limits

General local model hallucinations/repetition and decode time remain open. Reference admission
is not a substitute for broad reasoning; unmatched requests can still need factual review.
Static notebook analysis is partial and cannot certify all packages, dynamic imports, code,
exercise answers or runtime compatibility. Remaining course exercises stay learner-owned.
No Firefox/Safari, human screen-reader, original-course training or broader model-quality
acceptance is claimed. No new dependency, model download, graphics package or progress reset.
