---
title: Perplexity
---
## What perplexity measures
Perplexity is the exponential of the average negative log-likelihood per token. A perplexity of 20 means the model is, on average, as uncertain as a uniform choice among 20 tokens.

## Why it is not enough
Perplexity depends on the tokeniser, so it is not comparable across models with different vocabularies. It also rewards fluent text over correct text: a confident wrong answer can have low perplexity.

## When to use it
Use perplexity to track pre-training progress and to detect regressions after quantisation. Do not use it to compare instruction-tuned models on task quality.
