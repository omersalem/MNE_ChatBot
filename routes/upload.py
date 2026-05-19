import logging
from pathlib import Path
from uuid import uuid4
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename
from config import Config
from sync.processor import DocumentProcessor

logger = logging.getLogger(__name__)

upload_bp = Blueprint('upload', __name__)
processor = DocumentProcessor()


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def build_safe_filename(filename):
    raw_name = Path(filename).name.strip()
    ext = Path(raw_name).suffix.lower().lstrip('.')
    stem = Path(raw_name).stem

    safe_stem = secure_filename(stem)
    if not safe_stem:
        safe_stem = f"document_{uuid4().hex[:8]}"

    if ext:
        return f"{safe_stem}.{ext}"
    return safe_stem


@upload_bp.route('/api/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': f'File type not allowed. Allowed: {Config.ALLOWED_EXTENSIONS}'}), 400

    filename = build_safe_filename(file.filename)
    file_path = Config.COMPANY_DOCS_DIR / filename

    content = file.read()
    if len(content) > Config.MAX_UPLOAD_SIZE:
        return jsonify({'error': 'File too large. Maximum 50MB'}), 413

    file_path.write_bytes(content)

    try:
        result = processor.process_file(file_path)
        return jsonify(result)
    except Exception as e:
        logger.error(f"Upload processing error: {e}")
        return jsonify({'error': str(e)}), 500
