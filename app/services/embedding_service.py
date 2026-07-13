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
from itertools import chain
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
                        try:
                            model = SentenceTransformer(model_name, device=device, trust_remote_code=True, local_files_only=True)
                        except Exception:
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

    def _qdrant_search(
        self,
        client,
        collection_name: str,
        query_vector: list,
        limit: int = 20,
        score_threshold: Optional[float] = None,
    ) -> list:
        """Execute vector search across QdrantClient versions (query_points vs search)."""
        try:
            if hasattr(client, "query_points"):
                kwargs = {
                    "collection_name": collection_name,
                    "query": query_vector,
                    "limit": limit,
                }
                if score_threshold is not None and score_threshold > 0:
                    kwargs["score_threshold"] = score_threshold
                res = client.query_points(**kwargs)
                if hasattr(res, "points") and isinstance(res.points, list):
                    return res.points
                if isinstance(res, list):
                    return res

            if hasattr(client, "search"):
                kwargs = {
                    "collection_name": collection_name,
                    "query_vector": query_vector,
                    "limit": limit,
                }
                if score_threshold is not None and score_threshold > 0:
                    kwargs["score_threshold"] = score_threshold
                res = client.search(**kwargs)
                if isinstance(res, list):
                    return res
                if hasattr(res, "points") and isinstance(res.points, list):
                    return res.points

            return []
        except Exception as e:
            logger.warning("Qdrant vector query failed: %s", e)
            return []

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

        search_results = self._qdrant_search(
            client=client,
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

            similar = self._qdrant_search(
                client=client,
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

            search_results = self._qdrant_search(
                client=client,
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

    def find_batch_relations(
        self,
        project_id: Optional[int] = None,
        pos: Optional[str] = None,
        threshold: float = 0.5,
        top_k: int = 20,
        sample_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Batch discovery of semantically related entry pairs across the entire index.

        Strategy:
          1. Scroll ALL Qdrant points (with vectors) for the project,
             optionally filtered by POS.
          2. Group points by entry_id; compute mean vector per entry.
          3. For each entry's mean vector, search Qdrant for top K neighbors.
          4. Collect candidate pairs, deduplicate, sort by score.

        Returns list of candidate dicts:
            [{
                'entry_id_a': str, 'entry_id_b': str,
                'score': float,
                'a_headword': str, 'b_headword': str,
                'a_pos': str, 'b_pos': str,
                'a_sense_count': int, 'b_sense_count': int,
                'a_sense_ids': list, 'b_sense_ids': list,
                'a_definition': str, 'b_definition': str,
            }, ...]
        """
        # Check cache via Redis-backed CacheService
        cache_key = f"discovery:batch_rels:p{project_id}:t{threshold}:s{sample_size}:pos{pos}"
        try:
            from app.services.cache_service import cache_service
            cached = cache_service.get(cache_key)
            if cached is not None:
                logger.info("Returning cached batch discovery results (%d candidates)", len(cached))
                return cached
        except Exception:
            pass

        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)

        from qdrant_client.http import models as rest_models

        if progress_callback:
            progress_callback(0, 0, "Checking Qdrant collection...")

        if not client.collection_exists(collection_name):
            raise EmbeddingServiceError(
                "Qdrant index not built. Build it in Settings > Embedding Index first."
            )

        # --- Phase 1: Scroll metadata only (no vectors) to build entry list ---
        scroll_filter = None
        if pos:
            scroll_filter = rest_models.Filter(
                must=[
                    rest_models.FieldCondition(
                        key="pos",
                        match=rest_models.MatchValue(value=pos),
                    )
                ]
            )

        if progress_callback:
            progress_callback(0, 0, "Scanning entry metadata...")

        # Normalize raw POS from Qdrant payload to short codes
        def _norm_pos(raw: str) -> str:
            raw = raw.strip()
            if raw in ("Verb",):
                return "v"
            if raw in ("Noun",):
                return "n"
            if raw in ("Adjective", "Adj"):
                return "adj"
            if raw in ("Adverb", "Adv"):
                return "adv"
            return raw

        entry_groups: Dict[str, Dict[str, Any]] = {}
        next_offset = None
        while True:
            if cancel_check and cancel_check():
                raise EmbeddingServiceError("Operation cancelled by user")
            batch, next_offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=scroll_filter,
                limit=5000,
                with_vectors=False,
                with_payload=True,
                offset=next_offset,
            )
            if not batch:
                break
            for point in batch:
                payload = point.payload or {}
                eid = payload.get("entry_id")
                if not eid:
                    continue
                if eid not in entry_groups:
                    entry_groups[eid] = {
                        "entry_id": eid,
                        "headword": payload.get("headword", ""),
                        "pos": _norm_pos(payload.get("pos", "")),
                        "definition": payload.get("definition", ""),
                    }
                else:
                    # Collect all POS values for multi-POS entries (e.g. "cut" is both n and v)
                    existing = entry_groups[eid]
                    this_pos = _norm_pos(payload.get("pos", ""))
                    if this_pos and this_pos not in existing.get("_all_pos", set()):
                        if "_all_pos" not in existing:
                            existing["_all_pos"] = {existing["pos"]} if existing["pos"] else set()
                        existing["_all_pos"].add(this_pos)
            if next_offset is None or next_offset == "":
                break

        if not entry_groups:
            return []

        entries = list(entry_groups.values())
        total_entries = len(entries)

        if progress_callback:
            progress_callback(total_entries, 0, f"Found {total_entries} entries")

        # Enforce a reasonable max — no sample_size means full scan, which is O(n²)
        if sample_size and sample_size < total_entries:
            entries = entries[:sample_size]
            total_entries = len(entries)

        if progress_callback:
            progress_callback(total_entries, 0, f"Encoding {total_entries} entries...")

        # --- POS tag entries missing POS in Qdrant payload ---
        pending_pos = [e for e in entries if not (e.get("pos") or "").strip()]
        if pending_pos:
            try:
                from app.services.pos_tagger_service import get_pos_tagger_service
                tagger = get_pos_tagger_service()
                pos_map = {"noun": "n", "verb": "v", "adjective": "adj", "adverb": "adv", "preposition": "prep", "pronoun": "pron", "conjunction": "conj", "determiner": "det", "numeral": "num", "interjection": "interj", "particle": "part"}
                for entry in pending_pos:
                    hw = (entry.get("headword") or "").strip()
                    if not hw:
                        continue
                    try:
                        tokens = tagger.tag_text(hw)
                        if tokens:
                            tag = tokens[0].get("normalized_pos", "").lower()
                            entry["pos"] = pos_map.get(tag, tag[:3])
                    except Exception:
                        pass
            except Exception:
                logger.warning("PosTaggerService unavailable for POS fallback")

        # --- Phase 2: Encode at query time ---
        texts = []
        for entry in entries:
            hw = entry.get("headword", "") or ""
            pos_val = entry.get("pos", "") or ""
            defn = entry.get("definition", "") or ""
            text = hw
            if pos_val:
                text += f" ({pos_val})"
            if defn:
                text += f": {defn}"
            texts.append(text)

        model_name = "jinaai/jina-embeddings-v3"
        device = self._resolve_device()
        model = self._get_model(model_name, device=device)

        import numpy as np
        import torch

        query_vectors = []
        batch_size = 64
        for i in range(0, len(texts), batch_size):
            if cancel_check and cancel_check():
                raise EmbeddingServiceError("Operation cancelled by user")
            batch_texts = texts[i:i + batch_size]
            encode_kwargs = {
                "batch_size": len(batch_texts),
                "normalize_embeddings": True,
                "show_progress_bar": False,
                "task": "text-matching",
            }
            with torch.no_grad():
                encoded = model.encode(batch_texts, **encode_kwargs)
            query_vectors.extend(encoded.cpu().numpy() if hasattr(encoded, 'cpu') else encoded)
            if progress_callback:
                progress_callback(total_entries, min(i + batch_size, total_entries),
                                  f"Encoding: {min(i + batch_size, total_entries)}/{total_entries}")

        n = len(query_vectors)
        if n < 2:
            return []

        if progress_callback:
            progress_callback(n, 0, f"Searching Qdrant for {n} entries...")

        # --- Phase 3: query_batch_points — let Qdrant's HNSW find neighbors ---
        requests = []
        for qv in query_vectors:
            requests.append(
                rest_models.QueryRequest(
                    query=qv.tolist(),
                    limit=top_k,
                    score_threshold=threshold,
                    with_payload=True,
                )
            )

        # Split into sub-batches of 100 to avoid oversized gRPC messages
        batch_results = []
        sub_batch_size = 100
        for batch_start in range(0, len(requests), sub_batch_size):
            if cancel_check and cancel_check():
                raise EmbeddingServiceError("Operation cancelled by user")
            sub_requests = requests[batch_start:batch_start + sub_batch_size]
            sub_resp = client.query_batch_points(
                collection_name=collection_name,
                requests=sub_requests,
            )
            # Unpack per-query results
            for qr in sub_resp:
                batch_results.append(getattr(qr, 'points', []) or [])
            if progress_callback:
                p = min(batch_start + sub_batch_size, n)
                progress_callback(n, p, f"Qdrant search: {p}/{n}")

        # Build lookup: entry_id -> set of POS values this entry has
        entry_pos_set: Dict[str, set] = {}
        for e in entries:
            all_pos = e.get("_all_pos")
            if all_pos:
                entry_pos_set[e["entry_id"]] = all_pos
            else:
                p = e.get("pos", "")
                entry_pos_set[e["entry_id"]] = {p} if p else set()

        # Normalize raw POS from Qdrant payload to short codes for cross-POS matching
        def _norm_pos(raw: str) -> str:
            raw = raw.strip().title()
            if raw in ("Verb",):
                return "v"
            if raw in ("Noun",):
                return "n"
            if raw in ("Adjective", "Adj"):
                return "adj"
            if raw in ("Adverb", "Adv"):
                return "adv"
            if raw in ("Preposition",):
                return "prep"
            if raw in ("Pronoun",):
                return "pron"
            return raw.lower()

        # --- Phase 4: Aggregate results ---
        if progress_callback:
            progress_callback(n, n, "Aggregating results...")

        candidates = []
        seen_pairs: set[tuple[str, str]] = set()

        for i, hits in enumerate(batch_results):
            eid_a = entries[i]["entry_id"]
            hw_a = entries[i]["headword"]

            for hit in hits:
                payload = hit.payload or {}
                eid_b = payload.get("entry_id")
                if not eid_b or eid_b == eid_a:
                    continue
                if eid_b not in sampled_ids:
                    continue
                # Filter by POS — synonyms overwhelmingly share the same POS.
                # Use set intersection: entries with multiple POS (e.g. "cut": n+v)
                # match if any POS overlaps.
                pos_set_a = entry_pos_set.get(eid_a, set())
                pos_set_b = entry_pos_set.get(eid_b, set())
                if pos_set_a and pos_set_b and not (pos_set_a & pos_set_b):
                    continue

                pair_key = tuple(sorted([eid_a, eid_b]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                score = round(float(hit.score), 4)
                # Join multiple POS for display (e.g. "n, v" for cut)
                pos_display_a = ", ".join(sorted(pos_set_a)) if pos_set_a else entries[i].get("pos", "")
                pos_display_b = ", ".join(sorted(pos_set_b)) if pos_set_b else _norm_pos(payload.get("pos", ""))
                candidates.append({
                    "entry_id_a": eid_a,
                    "entry_id_b": eid_b,
                    "score": score,
                    "a_headword": hw_a,
                    "b_headword": payload.get("headword", ""),
                    "a_pos": pos_display_a,
                    "b_pos": pos_display_b,
                    "a_sense_count": -1,
                    "b_sense_count": -1,
                    "a_sense_ids": [],
                    "b_sense_ids": [],
                    "a_definition": entries[i].get("definition", ""),
                    "b_definition": payload.get("definition", ""),
                })

        if progress_callback:
            progress_callback(n, n, f"Done — {len(candidates)} candidates found")

        candidates.sort(key=lambda c: -c["score"])

        # Store in Redis-backed cache — the embedding index only changes on manual rebuild
        try:
            from app.services.cache_service import cache_service
            cache_service.set(cache_key, candidates, ttl=2592000)  # 30 days
        except Exception:
            pass

        return candidates

    def find_batch_subentry_relations(
        self,
        project_id: Optional[int] = None,
        threshold: float = 0.3,
        top_k: int = 30,
        sample_size: Optional[int] = None,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Batch discovery of subentry relations using embeddings.

        Scans all points, classifies phrase vs main entries (by headword),
        then for each main entry finds semantically similar phrase entries
        whose headword contains the main entry's headword.

        Returns same format as find_batch_relations().
        """
        # Check cache
        cache_key = f"discovery:batch_subs:p{project_id}:t{threshold}:s{sample_size}"
        try:
            from app.services.cache_service import cache_service
            cached = cache_service.get(cache_key)
            if cached is not None:
                logger.info("Returning cached subentry discovery results (%d candidates)", len(cached))
                return cached
        except Exception:
            pass

        client = self._get_qdrant_client()
        collection_name = self.get_collection_name(project_id)

        if not client.collection_exists(collection_name):
            raise EmbeddingServiceError(
                "Qdrant index not built. Build it in Settings > Embedding Index first."
            )

        if progress_callback:
            progress_callback(0, 0, "Phase 1: scanning entry metadata...")

        # --- Phase 1: Scroll metadata only ---
        entry_groups: Dict[str, Dict[str, Any]] = {}
        next_offset = None
        while True:
            if cancel_check and cancel_check():
                raise EmbeddingServiceError("Operation cancelled by user")
            batch, next_offset = client.scroll(
                collection_name=collection_name,
                limit=5000,
                with_vectors=False,
                with_payload=True,
                offset=next_offset,
            )
            if not batch:
                break
            for point in batch:
                payload = point.payload or {}
                eid = payload.get("entry_id")
                if not eid:
                    continue
                if eid not in entry_groups:
                    hw = payload.get("headword", "")
                    is_phrase = " " in hw
                    entry_groups[eid] = {
                        "entry_id": eid,
                        "headword": hw,
                        "pos": payload.get("pos", ""),
                        "definition": payload.get("definition", ""),
                        "is_phrase": is_phrase,
                        "sense_ids": [],
                    }
                sid = payload.get("sense_id")
                if sid and sid not in entry_groups[eid]["sense_ids"]:
                    entry_groups[eid]["sense_ids"].append(sid)
            if next_offset is None or next_offset == "":
                break

        if not entry_groups:
            return []

        all_entries = list(entry_groups.values())
        main_entries = [e for e in all_entries if not e["is_phrase"]]
        phrase_entries = [e for e in all_entries if e["is_phrase"]]
        phrase_by_id = {e["entry_id"]: e for e in phrase_entries}

        if progress_callback:
            progress_callback(len(main_entries), 0,
                              f"Found {len(main_entries)} main, {len(phrase_entries)} phrase entries")

        if sample_size and sample_size < len(main_entries):
            main_entries = main_entries[:sample_size]

        total_main = len(main_entries)

        # Build word -> phrase lookup for headword containment
        import re
        word_to_phrases: Dict[str, list] = {}
        for p in phrase_entries:
            words = set(re.split(r"[\s\-]+", p["headword"].lower()))
            for w in words:
                w_clean = w.strip("'\".,;:!?()[]")
                if w_clean:
                    word_to_phrases.setdefault(w_clean, []).append(p)

        word_to_phrases = {k: list({pe["entry_id"]: pe for pe in v}.values())
                           for k, v in word_to_phrases.items()}

        # --- Phase 2: Fetch vectors only for entries that pass pre-filter ---
        if progress_callback:
            progress_callback(total_main, 0, "Phase 2: fetching vectors...")

        target_sense_ids = set()
        for entry in main_entries:
            target_sense_ids.update(entry["sense_ids"])
        for entry in phrase_entries:
            target_sense_ids.update(entry["sense_ids"])

        all_points = []
        next_offset = None
        from qdrant_client.http import models as rest_models
        sense_filter = rest_models.Filter(
            must=[
                rest_models.FieldCondition(
                    key="sense_id",
                    match=rest_models.MatchAny(any=list(target_sense_ids)),
                )
            ]
        )
        while True:
            if cancel_check and cancel_check():
                raise EmbeddingServiceError("Operation cancelled by user")
            batch, next_offset = client.scroll(
                collection_name=collection_name,
                scroll_filter=sense_filter,
                limit=5000,
                with_vectors=True,
                with_payload=True,
                offset=next_offset,
            )
            if not batch:
                break
            all_points.extend(batch)
            if progress_callback:
                progress_callback(total_main, len(all_points),
                                  f"Fetching vectors: {len(all_points)}/{len(target_sense_ids)}")
            if next_offset is None or next_offset == "":
                break

        # --- Group vectors by entry_id ---
        entry_vectors: Dict[str, list] = {}
        for entry in chain(main_entries, phrase_entries):
            entry_vectors[entry["entry_id"]] = []
        for point in all_points:
            eid = (point.payload or {}).get("entry_id")
            if eid in entry_vectors:
                entry_vectors[eid].append(point.vector)

        # --- Compute mean vectors ---
        import numpy as np
        main_data = []
        phrase_data_by_id = {}

        for entry in main_entries:
            vecs = entry_vectors.get(entry["entry_id"], [])
            n = len(vecs)
            if n == 0:
                continue
            try:
                mean_vec = np.mean(vecs, axis=0)
            except Exception:
                continue
            entry["mean_vector"] = mean_vec
            main_data.append(entry)

        for entry in phrase_entries:
            vecs = entry_vectors.get(entry["entry_id"], [])
            n = len(vecs)
            if n == 0:
                continue
            try:
                mean_vec = np.mean(vecs, axis=0)
            except Exception:
                continue
            entry["mean_vector"] = mean_vec
            phrase_data_by_id[entry["entry_id"]] = entry

        if not main_data or not phrase_data_by_id:
            return []

        total_main = len(main_data)

        # --- Build phrase matrix and phrase index ---
        phrase_ids = list(phrase_data_by_id.keys())
        phrase_matrix = np.stack([phrase_data_by_id[pid]["mean_vector"] for pid in phrase_ids])  # (n_phrase, dim)

        candidates = []
        seen_pairs: set[tuple[str, str]] = set()
        pattern_cache: Dict[str, re.Pattern] = {}

        if progress_callback:
            progress_callback(total_main, 0, f"Comparing {total_main} main entries with {len(phrase_ids)} phrases")

        import re

        for idx, main in enumerate(main_data):
            if cancel_check and cancel_check():
                raise EmbeddingServiceError("Operation cancelled by user")

            main_hw = main["headword"].strip()
            main_hw_lc = main_hw.lower()
            if len(main_hw_lc) < 2:
                continue

            # Headword containment pre-filter
            cand_phrase_entries = word_to_phrases.get(main_hw_lc, [])
            if not cand_phrase_entries:
                continue

            # Build index positions of candidate phrases in phrase_matrix
            cand_indices = []
            pattern = pattern_cache.get(main_hw_lc)
            if not pattern:
                pattern = re.compile(rf"\b{re.escape(main_hw_lc)}\b", re.IGNORECASE)
                pattern_cache[main_hw_lc] = pattern

            for p_entry in cand_phrase_entries:
                if p_entry["entry_id"] == main["entry_id"]:
                    continue
                try:
                    pidx = phrase_ids.index(p_entry["entry_id"])
                except ValueError:
                    continue
                if pattern.search(p_entry["headword"].lower()):
                    cand_indices.append(pidx)

            if not cand_indices:
                continue

            # Compute cosine similarity against all candidate phrases in one matrix op
            main_vec = main["mean_vector"]  # (dim,)
            # Dot product with selected phrase rows -> (n_cand,)
            sims = phrase_matrix[cand_indices] @ main_vec

            for pi, score in zip(cand_indices, sims):
                score_f = float(score)
                if score_f < threshold:
                    continue

                pid = phrase_ids[pi]
                pair_key = (main["entry_id"], pid)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                p_entry = phrase_data_by_id[pid]
                candidates.append({
                    "entry_id_a": main["entry_id"],
                    "entry_id_b": pid,
                    "score": round(score_f, 4),
                    "a_headword": main["headword"],
                    "b_headword": p_entry["headword"],
                    "a_pos": main["pos"],
                    "b_pos": p_entry["pos"],
                    "a_sense_count": len(main["sense_ids"]),
                    "b_sense_count": len(p_entry["sense_ids"]),
                    "a_sense_ids": main["sense_ids"],
                    "b_sense_ids": p_entry["sense_ids"],
                    "a_definition": main["definition"],
                    "b_definition": p_entry["definition"],
                })

            if progress_callback and (idx + 1) % 100 == 0:
                progress_callback(total_main, idx + 1,
                                  f"Scanned {idx+1}/{total_main} ({len(candidates)} candidates)")

        if progress_callback:
            progress_callback(total_main, total_main,
                              f"Done — {len(candidates)} subentry candidates found")

        candidates.sort(key=lambda c: -c["score"])

        # Store in Redis-backed cache (30 days — index only changes on rebuild)
        try:
            from app.services.cache_service import cache_service
            cache_service.set(cache_key, candidates, ttl=2592000)
        except Exception:
            pass

        return candidates

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
