import json
import logging
import re
from collections import Counter
from pathlib import Path
from config import Config

logger = logging.getLogger(__name__)


class SuggestedQuestions:
    def __init__(self):
        self.cache_file = Config.CACHE_DIR / 'suggested_questions.json'
        Config.CACHE_DIR.mkdir(exist_ok=True)

    def get_questions(self):
        questions = self._load_cache()
        if not questions:
            questions = self._generate_questions()
            self._save_cache(questions)
        return questions

    def refresh(self):
        questions = self._generate_questions()
        self._save_cache(questions)
        return questions

    def _generate_questions(self):
        from rag.vector_store import VectorStore
        vector_store = VectorStore()
        documents = vector_store.get_documents()
        
        if not documents:
            return []

        questions = []
        metadata = vector_store.metadata

        for doc in documents:
            filename = doc['filename']
            name_no_ext = Path(filename).stem

            questions.append(f"What is in the {name_no_ext} document?")
            questions.append(f"Summarize the {name_no_ext} document")

        doc_chunks = {}
        for m in metadata:
            src = m['source_file']
            if src not in doc_chunks:
                doc_chunks[src] = []
            doc_chunks[src].append(m['text'])

        for src, chunks in doc_chunks.items():
            combined = ' '.join(chunks)
            headings = re.findall(r'#{1,6}\s+(.+)', combined)
            for heading in headings[:3]:
                questions.append(f"What does the document say about {heading.strip()}?")

            words = re.findall(r'\b[A-Z][a-zA-Z]{3,}\b', combined)
            common = Counter(words).most_common(10)
            for word, _ in common[:2]:
                questions.append(f"Tell me about {word} in the documents")

        seen = set()
        unique = []
        for q in questions:
            q_lower = q.lower()
            if q_lower not in seen:
                seen.add(q_lower)
                unique.append(q)

        return unique[:20]

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading question cache: {e}")
        return []

    def _save_cache(self, questions):
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(questions, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving question cache: {e}")
