import os
import json
import chromadb
import requests
from typing import List, Dict, Any

from config import (
    CHROMA_DIR,
    COLLECTION_NAME,
    JSON_FILE,
    EMBED_MODEL,
    LLM_MODEL,
    OLLAMA_HOST,
    HTTP_TIMEOUT_SECONDS,
)
from errors import RAGError, EmbeddingError, VectorDBError


class RAGEngine:
    def __init__(self):
        # Setup ChromaDB client and collection
        try:
            self.chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)
            self.collection = self.chroma_client.get_or_create_collection(name=COLLECTION_NAME)
        except Exception as e:
            raise VectorDBError(f"Failed to initialize ChromaDB: {e}")

    def _http_post(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{OLLAMA_HOST}{path}"
        try:
            resp = requests.post(url, json=payload, timeout=HTTP_TIMEOUT_SECONDS)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            raise RAGError(f"HTTP request to {url} failed: {e}")

    def get_embedding(self, text: str) -> List[float]:
        try:
            data = self._http_post(
                "/api/embeddings",
                {"model": EMBED_MODEL, "prompt": text},
            )
            emb = data.get("embedding")
            if not emb:
                raise EmbeddingError("No embedding returned from Ollama")
            return emb
        except RAGError:
            raise
        except Exception as e:
            raise EmbeddingError(str(e))

    def load_food_data(self) -> int:
        """Load data from JSON and add only new items to Chroma. Returns count of added docs."""
        if not os.path.exists(JSON_FILE):
            raise FileNotFoundError(f"Data file not found: {JSON_FILE}")

        with open(JSON_FILE, "r", encoding="utf-8") as f:
            food_data = json.load(f)

        try:
            existing = self.collection.get()
            existing_ids = set(existing.get("ids", []))
        except Exception as e:
            raise VectorDBError(f"Failed to read existing IDs from Chroma: {e}")

        new_items = [item for item in food_data if item.get("id") not in existing_ids]

        if not new_items:
            print("✅ All documents already in ChromaDB.")
            return 0

        print(f"🆕 Adding {len(new_items)} new documents to Chroma...")
        added = 0
        for item in new_items:
            text = item.get("text", "").strip()
            if not text:
                continue

            # Enhance text with region/type for embedding quality, keep original text as retrievable doc
            enriched = text
            region = item.get("region")
            ftype = item.get("type")
            if region:
                enriched += f" This food is popular in {region}."
            if ftype:
                enriched += f" It is a type of {ftype}."

            emb = self.get_embedding(enriched)

            try:
                self.collection.add(
                    documents=[text],
                    embeddings=[emb],
                    ids=[item["id"]],
                )
                added += 1
            except Exception as e:
                raise VectorDBError(f"Failed to add document {item.get('id')}: {e}")

        return added

    def rag_query(self, question: str, n_results: int = 3) -> str:
        # Step 1: Embed the user question
        q_emb = self.get_embedding(question)

        # Step 2: Query the vector DB
        try:
            results = self.collection.query(
                query_embeddings=[q_emb],
                n_results=n_results,
                include=["documents", "ids"],
            )
        except Exception as e:
            raise VectorDBError(f"Vector query failed: {e}")

        # Step 3: Extract documents and show sources
        top_docs = results.get("documents", [[]])[0]
        top_ids = results.get("ids", [[]])[0]

        print("\n🧠 Retrieving relevant information to reason through your question...\n")
        for i, doc in enumerate(top_docs):
            src_id = top_ids[i] if i < len(top_ids) else "?"
            print(f"🔹 Source {i + 1} (ID: {src_id}):")
            print(f"    \"{doc}\"\n")

        if not top_docs:
            return "I couldn't find relevant information in the knowledge base."

        print("📚 These seem to be the most relevant pieces of information to answer your question.\n")

        # Step 4: Build prompt from context
        context = "\n".join(top_docs)
        prompt = (
            "Use the following context to answer the question.\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )

        # Step 5: Generate answer with Ollama
        data = self._http_post(
            "/api/generate",
            {"model": LLM_MODEL, "prompt": prompt, "stream": False},
        )
        return (data.get("response") or "").strip()


def main():
    engine = RAGEngine()
    try:
        added = engine.load_food_data()
        if added:
            print(f"✅ Indexed {added} new document(s).")
    except Exception as e:
        print(f"⚠️  Initialization warning: {e}")

    print("\n🧠 RAG is ready. Ask a question (type 'exit' to quit):\n")
    while True:
        try:
            question = input("You: ")
        except EOFError:
            break
        if question.strip().lower() in ["exit", "quit"]:
            print("👋 Goodbye!")
            break
        try:
            answer = engine.rag_query(question)
        except RAGError as e:
            answer = f"An error occurred while processing your request: {e}"
        print("🤖:", answer)


if __name__ == "__main__":
    main()
