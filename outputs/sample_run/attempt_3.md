## What is RAG? (Retrieval-Augmented Generation)

RAG is a smart way to make computer programs that talk (like ChatGPT) give better answers. Imagine you are in an exam. If you do not know an answer, you might guess. But if you can look in your book, you can give a correct answer. RAG helps the computer program "look in its book."

### 1. Why RAG Matters: Fixing Computer Program Problems

Computer programs that talk are called "language models." They learn from a lot of text, like books and websites. But they have some problems:

*   **Old Information:** They only know what they learned up to a certain date. They do not know about new events. Like an old textbook, it does not have the newest news.
*   **No Secret Information:** They do not know your family's secrets or your company's private letters. They only know public information.
*   **Making Things Up:** Sometimes, if they do not know the answer, they will just invent one. This made-up answer sounds real, but it is wrong. We call this "hallucination."

RAG helps by supplying relevant and up-to-date information from outside text at the moment of the question. This usually reduces mistakes, but the information found can be wrong, and the model can still make errors.

### 2. Embeddings: Turning Words into Numbers

Imagine you have many pictures. You want to find pictures that look similar. How would you do it? Maybe you group them by color or shape.

Computers do something similar with words. An "embedding" is a list of numbers that shows the meaning of a piece of text. Like a special code for words.

*   **Meaning in Numbers:** If two pieces of text mean similar things, their number lists (embeddings) will be very close to each other. If they mean different things, their number lists will be far apart.
*   **Special Helper:** A different computer program creates these embeddings. It is not the same program that gives the final answer.
*   **Not the Text Itself:** The embedding is just numbers. You cannot get the original words back from the numbers. The original words are stored separately, like how a library keeps both the book and its catalog card.

### 3. The Vector Store: Finding the Right Information

Think of a big library. When you ask the librarian for a book on "history of India," she does not read every book. She looks at the catalog cards to find the right books quickly.

A "vector store" is like that library catalog for embeddings. It stores all the number lists (embeddings) of many pieces of text. It also stores the original text next to its embedding.

Here is how it finds information:

1.  **Your Question Becomes Numbers:** First, your question is also turned into a list of numbers (an embedding) using the *same* special helper program.
2.  **Searching for Matches:** The vector store quickly looks for text pieces whose number lists are most similar to your question's number list. It finds the "closest" meanings.
3.  **Getting the Best Pieces:** It then picks the top few pieces of text that are the best matches. These are the most relevant parts of the "book" for your question.

Before storing, long documents are broken into smaller parts called "chunks." This is like breaking a big book into chapters. It helps find very specific information. If the chunks are too small, they lose meaning. If they are too big, they might have too much useless information.

### 4. Augmentation: Adding the Information to the Question

Now the computer program has your original question and the best pieces of information from the vector store. This is like you asking a question, and someone handing you the correct pages from a book.

"Augmentation" means adding these retrieved pieces of text to your question. The system puts them together into one big message. It also tells the language model: "Use *only* this information to answer the question. If this information does not have the answer, say you don't know."

This combined message is what the language model actually sees.

### 5. Generation: Writing the Answer

Finally, the language model reads the big message (your question + the extra information).

*   **Smart Answering:** It is told to use the provided information to write a good answer. This instruction is a guardrail, not a guarantee. The model can still use its own knowledge or misread the context. So, RAG reduces but does not eliminate incorrect answers. Because it has the facts, it is less likely to make things up.
*   **Showing Sources:** Since the system knows exactly which pieces of text it used, it can even tell you where the information came from. This is like a student showing which page number they found an answer on. This helps you trust the answer.

### 6. RAG in Action: A Worked Example

Let us see RAG work step-by-step with an example. Imagine you have a company document about "Leave Policy."

**Step 1: Indexing (Preparing the Information)**

First, we prepare our company's "Leave Policy" document. This happens once, before anyone asks questions.

*   **Original Document:**
    '''
    **Company Leave Policy**

    Employees are entitled to 15 days of paid annual leave. To request leave, employees must submit a leave application form at least 7 days in advance to their manager. For sick leave, a doctor's note is required for absences longer than 2 days. Unused annual leave cannot be carried over to the next year and will be forfeited.
    '''

*   **Chunking:** The document is broken into smaller parts (chunks). For this example, let us imagine two chunks:
    *   **Chunk 1:** "Employees are entitled to 15 days of paid annual leave. To request leave, employees must submit a leave application form at least 7 days in advance to their manager."
    *   **Chunk 2:** "For sick leave, a doctor's note is required for absences longer than 2 days. Unused annual leave cannot be carried over to the next year and will be forfeited."

*   **Embedding:** Each chunk is turned into a list of numbers (an embedding) by a special embedding program. The exact numbers are very long, but imagine them like this:
    *   Embedding for Chunk 1: `[0.1, 0.5, 0.2, ...]`
    *   Embedding for Chunk 2: `[0.8, 0.3, 0.9, ...]`

*   **Storing:** These chunks and their embeddings are saved in our vector store.

**Step 2: Querying (Answering a User's Question)**

Now, a user asks a question:

*   **User Question:** "How many days of annual leave do I get?"

*   **Embed the Question:** The user's question is also turned into a list of numbers (an embedding) using the *same* embedding program:
    *   Embedding for Question: `[0.12, 0.48, 0.23, ...]`

*   **Retrieve Chunks:** The vector store compares the question's embedding to all the stored chunk embeddings. It finds that Chunk 1 is the most similar because its meaning is closest to the question.
    *   Retrieved Chunk: "Employees are entitled to 15 days of paid annual leave. To request leave, employees must submit a leave application form at least 7 days in advance to their manager."

*   **Augment the Prompt:** The retrieved chunk is added to the user's question. The system creates a message for the language model:
    '''
    Answer the question using only the context below. If the context does not contain the answer, say you don't know.

    Context:
    Employees are entitled to 15 days of paid annual leave. To request leave, employees must submit a leave application form at least 7 days in advance to their manager.

    Question: How many days of annual leave do I get?
    '''

*   **Generate the Answer:** The language model reads this combined message and is told to answer based on the provided context. 

    *   **Model's Answer:** "You are entitled to 15 days of paid annual leave."

This example shows how RAG uses the company's specific document to answer a question accurately, even if the language model did not know this specific detail before.

So, RAG helps language models give more accurate and up-to-date answers by giving them relevant information at the right time. It is like giving a student an open book for an exam, but only opening it to the correct pages for each question. It does not change the student's brain, it just gives them better tools to answer.