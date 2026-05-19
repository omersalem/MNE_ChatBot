import logging
from pathlib import Path
from parsers.parser_factory import get_parser
from rag.chunker import Chunker
from rag.vector_store import VectorStore
from config import Config

logger = logging.getLogger(__name__)


class DocumentProcessor:
    def __init__(self):
        self.chunker = Chunker(chunk_size=Config.CHUNK_SIZE, overlap=Config.CHUNK_OVERLAP)
        self.vector_store = VectorStore()

    def process_file(self, file_path):
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        filename = file_path.name
        ext = file_path.suffix.lower().lstrip('.')

        logger.info(f"Processing file: {filename}")

        parser = get_parser(str(file_path))
        text = parser.parse(str(file_path))

        if not text.strip():
            logger.warning(f"Empty document: {filename}")
            return {'filename': filename, 'chunks': 0, 'status': 'empty'}

        self.vector_store.remove_by_source(filename)

        chunks = self.chunker.chunk(text, source_file=filename, document_type=ext)
        self.vector_store.add_chunks(chunks)

        logger.info(f"Indexed {filename}: {len(chunks)} chunks")
        return {'filename': filename, 'chunks': len(chunks), 'status': 'indexed'}

    def process_all(self):
        docs_dir = Config.COMPANY_DOCS_DIR
        results = []

        for ext in Config.ALLOWED_EXTENSIONS:
            for file_path in docs_dir.glob(f'*.{ext}'):
                try:
                    result = self.process_file(file_path)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Failed to process {file_path}: {e}")
                    results.append({'filename': file_path.name, 'chunks': 0, 'status': 'error', 'error': str(e)})

        return results

    def delete_file(self, filename):
        # Normalize incoming names to avoid path traversal and ensure a single file target.
        safe_name = Path(filename).name
        file_path = Config.COMPANY_DOCS_DIR / safe_name

        removed = self.vector_store.remove_by_source(safe_name)
        file_deleted = False

        if file_path.exists() and file_path.is_file():
            file_path.unlink()
            file_deleted = True

        logger.info(f"Deleted {safe_name}: removed {removed} chunks, file_deleted={file_deleted}")
        return {'filename': safe_name, 'removed_chunks': removed, 'file_deleted': file_deleted}
