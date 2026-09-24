from app.embeddings import get_embedding_model

from app.ingestion import get_or_create_collection


class PolicyRetriever:
    def __init__(self):
        self.model = get_embedding_model()
        self.collection = get_or_create_collection()

    def retrieve(
        self,
        query: str,
        top_k: int = 3,
    ) -> list[dict]:

        query_embedding = self.model.encode(
            query,
            normalize_embeddings=True,
        ).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=[
                "documents",
                "metadatas",
                "distances",
            ],
        )

        chunks = []

        if not results["documents"]:
            return chunks

        for i in range(len(results["documents"][0])):
            metadata = results["metadatas"][0][i]

            chunks.append(
                {
                    "chunk_id": metadata["chunk_id"],
                    "document_id": metadata["document_id"],
                    "text": results["documents"][0][i],
                    "distance": results["distances"][0][i],
                }
            )

        return chunks