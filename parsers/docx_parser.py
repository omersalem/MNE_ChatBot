import logging
from docx import Document

logger = logging.getLogger(__name__)


class DocxParser:
    def parse(self, file_path):
        try:
            doc = Document(file_path)
            text_parts = []
            for para in doc.paragraphs:
                text_parts.append(para.text)
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f"DOCX parse error for {file_path}: {e}")
            raise
