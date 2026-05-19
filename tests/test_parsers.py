import unittest
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from parsers.txt_parser import TxtParser
from parsers.md_parser import MdParser
from parsers.parser_factory import get_parser


class TestTxtParser(unittest.TestCase):
    def test_parse_txt(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("Hello world\nThis is a test.")
            f.flush()
            parser = TxtParser()
            result = parser.parse(f.name)
            self.assertIn("Hello world", result)
        os.unlink(f.name)


class TestMdParser(unittest.TestCase):
    def test_parse_md(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False) as f:
            f.write("# Heading\n\nSome **bold** text.")
            f.flush()
            parser = MdParser()
            result = parser.parse(f.name)
            self.assertIn("# Heading", result)
        os.unlink(f.name)


class TestParserFactory(unittest.TestCase):
    def test_txt_parser(self):
        parser = get_parser('test.txt')
        self.assertIsInstance(parser, TxtParser)

    def test_md_parser(self):
        parser = get_parser('test.md')
        self.assertIsInstance(parser, MdParser)

    def test_unsupported_type(self):
        with self.assertRaises(ValueError):
            get_parser('test.exe')


if __name__ == '__main__':
    unittest.main()
