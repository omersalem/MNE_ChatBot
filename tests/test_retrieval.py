import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.retrieval import RetrievalEngine


class TestRetrievalEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RetrievalEngine()

    def test_empty_retrieval(self):
        context, sources = self.engine.retrieve("nonexistent query about nothing", top_k=5)
        self.assertIsInstance(context, str)
        self.assertIsInstance(sources, list)

    def test_context_format(self):
        context, _ = self.engine.retrieve("test query")
        if context:
            self.assertIsInstance(context, str)
            self.assertGreater(len(context), 0)

    def test_sources_format(self):
        _, sources = self.engine.retrieve("test query")
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

    def test_arabic_token_normalization_supports_prefixes_and_suffixes(self):
        tokens = self.engine._tokenize("ما هي الأهداف المطلوبة للتجارة الإلكترونية")
        self.assertIn('اهداف', tokens)
        self.assertIn('تجار', tokens)
        self.assertNotIn('ما', tokens)

    def test_build_query_profile_expands_goal_queries(self):
        profile = self.engine._build_query_profile("ما هي اهداف قانون التجارة الإلكترونية")
        self.assertTrue(profile['asks_about_goals'])
        self.assertTrue(profile['mentions_ecommerce'])
        normalized_boosts = {self.engine._normalize_text(item) for item in profile['boost_phrases']}
        self.assertIn('الاهداف', normalized_boosts)
        self.assertIn('يهدف هذا القرار بقانون الي تحقيق الاتي', normalized_boosts)

    def test_rerank_prefers_goal_section_for_goal_question(self):
        profile = self.engine._build_query_profile("ما هي اهداف قانون التجارة الإلكترونية")
        results = [
            {
                'text': 'مادة 24 تطبيق القوانين ذات العلاقة تتعلق بالنزاعات الناشئة عن تفسير العقد التجاري الإلكتروني.',
                'score': 0.55,
                'source_file': '2025.pdf',
                'chunk_id': 'late-article',
                'chunk_index': 10,
                'document_type': 'pdf',
            },
            {
                'text': 'مادة 2 الأهداف يهدف هذا القرار بقانون إلى تحقيق الآتي: تنظيم وضبط التجارة الإلكترونية وتعزيز ثقة المستهلك.',
                'score': 0.42,
                'source_file': '2025.pdf',
                'chunk_id': 'goals-article',
                'chunk_index': 1,
                'document_type': 'pdf',
            },
        ]
        reranked = self.engine._rerank_results(profile, results, top_k=2)
        self.assertEqual(reranked[0]['chunk_id'], 'goals-article')

    def test_rerank_returns_empty_for_weak_generic_match(self):
        profile = self.engine._build_query_profile('dress code policy')
        results = [
            {
                'text': 'Office policies and visitor badges',
                'score': 0.42,
                'source_file': 'handbook.txt',
                'chunk_id': '1',
                'chunk_index': 0,
                'document_type': 'txt',
            },
        ]
        reranked = self.engine._rerank_results(profile, results, top_k=2)
        self.assertEqual(reranked, [])


if __name__ == '__main__':
    unittest.main()
