import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from config import Config


class GroupManager:
    def __init__(self):
        Config.CACHE_DIR.mkdir(exist_ok=True)
        self.groups_file = Config.CACHE_DIR / 'groups.json'
        self._data = self._load()

    def _refresh(self):
        self._data = self._load()

    def _load(self):
        if self.groups_file.exists():
            try:
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, dict) and isinstance(data.get('groups'), list):
                        data['groups'] = [self._repair_group(group) for group in data.get('groups', [])]
                        return data
            except Exception:
                pass
        return {'groups': []}

    def _repair_text(self, value):
        if not isinstance(value, str):
            return value
        if 'Ø' in value or 'Ù' in value:
            try:
                return value.encode('latin1').decode('utf-8')
            except Exception:
                return value
        return value

    def _repair_group(self, group):
        if not isinstance(group, dict):
            return group
        repaired = dict(group)
        repaired['name'] = self._repair_text(repaired.get('name', ''))
        repaired['description'] = self._repair_text(repaired.get('description', ''))
        repaired_docs = []
        for doc in repaired.get('documents', []) or []:
            repaired_docs.append(self._repair_text(doc))
        repaired['documents'] = repaired_docs
        return repaired

    def _save(self):
        with open(self.groups_file, 'w', encoding='utf-8') as f:
            json.dump(self._data, f, ensure_ascii=False, indent=2)

    def _normalize_documents(self, documents):
        normalized = []
        for doc in documents or []:
            name = Path(str(doc)).name
            if name and name not in normalized:
                normalized.append(name)
        return normalized

    def list_groups(self):
        self._refresh()
        return list(self._data.get('groups', []))

    def get_group(self, group_id):
        self._refresh()
        for group in self._data.get('groups', []):
            if group.get('id') == group_id:
                return group
        return None

    def create_group(self, payload):
        self._refresh()
        group = {
            'id': str(uuid4()),
            'name': (payload.get('name') or '').strip(),
            'description': (payload.get('description') or '').strip(),
            'documents': self._normalize_documents(payload.get('documents', [])),
            'color': (payload.get('color') or 'gold').strip() or 'gold',
            'created_at': datetime.now(timezone.utc).isoformat(),
            'updated_at': datetime.now(timezone.utc).isoformat(),
        }
        if not group['name']:
            raise ValueError('Group name is required')
        self._data['groups'].append(group)
        self._save()
        return group

    def update_group(self, group_id, payload):
        self._refresh()
        group = self.get_group(group_id)
        if not group:
            raise ValueError('Group not found')

        if 'name' in payload:
            group['name'] = (payload.get('name') or '').strip()
            if not group['name']:
                raise ValueError('Group name is required')
        if 'description' in payload:
            group['description'] = (payload.get('description') or '').strip()
        if 'documents' in payload:
            group['documents'] = self._normalize_documents(payload.get('documents', []))
        if 'color' in payload:
            group['color'] = (payload.get('color') or 'gold').strip() or 'gold'

        group['updated_at'] = datetime.now(timezone.utc).isoformat()
        self._save()
        return group

    def delete_group(self, group_id):
        self._refresh()
        groups = self._data.get('groups', [])
        original_len = len(groups)
        self._data['groups'] = [g for g in groups if g.get('id') != group_id]
        removed = original_len - len(self._data['groups'])
        self._save()
        return removed > 0

    def remove_document_everywhere(self, filename):
        self._refresh()
        target = Path(str(filename)).name
        changed = False

        for group in self._data.get('groups', []):
            docs = group.get('documents', [])
            filtered = [doc for doc in docs if Path(str(doc)).name != target]
            if len(filtered) != len(docs):
                group['documents'] = filtered
                group['updated_at'] = datetime.now(timezone.utc).isoformat()
                changed = True

        if changed:
            self._save()

        return changed

    def prune_missing_documents(self, available_documents):
        self._refresh()
        available = {Path(str(doc)).name for doc in (available_documents or [])}
        changed = False

        for group in self._data.get('groups', []):
            docs = group.get('documents', [])
            filtered = [doc for doc in docs if Path(str(doc)).name in available]
            if len(filtered) != len(docs):
                group['documents'] = filtered
                group['updated_at'] = datetime.now(timezone.utc).isoformat()
                changed = True

        if changed:
            self._save()

        return changed
