import logging
from pypdf import PdfReader

logger = logging.getLogger(__name__)


class PdfParser:
    def parse(self, file_path):
        try:
            reader = PdfReader(file_path)
            text_parts = []
            for page in reader.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
            return '\n\n'.join(text_parts)
        except Exception as e:
            logger.error(f"PDF parse error for {file_path}: {e}")
            raise
