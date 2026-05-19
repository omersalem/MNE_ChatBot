import unittest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.chunker import Chunker


class TestChunker(unittest.TestCase):
    def setUp(self):
        self.chunker = Chunker(chunk_size=100, overlap=20)

    def test_basic_chunking(self):
        text = "Paragraph one content here.\n\nParagraph two content here.\n\nParagraph three content here."
        chunks = self.chunker.chunk(text, source_file='test.txt')
        self.assertGreater(len(chunks), 0)

    def test_chunk_metadata(self):
        text = "Test content"
        chunks = self.chunker.chunk(text, source_file='test.txt', document_type='txt')
        chunk = chunks[0]
        self.assertIn('source_file', chunk)
        self.assertIn('chunk_id', chunk)
        self.assertIn('chunk_index', chunk)
        self.assertIn('timestamp', chunk)
        self.assertIn('document_type', chunk)
        self.assertEqual(chunk['source_file'], 'test.txt')
        self.assertEqual(chunk['document_type'], 'txt')

    def test_empty_text(self):
        chunks = self.chunker.chunk('', source_file='test.txt')
        self.assertEqual(len(chunks), 0)

    def test_chunk_size_respected(self):
        text = "A" * 300
        chunks = self.chunker.chunk(text, source_file='test.txt')
        for chunk in chunks:
            self.assertLessEqual(len(chunk['text']), self.chunker.chunk_size + 50)

    def test_markdown_table_normalization(self):
        text = "## Messaging\n\n| Property | Value |\n|---|---|\n| Version | CU 15.2 |\n| Edition | Enterprise |\n"
        chunks = self.chunker.chunk(text, source_file='test.md', document_type='md')
        self.assertTrue(any('Property: Version; Value: CU 15.2' in chunk['text'] for chunk in chunks))

    def test_ascii_art_is_skipped(self):
        text = "## Topology\n\n┌────┐\n│ FW │\n└────┘\n\nUseful paragraph here."
        chunks = self.chunker.chunk(text, source_file='test.md', document_type='md')
        combined = '\n'.join(chunk['text'] for chunk in chunks)
        self.assertIn('Useful paragraph here.', combined)
        self.assertNotIn('┌────┐', combined)


if __name__ == '__main__':
    unittest.main()
