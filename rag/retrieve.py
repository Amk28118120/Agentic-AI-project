"""
rag/retrieve.py

Loads the FAISS index and retrieves the most relevant document
chunks for a user's question.

Compatible with embed.py, which stores metadata:

{
    "source": "knowledge" | "user",
    "filename": "...",
    "text": "..."
}
"""

import pickle
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai

from config import GEMINI_MODEL


client = genai.Client()

PROJECT_ROOT = Path(__file__).resolve().parents[1]

INDEX_FILE = PROJECT_ROOT / "rag" / "index.faiss"

CHUNK_FILE = PROJECT_ROOT / "rag" / "chunks.pkl"

model = SentenceTransformer("all-MiniLM-L6-v2")


# --------------------------------------------------------
# Lazy loading
# --------------------------------------------------------

_index = None
_chunks = None


def load_index():
    """
    Loads the FAISS index and chunk metadata only when needed.
    """

    global _index, _chunks

    if _index is not None:
        return

    if not INDEX_FILE.exists():
        raise FileNotFoundError(
            f"FAISS index not found.\n"
            f"Run:\n"
            f"python rag/embed.py"
        )

    if not CHUNK_FILE.exists():
        raise FileNotFoundError(
            f"{CHUNK_FILE} not found."
        )

    _index = faiss.read_index(str(INDEX_FILE))

    with open(CHUNK_FILE, "rb") as f:
        _chunks = pickle.load(f)


# --------------------------------------------------------
# Retrieval
# --------------------------------------------------------

def retrieve(question: str, top_k: int = 4):

    load_index()

    embedding = model.encode(
        [question],
        convert_to_numpy=True,
    )

    embedding = np.asarray(
        embedding,
        dtype=np.float32,
    )

    distances, indices = _index.search(
        embedding,
        top_k,
    )

    results = []

    for idx in indices[0]:

        if idx == -1:
            continue

        results.append(_chunks[idx])

    return results


# --------------------------------------------------------
# Gemini
# --------------------------------------------------------

def answer_question(question: str) -> str:
    """
    Answers a question using retrieved context.
    """

    docs = retrieve(question)

    if not docs:
        return "No relevant documents were found."

    context = ""

    for doc in docs:

        context += (
            f"Source: {doc['source']}\n"
            f"File: {doc['filename']}\n\n"
            f"{doc['text']}\n\n"
            f"{'-'*60}\n\n"
        )

    prompt = f"""
You are an assistant for photonic crystal simulations and COMSOL.

Answer ONLY using the supplied context.

If the answer is not contained in the context, reply exactly:

I couldn't find that information in the available documents.

Context:

{context}

Question:

{question}
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
    )

    return response.text.strip()


# --------------------------------------------------------
# Standalone testing
# --------------------------------------------------------

if __name__ == "__main__":

    while True:

        q = input("\nQuestion: ")

        if not q:
            break

        print()

        print(answer_question(q))
