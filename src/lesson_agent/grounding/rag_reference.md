# Grounding Reference: Retrieval-Augmented Generation (RAG)

> **Purpose.** This file is the evaluator's source of truth for gate G5 (factual accuracy).
> The judge checks the generated lesson *against this document*, not against its own
> recollection. Without it, "is this accurate?" collapses into one model's opinion of
> another model's output — the exact failure mode this system exists to prevent.
>
> Keep this file short, factual, and conservative. Every claim here should be
> uncontroversial. When the lesson and this file disagree, this file wins.

---

## 1. What RAG is

Retrieval-Augmented Generation (RAG) is a technique that improves a language model's
answers by **retrieving relevant external text at query time and placing it into the
model's prompt** before the model generates a response.

The model itself is not changed. No weights are updated. RAG is an *inference-time*
technique: it changes what the model is shown, not what the model is.

The term was introduced in the 2020 paper *"Retrieval-Augmented Generation for
Knowledge-Intensive NLP Tasks"* (Lewis et al., Facebook AI Research).

## 2. The problem RAG solves

A language model trained on a fixed dataset has three limitations:

1. **Knowledge cutoff.** It knows nothing about events after its training data ends.
2. **No private knowledge.** It has never seen your company's internal documents.
3. **Hallucination.** When it lacks a fact, it may generate a fluent, confident,
   and wrong answer rather than declining to answer.

RAG addresses all three by supplying the needed text at the moment of the question.
It **reduces** hallucination; it does not eliminate it. A model can still misread or
contradict correctly retrieved text.

## 3. Embeddings

An **embedding** is a list of numbers (a vector) that represents a piece of text's
meaning. Texts with similar meaning produce vectors that are close together in
mathematical space; unrelated texts produce distant vectors.

Key points:
- Embeddings are produced by a separate model (an *embedding model*), not by the
  chat model that writes the final answer.
- Closeness is measured with a distance/similarity metric — most commonly **cosine
  similarity**.
- A typical embedding has a few hundred to a few thousand dimensions (e.g. 384,
  768, 1536). The exact number depends on the embedding model.
- Embeddings capture *semantic* similarity, not keyword overlap. "How do I reset my
  password?" and "I forgot my login details" embed closely despite sharing few words.

## 4. Chunking

Documents are split into smaller passages ("chunks") before embedding, because:
- Whole documents are usually too large to fit in a prompt.
- A smaller chunk gives a more precise match to a specific question.

Chunk size is a trade-off: chunks that are too small lose surrounding context; chunks
that are too large dilute the match and waste prompt space. Chunks often overlap
slightly so that a sentence spanning a boundary is not lost.

## 5. Vector store and retrieval

A **vector database** (or vector store) holds the chunks alongside their embeddings
and supports fast similarity search.

The retrieval step:
1. Embed the user's question using the **same embedding model** used for the chunks.
   (Using a different model would place the question in an incompatible space.)
2. Search the store for the chunks whose embeddings are nearest to the question's.
3. Return the top *k* matches, where *k* is a chosen number, commonly 3–10.

At realistic scale this search is *approximate* (ANN — approximate nearest neighbour),
trading a small amount of accuracy for large speed gains. Common vector stores include
FAISS, Chroma, Qdrant, Weaviate, Milvus, and pgvector.

RAG does not require a vector database. Keyword search (such as BM25) is a valid
retriever, and **hybrid search** combines keyword and vector retrieval. Vector search
is the most common choice, not the only one.

## 6. Augmentation

The retrieved chunks are inserted into the prompt along with the user's question,
usually with an instruction such as: *"Answer the question using only the context
below. If the context does not contain the answer, say you don't know."*

This assembled prompt is what the model actually receives. This step is the
"augmented" in Retrieval-Augmented Generation.

The instruction to refuse when the context is insufficient is an important guardrail,
though it is not perfectly reliable.

## 7. Generation

The language model reads the augmented prompt and writes an answer grounded in the
supplied text. Because the source chunks are known, the system can **cite** them,
letting a user verify the answer — a property a bare language model cannot offer.

## 8. The two phases

RAG has two distinct phases, and conflating them is a common error:

**Indexing (offline, done ahead of time):**
load documents → split into chunks → embed each chunk → store in the vector database

**Querying (online, per user question):**
embed the question → retrieve top-k similar chunks → build the augmented prompt →
generate the answer

Indexing happens once (and on updates). Querying happens on every question.

## 9. RAG vs fine-tuning

| | RAG | Fine-tuning |
|---|---|---|
| Changes model weights | No | Yes |
| Updating knowledge | Re-index documents | Retrain |
| Cost of an update | Low | High |
| Can cite sources | Yes | No |
| Best suited to | Supplying facts | Teaching style, format, behaviour |

These are complementary, not competing. A system may use both.

## 10. Common misconceptions to check the lesson against

Each of these is **false**. If the lesson asserts one, gate G5 fails.

- ❌ "RAG retrains or fine-tunes the model on your documents."
  → RAG never changes model weights.
- ❌ "RAG eliminates hallucination."
  → It reduces hallucination. The model can still err on retrieved text.
- ❌ "RAG requires a vector database."
  → Keyword and hybrid retrieval are valid.
- ❌ "Embeddings are generated by the chat model."
  → A separate embedding model produces them.
- ❌ "Embeddings store the text itself" / "an embedding is a compressed document."
  → An embedding is a numeric representation of meaning. The original text is stored
    alongside it; it cannot be reconstructed from the vector.
- ❌ "Retrieval searches for matching keywords."
  → Vector retrieval matches meaning. Keyword matching is a different retriever.
- ❌ "The question and the chunks can use different embedding models."
  → They must share an embedding space.
- ❌ "RAG is a model" / "RAG is a type of language model."
  → RAG is an architecture/technique that combines retrieval with a language model.
