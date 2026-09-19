---
title: Human evaluation and LLM judges
---
## Human evaluation
Pairwise preference between two answers is more reliable than absolute scores. Give raters a rubric with concrete criteria and measure inter-rater agreement with Cohen's kappa.

## LLM-as-judge
A strong model can grade answers against a rubric at scale. Known biases: position bias (the first answer wins more often), verbosity bias (longer answers score higher), and self-preference. Swap the order and average to cancel position bias.

## Rubric-anchored grading
Ask the judge for per-criterion evidence quotes before a score. Bare scores drift; quoted evidence can be audited by a human.
