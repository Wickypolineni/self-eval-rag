# Introduction to Retrieval-Augmented Generation (RAG)

This lesson will teach you about RAG. RAG helps computer programs answer questions better. We will learn:

1.  **WHAT RAG IS:** What does RAG mean?
2.  **WHY RAG MATTERS:** Why is RAG useful?
3.  **HOW RAG WORKS:** How does RAG do its job?

---

### 1. WHAT RAG IS

RAG stands for **R**etrieval-**A**ugmented **G**eneration. It is a way to make special computer programs called **large language models** (LLMs) more helpful.

*   A **large language model** (LLM) is a computer program that can understand and create human-like text. Think of it like a very smart student who has read many, many books. It can write stories, answer questions, and even help you write emails.

RAG helps these LLMs answer questions using extra information, like looking up facts in a library book. This makes their answers more accurate and up-to-date.

### 2. WHY RAG MATTERS

RAG solves three main problems that large language models have:

**Problem 1: Old Information (Knowledge Cutoff)**

Imagine your smart student (the LLM) only read books published before last year. If you ask about something that happened this year, they won't know. This is called **knowledge cutoff**.

*   **Knowledge cutoff:** Large language models learn from data up to a certain date. They do not know about new events or information after that date.

**How RAG helps:** RAG lets the LLM look at new documents, like today's newspaper, to find the latest information. So, it can answer questions about recent events.

**Problem 2: Forgetting or Making Things Up (Hallucination)**

Sometimes, the smart student might forget a detail or even make up an answer if they are not sure. This is called **hallucination**.

*   **Hallucination:** When a large language model gives information that sounds correct but is actually false or made up.

**How RAG helps:** RAG makes the LLM check facts in reliable documents. It's like asking the student to always show you which book and page they got their answer from. This makes the answers more trustworthy and reduces hallucination.

**Problem 3: Not Knowing Private Information**

The smart student learned from many public books. But they don't know your family's private information, like your home address or your company's secret plans. LLMs also don't know private or company-specific documents.

**How RAG helps:** RAG lets the LLM read your company's private documents (if you give them permission). So, it can answer questions about your company's specific rules or products, even if that information is not public.

### 3. HOW RAG WORKS

Imagine you have a big library (your documents) and you want to ask a smart student (the LLM) a question. RAG works in four main steps:

1.  **Indexing:** Arranging the library books so they are easy to find.
2.  **Retrieval:** Finding the right books for your question.
3.  **Augmentation:** Giving the books to the student along with your question.
4.  **Generation:** The student reads the books and answers your question.

Let's look at each step with an example.

**Example:** You work for a mobile phone company. A customer asks, "How do I return my phone if it's broken?" Your company has a special document with its return policy.

#### Step 1: Indexing (Preparing Your Documents)

Before the LLM can find information, we need to prepare all the documents. Think of this like a librarian organizing books in a library.

*   **Documents:** These are the pieces of information RAG can use. They can be web pages, company manuals, articles, or even private notes.

First, we break down large documents into smaller pieces. These smaller pieces are called **chunks**.

*   **Chunk:** A small, manageable part of a larger document. It's like breaking a big book into many small chapters or paragraphs.

For our example, the company's "Return Policy" document might be broken into chunks like this:

*   **Chunk 1:** "Our return policy allows returns within 30 days of purchase."
*   **Chunk 2:** "To return a broken phone, you must first contact customer service."
*   **Chunk 3:** "Once customer service approves, you will receive a return shipping label."
*   **Chunk 4:** "Refunds are processed within 5-7 business days after we receive the returned item."

Next, we turn each chunk into a special number code. This code helps the computer understand the meaning of the chunk. These number codes are called **embeddings** or **vectors**.

*   **Embedding** (or **Vector**): A list of numbers that represents the meaning of a word, sentence, or document chunk. If two chunks have similar meanings, their embeddings will be very similar.

Think of it like giving each book chapter a unique shelf number and also a code that describes its topic (e.g., "History-Ancient Rome" or "Science-Physics"). Chapters about similar topics will have similar codes.

These embeddings are then stored in a special database called a **vector store**.

*   **Vector store:** A special database that stores embeddings (number codes) and helps find similar ones very quickly. It's like a super-fast index for our library, but instead of words, it uses these number codes.

So, for our example, Chunk 1's embedding (number code) would be stored in the vector store, Chunk 2's embedding, and so on.

#### Step 2: Retrieval (Finding Relevant Information)

When you ask a question, RAG first turns your question into an embedding (number code), just like it did for the document chunks.

*   **Query:** The question you ask the large language model.

Your question: "How do I return my phone if it's broken?"

This question becomes its own embedding (number code).

Then, RAG uses this question's embedding to search the **vector store**. It looks for document chunks whose embeddings are most similar to the question's embedding. This is like finding the books in the library whose topic codes match your question's topic code.

*   **Retrieval:** The process of finding the most relevant document chunks from the vector store that are related to your question.

This search is very fast thanks to something called **Approximate Nearest Neighbour (ANN) search**.

*   **Approximate Nearest Neighbour (ANN) search:** A quick way to find items (like embeddings) that are very similar to a given item, even in a very large collection. It's "approximate" because it finds very good matches quickly, not necessarily the absolute perfect match every time, but it is usually good enough.

For our example, when you ask, "How do I return my phone if it's broken?", the vector store might find these top two chunks as most relevant:

*   **Retrieved Chunk A:** "To return a broken phone, you must first contact customer service." (This was Chunk 2 from before)
*   **Retrieved Chunk B:** "Our return policy allows returns within 30 days of purchase." (This was Chunk 1 from before)

#### Step 3: Augmentation (Adding Information to the Question)

Now, RAG takes your original question and the retrieved chunks. It combines them into a single message for the large language model. This is like giving the smart student your question and the specific library books they need to read to answer it.

*   **Augmentation:** The process of adding the retrieved relevant information to the original question before sending it to the large language model.

This combined message is often called a **prompt**.

*   **Prompt:** The instruction or question given to a large language model, often including extra information to help it generate a better answer.

For our example, the prompt sent to the LLM would look something like this:

```
Answer the following question using ONLY the provided context. If the answer is not in the context, say "I don't have enough information to answer this question."

Context:
Retrieved Chunk A: "To return a broken phone, you must first contact customer service."
Retrieved Chunk B: "Our return policy allows returns within 30 days of purchase."

Question: How do I return my phone if it's broken?
```

#### Step 4: Generation (Answering the Question)

Finally, the large language model receives this augmented prompt. It reads the context (the retrieved chunks) and your question. Then, it uses its knowledge and the provided context to generate a helpful answer.

*   **Generation:** The process where the large language model creates a human-like text answer based on the given prompt and context.

It's like the smart student reading the specific pages you gave them and then writing down the answer using that information. Because the student (LLM) has the relevant books (chunks), its answer will be correct and specific to your company's policy.

For our example, the large language model would generate an answer like this:

"To return a broken phone, you must first contact customer service. Our return policy allows returns within 30 days of purchase."

This answer directly uses the information from the retrieved chunks. This makes the answer accurate and reliable, just like if the student told you exactly which book and page their answer came from.
