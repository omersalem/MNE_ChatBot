import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retrieval import RetrievalEngine


class TestRetrievalEngine(unittest.TestCase):
    def setUp(self):
        self.engine = RetrievalEngine()

    def test_empty_retrieval(self):
        context, sources = self.engine.retrieve("nonexistent query about nothing", top_k=5)
        self.assertIsInstance(context, str)
        self.assertIsInstance(sources, list)

    def test_context_format(self):
        context, sources = self.engine.retrieve("test query")
        if context:
            self.assertIsInstance(context, str)
            self.assertGreater(len(context), 0)

    def test_sources_format(self):
        context, sources = self.engine.retrieve("test query")
        for source in sources:
            self.assertIn('filename', source)
            self.assertIn('chunk_id', source)
            self.assertIn('score', source)

    def test_tokenize_removes_stopwords(self):
        tokens = self.engine._tokenize("What is the exchange server version")
        self.assertIn('exchange', tokens)
        self.assertIn('server', tokens)
        self.assertIn('version', tokens)
        self.assertNotIn('what', tokens)
        self.assertNotIn('the', tokens)

    def test_rerank_filters_irrelevant_hits(self):
        results = [
            {'text': 'Completely unrelated content', 'score': 0.05, 'source_file': 'misc.md', 'chunk_id': '1', 'document_type': 'md'},
            {'text': 'Exchange Server 2019 Version 15.2', 'score': 0.31, 'source_file': 'infra.md', 'chunk_id': '2', 'document_type': 'md'},
        ]
        reranked = self.engine._rerank_results('exchange server version', results, top_k=2)
        self.assertEqual(len(reranked), 1)
        self.assertEqual(reranked[0]['chunk_id'], '2')

    def test_rerank_returns_empty_for_weak_generic_match(self):
        results = [
            {'text': 'Office policies and visitor badges', 'score': 0.42, 'source_file': 'handbook.txt', 'chunk_id': '1', 'document_type': 'txt'},
        ]
        reranked = self.engine._rerank_results('dress code policy', results, top_k=2)
        self.assertEqual(reranked, [])


if __name__ == '__main__':
    unittest.main()
