import re
import uuid
from datetime import datetime, timezone


class Chunker:
    def __init__(self, chunk_size=500, overlap=100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text, source_file, document_type='text'):
        cleaned_text = self._normalize_text(text)
        paragraphs = cleaned_text.split('\n\n')
        chunks = []
        current_chunk = ''
        chunk_index = 0

        for para in paragraphs:
            para = para.strip()
            if not para or self._should_skip_paragraph(para):
                continue

            if len(current_chunk) + len(para) <= self.chunk_size:
                current_chunk += ('\n\n' if current_chunk else '') + para
            else:
                if current_chunk:
                    chunks.append(self._make_chunk(current_chunk, source_file, document_type, chunk_index))
                    chunk_index += 1
                current_chunk = para

                while len(current_chunk) > self.chunk_size:
                    split_point = self._find_split_point(current_chunk, self.chunk_size)
                    chunks.append(self._make_chunk(current_chunk[:split_point], source_file, document_type, chunk_index))
                    chunk_index += 1
                    current_chunk = current_chunk[split_point - self.overlap:] if split_point > self.overlap else current_chunk[split_point:]

        if current_chunk:
            chunks.append(self._make_chunk(current_chunk, source_file, document_type, chunk_index))

        return chunks

    def _make_chunk(self, text, source_file, document_type, chunk_index):
        return {
            'text': text,
            'source_file': source_file,
            'chunk_id': str(uuid.uuid4()),
            'chunk_index': chunk_index,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'document_type': document_type,
        }

    def _find_split_point(self, text, max_length):
        if len(text) <= max_length:
            return len(text)

        split_point = max_length
        for sep in ['.', '!', '?', '\n', ';', ',']:
            last_sep = text.rfind(sep, 0, max_length)
            if last_sep > max_length * 0.5:
                split_point = max(split_point, last_sep + 1)
                break

        return min(split_point, max_length)

    def _normalize_text(self, text):
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        text = self._convert_markdown_tables(text)
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text.strip()

    def _convert_markdown_tables(self, text):
        lines = text.split('\n')
        converted = []
        i = 0

        while i < len(lines):
            line = lines[i]

            if self._is_table_line(line):
                table_lines = []
                while i < len(lines) and self._is_table_line(lines[i]):
                    table_lines.append(lines[i])
                    i += 1
                converted.append(self._format_markdown_table(table_lines))
                continue

            converted.append(line)
            i += 1

        return '\n'.join(part for part in converted if part is not None)

    def _is_table_line(self, line):
        stripped = line.strip()
        return stripped.startswith('|') and stripped.endswith('|') and stripped.count('|') >= 2

    def _format_markdown_table(self, table_lines):
        if len(table_lines) < 2:
            return '\n'.join(table_lines)

        header_cells = self._split_table_row(table_lines[0])
        separator_cells = self._split_table_row(table_lines[1])
        if not header_cells or not separator_cells:
            return '\n'.join(table_lines)

        formatted_rows = []
        for row in table_lines[2:]:
            cells = self._split_table_row(row)
            if not cells:
                continue
            pairs = []
            for idx, header in enumerate(header_cells):
                value = cells[idx] if idx < len(cells) else ''
                header = self._clean_cell(header)
                value = self._clean_cell(value)
                if header and value:
                    pairs.append(f"{header}: {value}")
            if pairs:
                formatted_rows.append('; '.join(pairs))

        return '\n'.join(formatted_rows) if formatted_rows else '\n'.join(table_lines)

    def _split_table_row(self, row):
        stripped = row.strip().strip('|')
        if not stripped:
            return []
        return [cell.strip() for cell in stripped.split('|')]

    def _clean_cell(self, value):
        value = value.replace('**', '').replace('`', '').strip()
        return re.sub(r'\s+', ' ', value)

    def _should_skip_paragraph(self, para):
        stripped = para.strip()
        if not stripped:
            return True
        if re.fullmatch(r'[-_=]{3,}', stripped):
            return True
        if '](#' in stripped:
            return True
        if self._is_ascii_art(stripped):
            return True
        return False

    def _is_ascii_art(self, text):
        box_chars = sum(1 for ch in text if ch in '│┌┐└┘├┤┬┴┼─')
        if box_chars >= 8:
            return True
        return bool(re.fullmatch(r'[\s\W_]+', text)) and len(text) > 20
