import logging

logger = logging.getLogger(__name__)


class TxtParser:
    def parse(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            with open(file_path, 'r', encoding='latin-1') as f:
                return f.read()
        except Exception as e:
            logger.error(f"TXT parse error for {file_path}: {e}")
            raise
