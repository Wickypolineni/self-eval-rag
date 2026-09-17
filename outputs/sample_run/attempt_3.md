# Introduction to RAG (Retrieval-Augmented Generation)

Imagine you ask a smart student a question. If they only know what is in their textbooks, they might not know about new things. They might also guess and give a wrong answer.

Computers that answer questions are similar. They are called "language models." They learn from a lot of text. But they have three problems:

1.  **Old knowledge:** They do not know about things that happened after they finished learning.
2.  **Secret knowledge:** They do not know about your company's private papers.
3.  **Making things up:** If they do not know an answer, they might still give a confident, but wrong, answer. This is called "hallucination."

RAG helps these language models. RAG stands for **Retrieval-Augmented Generation**. It is a method that helps a language model answer questions better. It does this by finding useful information *before* the language model answers.

## What RAG Is

RAG works like this: when you ask a question, RAG first **finds helpful text**. This text comes from outside the language model. Then, RAG **gives this text to the language model**. The language model then uses this text to create its answer.

Think of it like a student who can quickly look up information in a library *before* answering your question. The student himself does not change. He just gets new information to use.

RAG does not change the language model itself. It only changes the information the model sees when it answers a question.

## Why RAG Matters

RAG helps solve the three problems we talked about:

*   It can give the language model **new information**. This can be about recent events or private documents.
*   It **reduces** making things up (hallucination). The language model has real text to use, so it is less likely to guess. But it can still make mistakes or ignore the text.

With RAG, the language model's answer is more likely to be based on facts. You can also see where the information came from. This helps you trust the answer more. But remember, if the text RAG finds is wrong, the answer can still be wrong.

## How RAG Works: Two Main Parts

RAG has two main steps. One step happens ahead of time. The other step happens every time you ask a question.

### Part 1: Setting Up (Indexing Phase)

This part happens first, only one time (or when you add new documents). Imagine you have many books in a library. You want to make them easy to search.

1.  **Load Documents:** You take all your documents, like company reports or news articles.
2.  **Split into Chunks:** Each document is too big. So, you cut it into smaller pieces. We call these "chunks." Think of them as individual pages or paragraphs from a book. These chunks might slightly overlap, so no information is lost at the edges.
3.  **Create Embeddings:** For each chunk, a special computer program makes a "meaning number list." This list of numbers is called an **embedding**. It describes what the chunk is about. Chunks with similar meanings will have similar number lists.
    *   **What is an Embedding?** An embedding is a list of numbers that shows the meaning of a piece of text. Texts that mean similar things will have number lists that are close together. Texts with different meanings will have number lists that are far apart. This is like giving each book in a library a special code based on its topic.
    *   **How are Embeddings Made?** Another computer program, called an "embedding model," creates these number lists. It is not the same program that gives the final answer.
4.  **Store in a Vector Database:** You put all these chunks and their meaning number lists (embeddings) into a special storage. This is called a **vector database**. It is like a super-fast library catalog. It can quickly find chunks that are similar to your question.

### Part 2: Answering Questions (Querying Phase)

This part happens every time you ask a question. Imagine you go to the library and ask a question.

1.  **Embed Your Question:** First, your question is also turned into a "meaning number list" (an embedding) using the *same* program that made the chunk embeddings. This is important so the question and the chunks can be compared fairly.
2.  **Retrieve Top Chunks:** The vector database looks for the chunks whose meaning number lists are most similar to your question's meaning number list. It finds the best few matching chunks. This is like the librarian quickly finding the most helpful pages from different books for your question.
3.  **Augment the Prompt:** Now, your original question and the helpful chunks found by RAG are put together. They form a bigger message. This bigger message is called a "prompt." It also includes an instruction for the language model, like: "Answer the question using only the context below. If the context does not contain the answer, say you don't know." This step is the "Augmented" part of RAG.
4.  **Generate the Answer:** The language model reads this full prompt. It is told to use the helpful text to write an answer to your question. Because it has specific text to work from, its answer is more likely to be correct and factual. It also helps reduce made-up answers. However, the language model can still use its own knowledge or make mistakes, even with this instruction.

## Example: Finding a Refund Policy

Let's see how RAG works with an example.

**User Question:** "How do I get my money back if I am not happy with the product?"

### Setting Up (Indexing Phase - done already)

Imagine we have a document about a company's rules. This document was split into chunks. One chunk might be:

*   **Chunk 1:** "Our refund policy allows returns within 30 days of purchase. Products must be unopened and have the original receipt. To start a refund, visit our website and fill out the return form."

This chunk was turned into a meaning number list and stored in the vector database.

### Answering the Question (Querying Phase)

1.  **Embed Question:** Your question, "How do I get my money back if I am not happy with the product?", is turned into a meaning number list.
2.  **Retrieve Top Chunks:** The vector database compares your question's meaning number list to all the chunks' meaning number lists. It finds **Chunk 1** as the best match.
3.  **Augment the Prompt:** RAG creates a message for the language model. It looks like this:

    ```
    Text provided:
    "Our refund policy allows returns within 30 days of purchase. Products must be unopened and have the original receipt. To start a refund, visit our website and fill out the return form."

    User's question: How do I get my money back if I am not happy with the product?

    Instructions: Answer the question using only the context below. If the context does not contain the answer, say you don't know.
    ```

4.  **Generate the Answer:** The language model reads this message. It is told to use the refund policy text. It then writes an answer based on that text:

    "To get your money back, you must return the product within 30 days of buying it. Make sure the product is unopened and you have the original receipt. You can start the refund process by visiting our website and filling out the return form."

This answer is based on the information from Chunk 1. The model is told to use only this information, but it can sometimes use its own knowledge or make mistakes. You can also see that the answer came from the refund policy document.