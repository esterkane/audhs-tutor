# Local vector distance comparisons

Research requests comparing named source vectors can now calculate L2 distance, cosine distance and negative inner product locally. The existing dot-product/cosine-similarity path remains supported. Both paths preserve the original source, question and exchange history and never write assessment or mastery evidence.

Use a source such as:

```text
Vectors:
q=[1,0]
A=[2,2]
B=[1,0]
```

Ask: ``Compare L2 distance, cosine distance and negative inner product for query `q` with candidates `A` and `B`.`` The equivalent German request begins `Vergleiche L2-Abstand, Kosinusdistanz und negatives Skalarprodukt für Anfragevektor` and names the query and candidates in backticks.

The kernel computes exact rational squared L2 distances and negative inner products; cosine ranking uses sign-aware exact rational comparisons. Displayed L2 and cosine values are rounded. Undefined zero-vector cosine scores are excluded from ranking. The explanation labels this as local mathematics, not a database execution. Negative inner products can be negative, zero or positive.

Only complete supported requests use this path. Extra questions, unresolved issues, attached memories, unsupported material or oversized output preserve the normal tutor route. This does not replace fresh conceptual or causal explanations. Accepted calculation identity is versioned separately; older identities remain valid on save/resume.

Validation: kernel/API tests cover ordering, near-ties, zero vectors, history preservation, discussion/drafting, exact reuse and zero model calls. Four browser journeys cover uploaded source through research, writing, saving, reloading and review in English/desktop and German/narrow layouts. New distance response timings in one local run were 103 ms and 102 ms; these are not model-generation benchmarks or general latency guarantees.
