from pathlib import Path

import chromadb
from app.embeddings import get_embedding_model

from app.config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    DOCS_DIR,
)


def load_documents() -> list[dict]:
    documents = []

    for path in sorted(DOCS_DIR.glob("doc_*.txt")):
        text = path.read_text(encoding="utf-8").strip()

        documents.append(
            {
                "document_id": path.stem,
                "chunk_id": f"{path.stem}_chunk_00",
                "text": text,
            }
        )

    return documents


def get_chroma_client():
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(
        path=str(CHROMA_DIR)
    )


def build_vector_store():
    documents = load_documents()

    if len(documents) != 8:
        raise RuntimeError(
            f"Expected 8 documents, found {len(documents)}"
        )

    model = get_embedding_model()

    texts = [doc["text"] for doc in documents]

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
    ).tolist()

    client = get_chroma_client()

    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    collection.upsert(
        ids=[doc["chunk_id"] for doc in documents],
        documents=texts,
        embeddings=embeddings,
        metadatas=[
            {
                "document_id": doc["document_id"],
                "chunk_id": doc["chunk_id"],
            }
            for doc in documents
        ],
    )

    return collection


def get_or_create_collection():
    client = get_chroma_client()

    try:
        collection = client.get_collection(
            name=COLLECTION_NAME
        )

        if collection.count() == 8:
            return collection

    except Exception:
        pass

    return build_vector_store()


if __name__ == "__main__":
    collection = build_vector_store()

    print("Ingestion complete.")
    print("Collection:", COLLECTION_NAME)
    print("Documents indexed:", collection.count())