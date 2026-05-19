from pathlib import Path
from parsers.txt_parser import TxtParser
from parsers.md_parser import MdParser
from parsers.pdf_parser import PdfParser
from parsers.docx_parser import DocxParser

PARSERS = {
    'txt': TxtParser,
    'md': MdParser,
    'pdf': PdfParser,
    'docx': DocxParser,
}


def get_parser(file_path):
    ext = Path(file_path).suffix.lower().lstrip('.')
    if ext not in PARSERS:
        raise ValueError(f"Unsupported file type: .{ext}")
    return PARSERS[ext]()
