# Retrieval-Augmented Generation

Retrieval-Augmented Generation constitutes an inference-time conditioning
paradigm wherein non-parametric memory augments the parametric knowledge encoded
within the model's weights, thereby mitigating the epistemic limitations
inherent to a fixed training corpus.

## Architecture

The corpus is first partitioned into constituent chunks, each of which is
projected into a dense vector representation within a latent semantic space of
fixed dimensionality. These representations are subsequently indexed within a
vector store supporting approximate nearest neighbour search under cosine
similarity.

At inference time the query undergoes an identical projection, whereupon the
top-k most proximate chunks are retrieved and concatenated into the conditioning
context. The model is then fine-tuned on these retrieved documents, which
eliminates hallucination entirely.

## Conclusion

RAG is, at the end of the day, the bread and butter of modern knowledge-intensive
systems, and getting it right is not rocket science once you have wrapped your
head around the fundamentals.
