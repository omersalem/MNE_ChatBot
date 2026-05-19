import hashlib
import os
import secrets
import json
from pathlib import Path
from config import Config


class AuthManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.auth_file = Config.CACHE_DIR / 'auth.json'
        Config.CACHE_DIR.mkdir(exist_ok=True)
        self._init_admin()
        self._initialized = True

    def _init_admin(self):
        default_pw = 'fi@!2121@'
        if not self.auth_file.exists():
            self._set_password(default_pw)
        else:
            try:
                with open(self.auth_file) as f:
                    data = json.load(f)
                if not data.get('password_hash') or not data.get('salt'):
                    self._set_password(default_pw)
            except Exception:
                self._set_password(default_pw)

    def _set_password(self, password):
        salt = secrets.token_hex(16)
        password_hash = hashlib.sha256((salt + password).encode()).hexdigest()
        with open(self.auth_file, 'w') as f:
            json.dump({'salt': salt, 'password_hash': password_hash}, f)

    def verify_password(self, password):
        try:
            with open(self.auth_file) as f:
                data = json.load(f)
            salt = data.get('salt', '')
            stored_hash = data.get('password_hash', '')
            computed = hashlib.sha256((salt + password).encode()).hexdigest()
            return computed == stored_hash
        except Exception:
            return False

    def change_password(self, old_password, new_password):
        if not self.verify_password(old_password):
            return False
        self._set_password(new_password)
        return True

    def generate_session_token(self):
        return secrets.token_hex(32)

    def validate_session(self, token):
        try:
            session_file = Config.CACHE_DIR / 'session.json'
            if not session_file.exists():
                return False
            with open(session_file) as f:
                data = json.load(f)
            return data.get('token') == token
        except Exception:
            return False

    def save_session(self, token):
        session_file = Config.CACHE_DIR / 'session.json'
        with open(session_file, 'w') as f:
            json.dump({'token': token}, f)

    def clear_session(self):
        session_file = Config.CACHE_DIR / 'session.json'
        if session_file.exists():
            session_file.unlink()
