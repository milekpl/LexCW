"""
Semantic Embedding Service using sentence-transformers and Qdrant.

Provides vector index management, semantic search, duplicate detection,
and relation discovery for dictionary entries and senses.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Supported embedding models
AVAILABLE_MODELS = [
    {
        "id": "jinaai/jina-embeddings-v3",
        "dimension": 1024,
        "label": "Jina v3 (Multilingual - Recommended)",
    },
    {
        "id": "intfloat/multilingual-e5-large",
        "dimension": 1024,
        "label": "Multilingual E5 Large",
    },
    {
        "id": "sentence-transformers/paraphrase-multilingual-mpnet-base-v2",
        "dimension": 768,
        "label": "MPNet Multilingual Base",
    },
    {
        "id": "sentence-transformers/all-MiniLM-L6-v2",
        "dimension": 384,
        "label": "MiniLM L6 (Lightweight - English)",
    },
    {
        "id": "BAAI/bge-m3",
        "dimension": 1024,
        "label": "BGE-M3 (Multilingual)",
    },
]

MODEL_DIMENSIONS = {m["id"]: m["dimension"] for m in AVAILABLE_MODELS}


class EmbeddingServiceError(Exception):
    """Base exception for EmbeddingService errors."""
    pass


class EmbeddingService:
    """Service for managing semantic embeddings and Qdrant vector database interactions."""

    _model_cache: Dict[str, Any] = {}
    _model_lock = threading.Lock()

    def __init__(
        self,
        qdrant_host: Optional[str] = None,
        qdrant_port: Optional[int] = None,
    ):
        from flask import current_app
        try:
            self.qdrant_host = qdrant_host or current_app.config.get("QDRANT_HOST", "localhost")
            self.qdrant_port = qdrant_port or current_app.config.get("QDRANT_PORT", 6333)
        except RuntimeError:
            self.qdrant_host = qdrant_host or os.environ.get("QDRANT_HOST", "localhost")
            self.qdrant_port = qdrant_port or int(os.environ.get("QDRANT_PORT", 6333))

        self._qdrant_client = None
        self._qdrant_lock = threading.Lock()

    def _get_qdrant_client(self):
        """Lazy initialization of Qdrant client."""
        if self._qdrant_client is None:
            with self._qdrant_lock:
                if self._qdrant_client is None:
                    try:
                        from qdrant_client import QdrantClient
                        self._qdrant_client = QdrantClient(
                            host=self.qdrant_host,
                            port=self.qdrant_port,
                            timeout=30.0,
                            check_compatibility=False,
                        )
                    except Exception as e:
                        logger.error("Failed to initialize Qdrant client: %s", e)
                        raise EmbeddingServiceError(f"Qdrant connection error: {e}")
        return self._qdrant_client

    def _get_model(self, model_name: str, device: str = "cpu"):
        """Get or load a sentence-transformer model instance."""
        cache_key = f"{model_name}:{device}"
        if cache_key not in self._model_cache:
            with self._model_lock:
                if cache_key not in self._model_cache:
                    try:
                        logger.info("Loading sentence-transformer model: %s (device=%s)", model_name, device)
                        import sys
                        import transformers
                        # Ensure all_tied_weights_keys setter/getter exists for custom HF architectures (Jina v3 XLMRobertaLoRA)
                        try:
                            if not hasattr(transformers.PreTrainedModel, "all_tied_weights_keys"):
                                transformers.PreTrainedModel.all_tied_weights_keys = property(
                                    lambda self: getattr(self, "_tied_weights_keys", []),
                                    lambda self, val: setattr(self, "_tied_weights_keys", val)
                                )
                        except Exception:
                            pass

                        if "/" in model_name:
                            try:
                                import glob
                                cache_pattern = f"/home/milek/.cache/huggingface/hub/models--{model_name.replace('/', '--')}/snapshots/*"
                                snapshots = glob.glob(cache_pattern)
                                if snapshots and snapshots[0] not in sys.path:
                                    sys.path.insert(0, snapshots[0])
                            except Exception as dl_err:
                                logger.debug("Cache lookup note for %s: %s", model_name, dl_err)

                        from sentence_transformers import SentenceTransformer
                        model = SentenceTransformer(model_name, device=device, trust_remote_code=True)
                        self._model_cache[cache_key] = model
                    except Exception as e:
                        logger.error("Failed to load model %s: %s", model_name, e)
                        raise EmbeddingServiceError(f"Failed to load model {model_name}: {e}")
        return self._model_cache[cache_key]

    def get_collection_name(self, project_id: Optional[int] = None) -> str:
        """Get Qdrant collection name for a given project ID."""
        pid = project_id if project_id is not None else 1
        return f"project_{pid}_senses"

    def ensure_collection(self, project_id: Optional[int], model_name: str, force_recreate: bool = False):
        """Ensure Qdrant collection exists with correct vector dimension."""
        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)
        dimension = MODEL_DIMENSIONS.get(model_name, 1024)

        from qdrant_client.http import models as rest_models

        try:
            exists = client.collection_exists(collection_name)
            if exists and force_recreate:
                logger.info("Recreating collection %s", collection_name)
                client.delete_collection(collection_name)
                exists = False

            if not exists:
                logger.info("Creating Qdrant collection %s with dimension %d", collection_name, dimension)
                client.create_collection(
                    collection_name=collection_name,
                    vectors_config=rest_models.VectorParams(
                        size=dimension,
                        distance=rest_models.Distance.COSINE,
                    ),
                )
        except Exception as e:
            logger.error("Error creating/checking Qdrant collection %s: %s", collection_name, e)
            raise EmbeddingServiceError(f"Qdrant collection error: {e}")

    def _compose_sense_text(self, headword: str, definition: str, glosses: List[str], pos: Optional[str] = None) -> str:
        """Compose text representation for a sense embedding."""
        parts = [headword]
        if pos:
            parts.append(f" ({pos})")
        if definition:
            parts.append(f": {definition}")
        clean_glosses = [g.strip() for g in glosses if g and g.strip()]
        if clean_glosses:
            parts.append(f" [{', '.join(clean_glosses)}]")
        return "".join(parts)

    def extract_senses_from_basex(self, dictionary_service, project_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """Extract all entry senses from BaseX database for embedding indexing."""
        connector = dictionary_service.db_connector
        db_name = dictionary_service._resolve_db_name(project_id)

        # XQuery to extract entry_id, headword, sense_id, pos, definition, glosses
        xquery = f"""
        for $e in collection('{db_name}')//entry
        let $eid := string($e/@id)
        let $hw := string(($e/lexical-unit/form/text)[1])
        let $pos := string(($e/grammatical-info/@value)[1])
        for $s in $e/sense
        let $sid := string($s/@id)
        let $def := string-join($s/definition/form/text/string(), ' ')
        let $glosses := string-join($s/gloss/text/string(), '|||')
        return concat($eid, '###', $hw, '###', $sid, '###', $pos, '###', $def, '###', $glosses)
        """

        try:
            result = connector.execute_query(xquery)
            items = result.strip().split("\n") if result and result.strip() else []
            senses_data = []

            for item in items:
                if not item.strip():
                    continue
                parts = item.split("###")
                if len(parts) >= 3:
                    entry_id = parts[0].strip()
                    headword = parts[1].strip()
                    sense_id = parts[2].strip()
                    pos = parts[3].strip() if len(parts) > 3 else ""
                    definition = parts[4].strip() if len(parts) > 4 else ""
                    raw_glosses = parts[5].strip() if len(parts) > 5 else ""
                    glosses = raw_glosses.split("|||") if raw_glosses else []

                    senses_data.append({
                        "entry_id": entry_id,
                        "headword": headword,
                        "sense_id": sense_id,
                        "pos": pos,
                        "definition": definition,
                        "glosses": glosses,
                        "text": self._compose_sense_text(headword, definition, glosses, pos),
                    })
            return senses_data
        except Exception as e:
            logger.error("Failed to extract senses from BaseX: %s", e)
            raise EmbeddingServiceError(f"BaseX extraction error: {e}")

    def rebuild_index(
        self,
        project_id: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        dictionary_service=None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Rebuild the semantic embedding index for a project."""
        return self.build_index(
            dictionary_service=dictionary_service,
            project_id=project_id,
            progress_callback=progress_callback,
            cancel_check=cancel_check,
        )

    @staticmethod
    def _resolve_device(device_setting: Optional[str] = None) -> str:
        try:
            import torch
            if torch.cuda.is_available():
                logger.info("CUDA is available! Selected device: cuda")
                return "cuda"
        except Exception as e:
            logger.debug("CUDA check failed: %s", e)
        logger.info("Using device: %s", device_setting or "cpu")
        return device_setting or "cpu"

    def build_index(
        self,
        dictionary_service=None,
        project_id: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Dict[str, Any]:
        """Build or rebuild Qdrant vector index for all senses in BaseX database."""
        from app.models.project_settings import ProjectSettings, db

        if dictionary_service is None:
            from app.services.dictionary_service import DictionaryService
            try:
                injector = getattr(current_app, "injector", None)
                if injector is not None:
                    dictionary_service = injector.get(DictionaryService)
            except Exception:
                pass

        if dictionary_service is None:
            from app.services.dictionary_service import DictionaryService
            from app.database.basex_connector import BaseXConnector
            connector = None
            try:
                injector = getattr(current_app, "injector", None)
                if injector is not None:
                    connector = injector.get(BaseXConnector)
            except Exception:
                pass
            if connector is None:
                host = "localhost"
                port = 1984
                username = "admin"
                password = "admin"
                database = "dictionary"
                try:
                    if current_app:
                        cfg = current_app.config
                        host = cfg.get("BASEX_HOST", host)
                        port = cfg.get("BASEX_PORT", port)
                        username = cfg.get("BASEX_USERNAME", username)
                        password = cfg.get("BASEX_PASSWORD", password)
                        database = os.environ.get("TEST_DB_NAME") or os.environ.get("BASEX_DATABASE") or cfg.get("BASEX_DATABASE", database)
                except Exception:
                    pass
                connector = BaseXConnector(host=host, port=port, username=username, password=password, database=database)
            dictionary_service = DictionaryService(db_connector=connector)

        # Get settings
        pid = project_id or 1
        settings = ProjectSettings.query.filter_by(id=pid).first()
        model_name = settings.embedding_model if settings and settings.embedding_model else "jinaai/jina-embeddings-v3"
        device = self._resolve_device(settings.embedding_device if settings else None)
        logger.info("Building vector index with model=%s on device=%s", model_name, device)

        if progress_callback:
            progress_callback(0, 0, f"Loading embedding model {model_name} on {device}...")

        model = self._get_model(model_name, device=device)
        self.ensure_collection(project_id, model_name, force_recreate=True)
        collection_name = self.get_collection_name(project_id)

        if progress_callback:
            progress_callback(0, 0, "Extracting senses from database...")

        senses_data = self.extract_senses_from_basex(dictionary_service, project_id)
        total_senses = len(senses_data)

        if total_senses == 0:
            logger.warning("No senses found for indexing in project %s", project_id)
            return {"indexed": 0, "total": 0, "model": model_name}

        if progress_callback:
            progress_callback(0, total_senses, f"Encoding {total_senses} senses...")

        client = self._get_qdrant_client()
        from qdrant_client.http import models as rest_models
        import uuid

        import os
        import torch

        batch_size = 64  # Safer batch size for GPU transformer memory stability
        processed = 0

        # Enable multi-threading for PyTorch CPU if needed
        try:
            if device == "cpu" and hasattr(torch, "set_num_threads"):
                cores = os.cpu_count() or 4
                torch.set_num_threads(cores)
        except Exception:
            pass

        for i in range(0, total_senses, batch_size):
            if cancel_check and cancel_check():
                logger.info("Indexing operation cancelled at %d/%d senses for project %s", processed, total_senses, project_id)
                if device == "cuda" and hasattr(torch, "cuda"):
                    torch.cuda.empty_cache()
                return {
                    "indexed": processed,
                    "total": total_senses,
                    "model": model_name,
                    "collection": collection_name,
                    "cancelled": True,
                }

            batch = senses_data[i : i + batch_size]
            texts = [item["text"] for item in batch]

            encode_kwargs = {
                "batch_size": len(texts),
                "normalize_embeddings": True,
                "show_progress_bar": False,
            }
            if "jina" in model_name.lower():
                encode_kwargs["task"] = "text-matching"

            try:
                # Solution 2: Wrap model.encode in torch.no_grad() to avoid autograd memory build-up
                with torch.no_grad():
                    embeddings = model.encode(texts, **encode_kwargs)
            except TypeError:
                # Fallback if model.encode does not accept task parameter
                encode_kwargs.pop("task", None)
                with torch.no_grad():
                    embeddings = model.encode(texts, **encode_kwargs)

            points = []
            for item, emb in zip(batch, embeddings):
                # Generate deterministic UUID from sense_id or entry_id + sense_id
                point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{item['entry_id']}:{item['sense_id']}"))
                points.append(
                    rest_models.PointStruct(
                        id=point_id,
                        vector=emb.tolist(),
                        payload={
                            "entry_id": item["entry_id"],
                            "headword": item["headword"],
                            "sense_id": item["sense_id"],
                            "pos": item["pos"],
                            "definition": item["definition"][:200],
                            "composed_text": item["text"],
                        },
                    )
                )

            client.upsert(collection_name=collection_name, points=points)
            processed += len(batch)

            if progress_callback:
                progress_callback(processed, total_senses, f"Indexed {processed}/{total_senses} senses...")

        # Update ProjectSettings
        if settings:
            settings.embedding_last_built = datetime.now(timezone.utc)
            settings.embedding_sense_count = processed
            try:
                db.session.commit()
            except Exception as e:
                logger.warning("Could not update project_settings timestamp: %s", e)

        if device == "cuda" and hasattr(torch, "cuda"):
            try:
                torch.cuda.empty_cache()
            except Exception:
                pass

        logger.info("Successfully rebuilt embedding index for project %s: %d senses", project_id, processed)
        return {
            "indexed": processed,
            "total": total_senses,
            "model": model_name,
            "collection": collection_name,
        }

    def semantic_search(
        self,
        query: str,
        project_id: Optional[int] = None,
        top_k: int = 20,
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Perform semantic similarity search for a text query."""
        model_name = "jinaai/jina-embeddings-v3"
        device = self._resolve_device()
        try:
            from app.models.project_settings import ProjectSettings
            pid = project_id or 1
            settings = ProjectSettings.query.filter_by(id=pid).first()
            if settings:
                if settings.embedding_model:
                    model_name = settings.embedding_model
                device = self._resolve_device(settings.embedding_device)
        except Exception as e:
            logger.debug("Could not query ProjectSettings, using defaults: %s", e)

        model = self._get_model(model_name, device=device)
        collection_name = self.get_collection_name(project_id)
        client = self._get_qdrant_client()

        encoded = model.encode([query], normalize_embeddings=True)[0]
        if hasattr(encoded, "tolist"):
            query_vector = encoded.tolist()
        else:
            query_vector = list(encoded)

        search_results = client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=top_k * 2,
            score_threshold=threshold,
        )

        # Aggregate results by entry_id to avoid duplicate entries
        seen_entries = set()
        results = []

        for hit in search_results:
            payload = hit.payload or {}
            entry_id = payload.get("entry_id")
            if not entry_id or entry_id in seen_entries:
                continue
            seen_entries.add(entry_id)

            results.append({
                "entry_id": entry_id,
                "headword": payload.get("headword", ""),
                "sense_id": payload.get("sense_id", ""),
                "pos": payload.get("pos", ""),
                "definition": payload.get("definition", ""),
                "score": round(float(hit.score), 4),
            })

            if len(results) >= top_k:
                break

        return results

    def find_semantic_duplicates(
        self,
        project_id: Optional[int] = None,
        threshold: float = 0.85,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Find candidate duplicate entry pairs based on high sense vector similarity."""
        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)

        if not client.collection_exists(collection_name):
            return []

        # Scroll sample points
        scroll_resp, _ = client.scroll(
            collection_name=collection_name,
            limit=500,
            with_vectors=True,
            with_payload=True,
        )

        duplicate_groups = []
        seen_pairs = set()

        for point in scroll_resp:
            if not point.vector:
                continue
            pt_payload = point.payload or {}
            entry_id = pt_payload.get("entry_id")
            headword = pt_payload.get("headword")
            if not entry_id:
                continue

            similar = client.search(
                collection_name=collection_name,
                query_vector=point.vector,
                limit=5,
                score_threshold=threshold,
            )

            for hit in similar:
                hit_payload = hit.payload or {}
                other_id = hit_payload.get("entry_id")
                other_hw = hit_payload.get("headword")
                if not other_id or other_id == entry_id:
                    continue

                pair_key = tuple(sorted([str(entry_id), str(other_id)]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                duplicate_groups.append({
                    "id": f"sem_dup_{entry_id}_{other_id}",
                    "confidence": round(float(hit.score), 4),
                    "mode": "semantic",
                    "entries": [
                        {
                            "entry_id": entry_id,
                            "headword": headword,
                            "pos": pt_payload.get("pos"),
                            "match_fields": ["sense_embedding"],
                        },
                        {
                            "entry_id": other_id,
                            "headword": other_hw,
                            "pos": hit_payload.get("pos"),
                            "match_fields": ["sense_embedding"],
                        },
                    ],
                    "merge_suggestion": "manual",
                })

                if len(duplicate_groups) >= limit:
                    break
            if len(duplicate_groups) >= limit:
                break

        return duplicate_groups

    def find_related(
        self,
        entry_id: str,
        project_id: Optional[int] = None,
        top_k: int = 10,
        threshold: float = 0.5,
    ) -> List[Dict[str, Any]]:
        """Find semantically related entries for a given entry ID."""
        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)

        from qdrant_client.http import models as rest_models

        # Find points for this entry
        points, _ = client.scroll(
            collection_name=collection_name,
            scroll_filter=rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="entry_id",
                        match=rest_models.MatchValue(value=entry_id),
                    )
                ]
            ),
            with_vectors=True,
            with_payload=True,
            limit=10,
        )

        if not points:
            return []

        related = []
        seen_entries = {entry_id}

        for point in points:
            if not point.vector:
                continue

            search_results = client.search(
                collection_name=collection_name,
                query_vector=point.vector,
                limit=top_k * 2,
                score_threshold=threshold,
            )

            for hit in search_results:
                other_id = hit.payload.get("entry_id")
                if other_id in seen_entries:
                    continue
                seen_entries.add(other_id)

                related.append({
                    "entry_id": other_id,
                    "headword": hit.payload.get("headword"),
                    "pos": hit.payload.get("pos"),
                    "definition": hit.payload.get("definition"),
                    "score": round(float(hit.score), 4),
                })

                if len(related) >= top_k:
                    break
            if len(related) >= top_k:
                break

        return related

    def delete_index(self, project_id: Optional[int] = None) -> bool:
        """Delete Qdrant vector index for a project."""
        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)
        if client.collection_exists(collection_name):
            client.delete_collection(collection_name)
            return True
        return False

    def get_index_status(self, project_id: Optional[int] = None) -> Dict[str, Any]:
        """Get current index status and metrics."""
        settings = None
        try:
            from app.models.project_settings import ProjectSettings
            pid = project_id or 1
            settings = ProjectSettings.query.filter_by(id=pid).first()
        except Exception as e:
            logger.debug("Could not query ProjectSettings in get_index_status: %s", e)

        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)

        exists = client.collection_exists(collection_name)
        vectors_count = 0
        if exists:
            info = client.get_collection(collection_name)
            vectors_count = info.points_count or 0

        return {
            "collection_exists": exists,
            "vectors_count": vectors_count,
            "model_name": settings.embedding_model if settings else "jinaai/jina-embeddings-v3",
            "device": settings.embedding_device if settings else "cpu",
            "last_built": settings.embedding_last_built.isoformat() if settings and settings.embedding_last_built else None,
        }


# Global instance & EventBus registration
_embedding_service_instance: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """Get singleton instance of EmbeddingService."""
    global _embedding_service_instance
    if _embedding_service_instance is None:
        _embedding_service_instance = EmbeddingService()
    return _embedding_service_instance


def _on_import_complete_handler(data: Dict[str, Any]):
    """Background handler when a LIFT import completes."""
    project_id = data.get("project_id", 1)
    logger.info("Auto-rebuilding embedding index following LIFT import for project %s", project_id)

    def _async_rebuild():
        from flask import current_app
        try:
            service = get_embedding_service()
            service.rebuild_index(project_id=project_id)
        except Exception as e:
            logger.error("Auto embedding rebuild failed for project %s: %s", project_id, e)

    t = threading.Thread(target=_async_rebuild, daemon=True)
    t.start()


# Register with EventBus
try:
    from app.services.event_bus import event_bus
    event_bus.on("import_complete", _on_import_complete_handler)
except Exception:
    pass
