"""Chroma-backed semantic retrieval for KEDB and historical incidents."""
from __future__ import annotations
import hashlib
from pathlib import Path
import chromadb
from chromadb.utils import embedding_functions
from itsm_service import list_kedb, list_resolved_incidents

ROOT = Path(__file__).resolve().parent
CLIENT = chromadb.PersistentClient(path=str(ROOT / ".chroma"))
_EMBEDDER = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")


def _text(record: dict, kind: str) -> str:
    if kind == "kedb":
        return " | ".join(str(record.get(k, "")) for k in ("title", "application", "symptoms", "root_cause", "workaround", "resolution"))
    return " | ".join(str(record.get(k, "")) for k in ("title", "application", "symptoms", "resolution"))


def _collection(kind: str):
    return CLIENT.get_or_create_collection(name=f"itsm_{kind}", embedding_function=_EMBEDDER, metadata={"hnsw:space": "cosine"})


def _upsert(kind: str, records: list[dict]):
    collection = _collection(kind)
    docs, ids, metas = [], [], []
    for record in records:
        key = record.get("known_error_id") or record.get("incident_id")
        docs.append(_text(record, kind))
        ids.append(str(key))
        metas.append({"record_json": __import__("json").dumps(record, ensure_ascii=False)})
    if ids:
        collection.upsert(ids=ids, documents=docs, metadatas=metas)


def index_records() -> None:
    _upsert("kedb", list_kedb())
    _upsert("resolved", list_resolved_incidents())


def search(query: str, kind: str = "kedb", n_results: int = 3) -> list[dict]:
    index_records()
    collection = _collection(kind)
    if collection.count() == 0:
        return []
    result = collection.query(query_texts=[query], n_results=min(n_results, collection.count()), include=["metadatas", "distances", "documents"])
    rows = []
    for i, metadata in enumerate(result.get("metadatas", [[]])[0]):
        record = __import__("json").loads(metadata["record_json"])
        distance = float(result["distances"][0][i])
        record["similarity"] = round(max(0.0, min(1.0, 1.0 - distance)), 3)
        record["retrieved_text"] = result["documents"][0][i]
        rows.append(record)
    return rows
