import logging
import markdown

logger = logging.getLogger(__name__)


class MdParser:
    def parse(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_md = f.read()
            html = markdown.markdown(raw_md)
            return raw_md
        except Exception as e:
            logger.error(f"Markdown parse error for {file_path}: {e}")
            raise
