# Introduction to Retrieval-Augmented Generation (RAG)

## What is RAG?

Imagine you have a very smart friend. This friend knows many things. But this friend only knows what they learned in school. They do not know about new events. They also do not know about your family or your company.

Retrieval-Augmented Generation (RAG) is a way to help this smart friend. RAG gives your friend new information. This new information comes at the exact moment they need it. It helps them answer your questions better.

RAG does not change your smart friend's brain. It only changes what your friend sees. This helps your friend give more correct answers.

## Why RAG Matters

Your smart friend (a language model) has three small problems:

1.  **Old knowledge:** They do not know about anything that happened after their school time. For example, new news or new discoveries.
2.  **No private knowledge:** They do not know about your personal things. For example, your company's secret documents.
3.  **Making things up:** Sometimes, if they do not know an answer, they will guess. They might give a wrong answer, but it sounds very confident. This is called "hallucination."

RAG helps with all these problems. It gives the friend the exact text they need. This makes their answers more accurate. It also helps them make up fewer things. But it does not stop them from making up things completely.

## How RAG Works: Two Main Parts

RAG works in two main stages. Think of it like preparing a library, and then using it to answer questions.

### Phase 1: Indexing (Preparing the Library)

This part happens first. You do it once, before anyone asks questions. It is like organizing all the books in a library.

1.  **Load Documents:** First, you gather all the information you want your smart friend to know. These are like many books. For example, company policies, news articles, or personal notes.
2.  **Split into Chunks:** Each document (book) is often too big. So, you break it into smaller pieces. These small pieces are called "chunks." Think of them as pages or paragraphs from a book. Chunks are usually a few sentences long. If they are too small, they lose meaning. If they are too big, they might not be precise.
3.  **Embed Each Chunk:** Now, for each small piece of text (chunk), you create a special list of numbers. This list of numbers is called an "embedding." This embedding captures the meaning of the text. Texts that mean similar things will have similar lists of numbers. A special program, called an "embedding model," creates these numbers. This is not your smart friend (the language model).
    *Example: "How do I reset my password?" and "I forgot my login details" would have very similar embedding numbers because they mean almost the same thing.*
4.  **Store in Vector Database:** All these chunks and their special number lists (embeddings) are stored together. This is like putting all the organized books with their special meaning codes into a special shelf in the library. This special shelf is called a "vector database" or "vector store." It helps to find similar meanings very fast.

### Phase 2: Querying (Answering Questions)

This part happens every time someone asks a question. It is like a librarian finding the right books to answer you.

Here is how it works step-by-step:

1.  **Embed the Question:** When you ask a question, your question also gets its own special list of numbers (embedding). The same embedding model that made numbers for the chunks makes numbers for your question. This is important so everything matches.
    *Example Question: "How can I get my company email password again?"*
    *This question becomes a list of numbers.*
2.  **Retrieve Top Chunks:** The system looks in the vector database. It finds the chunks whose number lists (embeddings) are most similar to your question's number list. It finds the top few, maybe 3 to 10 chunks. These are the most relevant pieces of information.
    *Example Retrieval: The system finds chunks like "To reset your password, visit the IT helpdesk portal..." and "If you have forgotten your login details, click on 'Forgot Password'..."*
3.  **Build the Augmented Prompt:** Now, the system creates a special message for your smart friend. This message includes:
    *   An instruction: "Answer the question using only the information below. If the information does not contain the answer, say you don't know."
    *   The retrieved chunks (the relevant pieces of information).
    *   Your original question.

    *Example Prompt for the smart friend:*
    '''
    Answer the question using only the context below. If the context does not contain the answer, say you don't know.

    Context:
    1. To reset your password, visit the IT helpdesk portal at help.mycompany.com and follow the steps for password recovery.
    2. If you have forgotten your login details, click on 'Forgot Password' on the company login page. An email with a reset link will be sent to your recovery email address.
    3. For all other IT issues, please contact support at extension 123.

    Question: How can I get my company email password again?
    '''
4.  **Generate the Answer:** Your smart friend (the language model) reads this special message. It uses only the information given in the chunks to answer your question. Because it uses known sources, the system can also tell you which chunk the information came from. This helps you check the answer.

    *Example Answer: "To get your company email password again, visit the IT helpdesk portal at help.mycompany.com and follow the password recovery steps. You can also click 'Forgot Password' on the company login page, and a reset link will be sent to your recovery email."*

## RAG vs. Fine-tuning

RAG and fine-tuning are two ways to improve language models. They do different things.

| Feature             | RAG                                     | Fine-tuning                               |
| :------------------ | :-------------------------------------- | :---------------------------------------- |
| Changes model brain | No. It changes what the model sees.     | Yes. It changes the model's internal knowledge. |
| Update knowledge    | Re-index new documents. This is easy.   | Retrain the model. This is costly.        |
| Cite sources        | Yes. It can show where facts came from. | No. It cannot show sources.               |
| Best for            | Giving facts and fresh information.     | Changing the model's writing style.       |

They can also work together. A system might use both RAG and fine-tuning. This means RAG can provide facts, and fine-tuning can make the model answer in a specific style.
