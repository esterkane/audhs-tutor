---
title: Retrieval metrics
---
## Recall at k
Recall@k is the fraction of relevant documents that appear in the top k results. For a RAG system recall@8 tells you whether the evidence the model needs was in the context window at all.

## Mean reciprocal rank
MRR averages 1 divided by the rank of the first relevant hit. It rewards putting a relevant chunk first, which matters when the prompt budget only fits a few chunks.

## Labelled query sets
Build a small labelled set: a query, the course and lecture that answer it, and a phrase the answer must contain. Twenty to fifty queries already catch most regressions when you change chunking or the embedding model.

## Citation coverage
Citation coverage is the share of answers whose claims point at a retrieved chunk. It is the metric that catches a tutor that answers from parametric memory instead of the course.
