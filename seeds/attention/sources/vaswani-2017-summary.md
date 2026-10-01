---
title: "Attention Is All You Need (Vaswani et al., 2017) — section summaries"
source_type: doc
trust_tier: 2
course: "Attention Mechanisms (seed)"
section: "Paper summary"
uri: https://arxiv.org/abs/1706.03762
publication_date: 2017-06-12
---

## Model overview {skill: attn-multi-head}

The paper proposes the Transformer, a sequence-transduction model built entirely from attention and position-wise feed-forward layers, with no recurrence and no convolution. The encoder stacks six identical layers, each with a multi-head self-attention sublayer and a feed-forward sublayer, both wrapped in residual connections and layer normalisation. The decoder adds a third sublayer that attends over the encoder output and masks its self-attention so predictions for position i depend only on outputs before i.

## Scaled dot-product attention (section 3.2.1) {skill: attn-scaled}

The authors define attention on a set of queries, keys of dimension d_k and values of dimension d_v as softmax(QKᵀ / sqrt(d_k)) V. They compare additive and dot-product attention, note that dot-product attention is faster and more memory-efficient in practice, and observe that for large d_k the dot products grow large in magnitude and push the softmax into regions with extremely small gradients. The 1/sqrt(d_k) factor counteracts that effect; they motivate it by noting that the dot product of two vectors with independent unit-variance components has variance d_k.

## Multi-head attention (section 3.2.2) {skill: attn-multi-head}

Rather than a single attention with d_model-dimensional keys and values, the model linearly projects queries, keys and values h times with different learned projections to d_k, d_k and d_v dimensions, runs attention in parallel on each projection, concatenates the h outputs and projects once more. The base model uses h = 8 heads with d_k = d_v = d_model / h = 64, so the total cost is similar to single-head attention at full dimension. The stated benefit is that the model can jointly attend to information from different representation subspaces at different positions, which a single head's averaging would suppress.

## Masking in the decoder (section 3.2.3) {skill: attn-masking}

Self-attention in the decoder must preserve the autoregressive property. The paper implements this inside scaled dot-product attention by masking out, with −∞, all values in the softmax input that correspond to illegal connections to subsequent positions, so the output at each position can depend only on earlier positions.

## Positional encoding (section 3.5) {skill: pos-encoding}

Because the model contains no recurrence or convolution, it has no inherent notion of token order, so the authors add positional encodings to the input embeddings at the bottom of the encoder and decoder stacks. They use sine and cosine functions of different frequencies, with wavelengths forming a geometric progression from 2π to 10000·2π, chosen so that relative positions can be attended to via linear functions of the encodings. Learned positional embeddings performed nearly identically in their experiments; the sinusoidal version was preferred because it may extrapolate to longer sequences.

## Why self-attention (section 4) {skill: attn-dot-product}

The paper compares self-attention with recurrent and convolutional layers on three criteria: total computational complexity per layer, the amount of computation that can be parallelised, and the path length between long-range dependencies. Self-attention connects all positions with a constant number of sequential operations and a maximum path length of one, whereas recurrence needs O(n) sequential steps. Self-attention is cheaper than recurrence per layer when the sequence length n is smaller than the representation dimension d.
