import logging
from pathlib import Path
from flask import Blueprint, send_from_directory, jsonify, request
from config import Config
from rag.vector_store import VectorStore
from providers.provider_manager import ProviderManager
from sync.processor import DocumentProcessor
from utils.group_manager import GroupManager

logger = logging.getLogger(__name__)

admin_bp = Blueprint('admin', __name__)
vector_store = VectorStore()
provider_manager = ProviderManager()
processor = DocumentProcessor()
group_manager = GroupManager()


def _list_company_documents():
    docs = []
    for ext in Config.ALLOWED_EXTENSIONS:
        for file_path in Config.COMPANY_DOCS_DIR.glob(f'*.{ext}'):
            docs.append(file_path.name)
    return sorted(set(docs), key=lambda x: x.lower())


@admin_bp.route('/')
def dashboard():
    client_dist = Path(__file__).resolve().parent.parent / 'client' / 'dist'
    if client_dist.exists():
        return send_from_directory(str(client_dist), 'index.html')
    return jsonify({'error': 'Frontend not built'}), 503


@admin_bp.route('/api/documents', methods=['GET'])
def list_documents():
    documents = vector_store.get_documents()
    return jsonify({'documents': documents})


@admin_bp.route('/api/documents/<filename>/reindex', methods=['POST'])
def reindex_document(filename):
    file_path = Config.COMPANY_DOCS_DIR / filename
    if not file_path.exists():
        return jsonify({'error': 'File not found'}), 404
    try:
        result = processor.process_file(file_path)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    try:
        result = processor.delete_file(filename)
        group_manager.remove_document_everywhere(filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/reindex-all', methods=['POST'])
def reindex_all():
    try:
        results = processor.process_all()
        return jsonify({'results': results})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/health', methods=['GET'])
def health_check():
    health = provider_manager.health_check_all()
    return jsonify({'providers': health})


@admin_bp.route('/api/stats', methods=['GET'])
def stats():
    return jsonify(vector_store.get_stats())


@admin_bp.route('/api/groups', methods=['GET'])
def list_groups():
    available_docs = _list_company_documents()
    group_manager.prune_missing_documents(available_docs)
    return jsonify({'groups': group_manager.list_groups()})


@admin_bp.route('/api/groups', methods=['POST'])
def create_group():
    data = request.get_json() or {}
    try:
        group = group_manager.create_group(data)
        return jsonify(group), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/groups/<group_id>', methods=['PUT'])
def update_group(group_id):
    data = request.get_json() or {}
    try:
        group = group_manager.update_group(group_id, data)
        return jsonify(group)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@admin_bp.route('/api/groups/<group_id>', methods=['DELETE'])
def delete_group(group_id):
    deleted = group_manager.delete_group(group_id)
    if not deleted:
        return jsonify({'error': 'Group not found'}), 404
    return jsonify({'deleted': True})


@admin_bp.route('/api/groups/documents', methods=['GET'])
def list_group_documents():
    return jsonify({'documents': _list_company_documents()})
