"""
rag/embed.py

Builds the FAISS index for the COMSOL Copilot.

Indexes PDFs from BOTH:

documents/
    knowledge/
    user/

Outputs:

rag/
    index.faiss
    chunks.pkl
"""

from pathlib import Path
import pickle

import faiss
import fitz  # PyMuPDF
import numpy as np
from sentence_transformers import SentenceTransformer


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOCUMENTS_DIR = PROJECT_ROOT / "documents"

KNOWLEDGE_DIR = DOCUMENTS_DIR / "knowledge"

USER_DIR = DOCUMENTS_DIR / "user"

INDEX_FILE = PROJECT_ROOT / "rag" / "index.faiss"

CHUNK_FILE = PROJECT_ROOT / "rag" / "chunks.pkl"


model = SentenceTransformer("all-MiniLM-L6-v2")


def chunk_text(text, chunk_size=800, overlap=150):
    chunks = []

    start = 0

    while start < len(text):

        end = min(start + chunk_size, len(text))

        chunk = text[start:end].strip()

        if chunk:
            chunks.append(chunk)

        start += chunk_size - overlap

    return chunks


def read_pdf(pdf_path: Path):

    doc = fitz.open(pdf_path)

    text = ""

    for page in doc:

        text += page.get_text()

    doc.close()

    return text


def load_documents():

    all_chunks = []

    folders = [
        ("knowledge", KNOWLEDGE_DIR),
        ("user", USER_DIR),
    ]

    for source, folder in folders:

        if not folder.exists():
            continue

        for pdf in folder.glob("*.pdf"):

            print(f"Reading {pdf.name}")

            text = read_pdf(pdf)

            chunks = chunk_text(text)

            for chunk in chunks:

                all_chunks.append(
                    {
                        "source": source,
                        "filename": pdf.name,
                        "text": chunk,
                    }
                )

    return all_chunks


def build():

    chunks = load_documents()

    if len(chunks) == 0:

        print("No PDF files found.")

        return

    texts = [c["text"] for c in chunks]

    print(f"Creating embeddings for {len(texts)} chunks...")

    embeddings = model.encode(
        texts,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    embeddings = np.asarray(
        embeddings,
        dtype=np.float32,
    )

    index = faiss.IndexFlatL2(
        embeddings.shape[1]
    )

    index.add(embeddings)

    faiss.write_index(
        index,
        str(INDEX_FILE),
    )

    with open(CHUNK_FILE, "wb") as f:

        pickle.dump(chunks, f)

    print("\nDone!")

    print(f"Indexed {len(chunks)} chunks.")

    print(f"Saved index to {INDEX_FILE}")

    print(f"Saved metadata to {CHUNK_FILE}")


if __name__ == "__main__":

    build()
