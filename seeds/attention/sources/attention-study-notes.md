---
title: Attention Mechanisms — Study Notes
source_type: doc
trust_tier: 2
course: "Attention Mechanisms (seed)"
section: "Notes"
uri: seeds/attention/sources/attention-study-notes.md
publication_date: 2026-09-19
---

## Dot product as similarity {skill: vec-dot-product}

The dot product of two vectors a and b is the sum of the products of their entries: a·b = Σ a_i b_i. Geometrically it equals |a||b|cos θ, so for fixed lengths it is largest when the vectors point the same way, zero when they are orthogonal, and negative when they oppose each other. That is why a dot product can be read as "how much do these two vectors agree".

Two things change its size without changing direction. Scaling either vector scales the product: (2a)·b = 2(a·b). And dimension matters when entries are random: if each entry of a and b has mean zero and unit variance, the products a_i b_i are independent with variance one, so the sum over d dimensions has variance d. In 512 dimensions a typical dot product is around ±22 (sqrt(512)) rather than around ±1. This growth with dimension is the fact that makes scaled attention necessary.

## Softmax as a weighting function {skill: softmax}

Softmax turns a vector of real scores s into positive weights that sum to one: softmax(s)_i = exp(s_i) / Σ_j exp(s_j). Adding the same constant to every score leaves the output unchanged; only differences between scores matter. For scores [1, 2, 3] the weights are roughly [0.09, 0.24, 0.67].

When the gaps between scores are large, softmax saturates: [10, 20, 30] gives weights close to [0, 0, 1]. Saturation has a training cost. The derivative of softmax with respect to its inputs shrinks toward zero when one output is near one and the rest near zero, so gradients flowing back through a saturated softmax are tiny. Dividing the scores by a temperature T > 1 softens the distribution; multiplying by a factor > 1 sharpens it.

## Dot-product attention: queries, keys, values {skill: attn-dot-product}

Attention answers the question "which other positions should this position read from, and what should it read?". Each position produces three vectors from its input x through learned matrices: a query q = x W_Q (what am I looking for), a key k = x W_K (what do I offer to be matched on), and a value v = x W_V (what content do I return if matched).

For one query, the score against every key is the dot product q·k_j. Softmax over the scores gives attention weights α_j that sum to one. The output is the weighted sum of the values, Σ_j α_j v_j. Keys are only used to decide the weights; values are what actually gets mixed into the output. In matrix form for all queries at once: Attention(Q, K, V) = softmax(QKᵀ) V.

Worked example with two tokens. Let q = [1, 0], K = [[1, 0], [0, 1]] and V = [[5, 5], [0, 10]]. Scores are q·k_1 = 1 and q·k_2 = 0. softmax([1, 0]) ≈ [0.73, 0.27]. The output is 0.73·[5, 5] + 0.27·[0, 10] = [3.65, 6.35]. The query matched the first key more strongly, so the output leans toward the first value.

## Scaled dot-product attention {skill: attn-scaled}

Because dot products grow with dimension, raw scores in a d_k-dimensional key space have variance about d_k when q and k have unit-variance entries. With d_k = 64 the scores have standard deviation 8, which is enough to push softmax into saturation: one weight near one, the rest near zero, and tiny gradients. Dividing every score by sqrt(d_k) restores unit variance, keeping softmax in its useful, soft range.

The full formula is Attention(Q, K, V) = softmax(QKᵀ / sqrt(d_k)) V. The factor is a fixed constant, not a learned parameter, and it is applied before softmax. For d_k = 256 the scale is 1/16.

## Multi-head attention {skill: attn-multi-head}

Instead of one attention with d_model-dimensional queries and keys, multi-head attention runs h independent attentions in parallel, each on a lower-dimensional projection. Head i has its own matrices W_Q^i, W_K^i, W_V^i that map the d_model input to d_k = d_model / h dimensions. With d_model = 512 and h = 8, each head works in 64 dimensions. The h outputs are concatenated back to 512 dimensions and passed through a final projection W_O.

Why several small heads rather than one large head? Each head can specialise in a different relation: one may track syntactic dependencies, another positional neighbours, another coreference. A single softmax can only produce one weighting per query, so one head cannot attend sharply to two different positions for two different reasons at the same time. Multiple heads make that possible at roughly the same total compute as one full-width head.

## Masking: padding and causal {skill: attn-masking}

Two situations require some positions to be ignored. A padding mask hides the filler tokens that pad shorter sequences in a batch so they receive no attention. A causal (look-ahead) mask, used in decoders and decoder-only language models, hides future positions so that position i can only attend to positions ≤ i. For a length-4 sequence the causal mask is a lower-triangular pattern: row 1 sees column 1; row 2 sees columns 1–2; and so on.

Masks are applied to the scores before softmax by adding −∞ (in practice a very large negative number) to the masked entries. Because exp(−∞) = 0, the masked positions drop out of the normalisation and the remaining weights still sum to one. Setting weights to zero after softmax would leave the other weights summing to less than one, and setting scores to zero instead of −∞ would leave the masked positions with real, non-zero weight.

## Positional encoding {skill: pos-encoding}

Attention is permutation-equivariant: shuffle the input tokens and the outputs shuffle the same way with identical values, because scores depend only on the content of queries and keys. Without extra information the model cannot tell "dog bites man" from "man bites dog". Positional encoding fixes this by adding a position-dependent vector to each token embedding before the first layer.

The original transformer used fixed sinusoidal encodings: for position pos and dimension index i, the encoding alternates sin(pos / 10000^(2i/d_model)) and cos(pos / 10000^(2i/d_model)). Low indices vary quickly with position and high indices vary slowly, so together they form a multi-frequency code that lets the model compare relative offsets with simple linear operations. Learned absolute embeddings are an alternative; relative schemes such as rotary embeddings encode the offset between positions directly in the attention scores.

## KV cache in autoregressive decoding {skill: kv-cache}

A decoder generates one token at a time. With a causal mask, the keys and values of earlier positions never change when a new token is appended, so recomputing them every step is wasted work. The KV cache stores, for every layer and head, the key and value vectors of all previous tokens. At each step only the newest token's query, key and value are computed; its key and value are appended to the cache and its query attends over the cached keys. Per-step cost falls from O(n²) to O(n) in the sequence length.

The cache is the main memory consumer at inference time. Its size is layers × 2 (keys and values) × sequence length × (heads × head dimension) × bytes per element. For 32 layers, a hidden size of 4096, a 4096-token context and fp16 (2 bytes), that is 32 × 2 × 4096 × 4096 × 2 ≈ 2.1 GB for a single sequence. Grouped-query attention reduces the cache by sharing keys and values across heads.
