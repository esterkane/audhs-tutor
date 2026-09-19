---
title: Learning-rate schedules
---
## Warmup
Warmup increases the learning rate linearly from zero over the first few hundred to few thousand steps. It protects Adam from taking huge steps while its moment estimates are still unreliable.

## Cosine decay
After warmup the rate follows half a cosine down to a small floor. Cosine decay is the default for pre-training runs because it needs no tuning of step boundaries.

## One-cycle and constant
The one-cycle policy rises then falls within a single run and works well for short fine-tunes. A constant rate with a final short decay, sometimes called warmup-stable-decay, lets you extend training without deciding the total length up front.
