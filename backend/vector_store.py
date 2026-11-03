import json
import logging
from typing import List, Optional
import chromadb
from chromadb.api.types import EmbeddingFunction, Documents, Embeddings
from sentence_transformers import SentenceTransformer

from backend.config import CHROMA_DIR, CHROMA_COLLECTION_NAME, EMBEDDING_MODEL_NAME, DATA_DIR
from backend.models import ProjectNote, ProjectNoteCreate

logger = logging.getLogger("vector_store")

class MiniLMEmbeddingFunction(EmbeddingFunction):
    """Custom ChromaDB Embedding Function using SentenceTransformer all-MiniLM-L6-v2."""
    def __init__(self, model_name: str = EMBEDDING_MODEL_NAME):
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def name(self) -> str:
        return f"sentence-transformers/{self.model_name}"

    def __call__(self, input: Documents) -> Embeddings:
        embeddings = self.model.encode(list(input), convert_to_numpy=True)
        return embeddings.tolist()

class VectorStore:
    def __init__(self):
        CHROMA_DIR.mkdir(parents=True, exist_ok=True)
        self.client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        self.embedding_fn = MiniLMEmbeddingFunction(EMBEDDING_MODEL_NAME)
        self.collection = self.client.get_or_create_collection(
            name=CHROMA_COLLECTION_NAME,
            embedding_function=self.embedding_fn,
            metadata={"hnsw:space": "cosine"}
        )
        self._ensure_default_notes_seeded()

    def _ensure_default_notes_seeded(self):
        """Seed default workshop project notes if collection is empty."""
        try:
            count = self.collection.count()
            if count == 0:
                default_file = DATA_DIR / "default_notes.json"
                if default_file.exists():
                    with open(default_file, "r", encoding="utf-8") as f:
                        notes = json.load(f)
                    
                    ids = [n["id"] for n in notes]
                    documents = [f"{n['title']}: {n['content']}" for n in notes]
                    metadatas = [
                        {
                            "title": n["title"],
                            "category": n.get("category", "General"),
                            "tags": ",".join(n.get("tags", []))
                        }
                        for n in notes
                    ]
                    self.collection.add(
                        ids=ids,
                        documents=documents,
                        metadatas=metadatas
                    )
                    logger.info(f"Seeded {len(notes)} workshop project notes into ChromaDB.")
        except Exception as e:
            logger.error(f"Error seeding default notes: {e}")

    def search_notes(self, query: str, n_results: int = 4) -> List[ProjectNote]:
        """Perform semantic vector search in ChromaDB using all-MiniLM-L6-v2 embeddings."""
        try:
            total_items = self.collection.count()
            if total_items == 0:
                return []
            
            n = min(n_results, total_items)
            results = self.collection.query(
                query_texts=[query],
                n_results=n,
                include=["documents", "metadatas", "distances"]
            )
            
            notes: List[ProjectNote] = []
            if results and results.get("ids") and len(results["ids"]) > 0:
                ids = results["ids"][0]
                docs = results["documents"][0]
                metas = results["metadatas"][0]
                distances = results["distances"][0] if results.get("distances") else [0.0] * len(ids)

                for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
                    similarity = max(0.0, min(1.0, 1.0 - dist))
                    tags_raw = meta.get("tags", "")
                    tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if isinstance(tags_raw, str) else []
                    
                    # Separate title if prefixed in document
                    title = meta.get("title", doc_id)
                    content = doc
                    if f"{title}: " in content:
                        content = content.replace(f"{title}: ", "", 1)

                    notes.append(ProjectNote(
                        id=doc_id,
                        title=title,
                        category=meta.get("category", "General"),
                        tags=tags_list,
                        content=content,
                        distance=round(dist, 4),
                        similarity=round(similarity, 4)
                    ))
            return notes
        except Exception as e:
            logger.error(f"Error querying ChromaDB: {e}")
            return []

    def list_all_notes(self) -> List[ProjectNote]:
        """List all stored project notes in ChromaDB."""
        try:
            total_count = self.collection.count()
            if total_count == 0:
                return []
            
            data = self.collection.get(include=["documents", "metadatas"])
            notes: List[ProjectNote] = []
            for doc_id, doc, meta in zip(data["ids"], data["documents"], data["metadatas"]):
                title = meta.get("title", doc_id)
                content = doc
                if f"{title}: " in content:
                    content = content.replace(f"{title}: ", "", 1)
                tags_raw = meta.get("tags", "")
                tags_list = [t.strip() for t in tags_raw.split(",") if t.strip()] if isinstance(tags_raw, str) else []
                
                notes.append(ProjectNote(
                    id=doc_id,
                    title=title,
                    category=meta.get("category", "General"),
                    tags=tags_list,
                    content=content
                ))
            return notes
        except Exception as e:
            logger.error(f"Error fetching all notes: {e}")
            return []

    def add_note(self, note: ProjectNoteCreate) -> ProjectNote:
        """Add a new project note with automatic vector embedding."""
        import uuid
        note_id = f"note-{uuid.uuid4().hex[:8]}"
        doc_text = f"{note.title}: {note.content}"
        meta = {
            "title": note.title,
            "category": note.category,
            "tags": ",".join(note.tags)
        }
        self.collection.add(
            ids=[note_id],
            documents=[doc_text],
            metadatas=[meta]
        )
        return ProjectNote(
            id=note_id,
            title=note.title,
            category=note.category,
            tags=note.tags,
            content=note.content
        )

    def delete_note(self, note_id: str) -> bool:
        """Delete a project note by ID."""
        try:
            self.collection.delete(ids=[note_id])
            return True
        except Exception as e:
            logger.error(f"Error deleting note {note_id}: {e}")
            return False

# Singleton instance
_store_instance: Optional[VectorStore] = None

def get_vector_store() -> VectorStore:
    global _store_instance
    if _store_instance is None:
        _store_instance = VectorStore()
    return _store_instance
