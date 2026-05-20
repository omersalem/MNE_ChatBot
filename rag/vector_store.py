import json
import logging
import os
import numpy as np
import faiss
from pathlib import Path
from config import Config
from rag.embeddings import EmbeddingEngine

logger = logging.getLogger(__name__)


class VectorStore:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.index = None
        self.metadata = []
        self.metadata_file = Config.VECTOR_DB_DIR / 'metadata.json'
        self.index_file = Config.VECTOR_DB_DIR / 'faiss.index'
        self.manifest_file = Config.VECTOR_DB_DIR / 'manifest.json'
        self.embedding_engine = EmbeddingEngine()
        self.requires_reindex = False
        self._load()
        self._initialized = True

    def _load(self):
        Config.VECTOR_DB_DIR.mkdir(exist_ok=True)
        manifest = self._load_manifest()
        if self.index_file.exists() and self.metadata_file.exists():
            if manifest is None:
                self.index = faiss.IndexFlatIP(self.embedding_engine.dimension)
                self.metadata = []
                self.requires_reindex = True
                self._save()
                logger.warning("Vector store reset because no manifest was found for the existing index")
                return

            if not self._manifest_matches(manifest):
                self.index = faiss.IndexFlatIP(self.embedding_engine.dimension)
                self.metadata = []
                self.requires_reindex = True
                self._save()
                logger.warning("Vector store reset because embedding configuration changed")
                return

            self.index = faiss.read_index(str(self.index_file))
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                self.metadata = json.load(f)
            logger.info(f"Loaded vector store: {len(self.metadata)} chunks")
        else:
            self.index = faiss.IndexFlatIP(self.embedding_engine.dimension)
            self.metadata = []
            self._save()
            logger.info("Created new vector store")

    def add_chunks(self, chunks):
        for chunk in chunks:
            chunk['embedding_model'] = Config.EMBEDDING_MODEL
        texts = [c['text'] for c in chunks]
        embeddings = self.embedding_engine.embed(texts)
        
        faiss.normalize_L2(embeddings)
        self.index.add(embeddings)
        self.metadata.extend(chunks)
        self._save()
        logger.info(f"Added {len(chunks)} chunks. Total: {len(self.metadata)}")

    def search(self, query, top_k=5, allowed_sources=None):
        if self.index.ntotal == 0:
            return []
        
        query_embedding = self.embedding_engine.embed_query(query)
        query_embedding = np.array([query_embedding]).astype(np.float32)
        faiss.normalize_L2(query_embedding)
        allowed = set(allowed_sources or [])
        candidate_count = min(max(top_k * 6, top_k), self.index.ntotal)
        scores, indices = self.index.search(query_embedding, candidate_count)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx == -1:
                continue
            meta = self.metadata[idx]
            if allowed and meta['source_file'] not in allowed:
                continue
            results.append({
                'text': meta['text'],
                'score': float(scores[0][i]),
                'source_file': meta['source_file'],
                'chunk_id': meta['chunk_id'],
                'chunk_index': meta.get('chunk_index', idx),
                'document_type': meta['document_type'],
            })
            if len(results) >= top_k:
                break
        return results

    def remove_by_source(self, source_file):
        original_count = len(self.metadata)
        to_remove = [i for i, m in enumerate(self.metadata) if m['source_file'] == source_file]
        
        if not to_remove:
            return 0
        
        keep_indices = [i for i in range(len(self.metadata)) if i not in to_remove]
        keep_metadata = [self.metadata[i] for i in keep_indices]
        
        if not keep_metadata:
            self.index = faiss.IndexFlatIP(self.embedding_engine.dimension)
            self.metadata = []
        else:
            keep_texts = [m['text'] for m in keep_metadata]
            keep_embeddings = self.embedding_engine.embed(keep_texts)
            faiss.normalize_L2(keep_embeddings)
            
            self.index = faiss.IndexFlatIP(self.embedding_engine.dimension)
            self.index.add(keep_embeddings)
            self.metadata = keep_metadata
        
        self._save()
        removed = original_count - len(self.metadata)
        logger.info(f"Removed {removed} chunks for {source_file}")
        return removed

    def _save(self):
        faiss.write_index(self.index, str(self.index_file))
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        with open(self.manifest_file, 'w', encoding='utf-8') as f:
            json.dump(self._current_manifest(), f, indent=2, ensure_ascii=False)

    def get_stats(self):
        return {
            'total_chunks': len(self.metadata),
            'total_vectors': self.index.ntotal,
            'unique_documents': len(set(m['source_file'] for m in self.metadata)),
        }

    def get_documents(self):
        doc_map = {}
        for m in self.metadata:
            src = m['source_file']
            if src not in doc_map:
                doc_map[src] = {'filename': src, 'chunk_count': 0, 'document_type': m['document_type']}
            doc_map[src]['chunk_count'] += 1
        return list(doc_map.values())

    def has_source(self, source_file):
        return any(m.get('source_file') == source_file for m in self.metadata)

    def get_indexed_sources(self):
        return {m.get('source_file') for m in self.metadata if m.get('source_file')}

    def is_empty(self):
        return self.index is None or self.index.ntotal == 0

    def _current_manifest(self):
        return {
            'embedding_model': Config.EMBEDDING_MODEL,
            'embedding_dimension': self.embedding_engine.dimension,
        }

    def _load_manifest(self):
        if not self.manifest_file.exists():
            return None
        try:
            with open(self.manifest_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as exc:
            logger.warning("Failed to load vector store manifest: %s", exc)
            return None

    def _manifest_matches(self, manifest):
        return (
            manifest.get('embedding_model') == Config.EMBEDDING_MODEL
            and manifest.get('embedding_dimension') == self.embedding_engine.dimension
        )
