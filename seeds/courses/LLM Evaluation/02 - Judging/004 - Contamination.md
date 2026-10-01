---
title: Benchmark contamination
---
## What contamination is
Contamination means the test questions, or paraphrases of them, were in the training data. Scores then measure memorisation rather than ability.

## Detecting it
Check n-gram overlap between the benchmark and the training corpus, or test whether the model can complete a benchmark question verbatim from its first half.

## Avoiding it
Prefer benchmarks published after the model's training cutoff, or private held-out sets that are never posted online.
