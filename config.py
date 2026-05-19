import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    API_KEYS = {
        'openai': os.getenv('OPENAI_API_KEY', ''),
        'anthropic': os.getenv('ANTHROPIC_API_KEY', ''),
        'opencode': os.getenv('OPENCODE_API_KEY', ''),
        'gemini': os.getenv('GEMINI_API_KEY', ''),
        'hapuppy': os.getenv('HAPUPPY_API_KEY', ''),
    }
    
    OPENCODE_API_BASE_URL = os.getenv('OPENCODE_API_BASE_URL', 'http://localhost:8080/v1')
    HAPUPPY_BASE_URL = os.getenv('HAPUPPY_BASE_URL', 'https://beta.hapuppy.com/v1')
    
    COMPANY_DOCS_DIR = BASE_DIR / 'company_docs'
    VECTOR_DB_DIR = BASE_DIR / 'vector_db'
    LOG_DIR = BASE_DIR / 'logs'
    CACHE_DIR = BASE_DIR / 'cache'
    
    MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB
    ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt', 'md'}
    
    DEFAULT_MODEL = {
        'openai': 'gpt-4o-mini',
        'anthropic': 'claude-sonnet-4-20250514',
        'opencode': 'opencode-model',
        'gemini': 'gemini-2.0-flash',
        'hapuppy': 'gemini-2.5-flash',
    }
    
    ACTIVE_PROVIDER = os.getenv('ACTIVE_PROVIDER', 'openai')
    
    CHUNK_SIZE = 800
    CHUNK_OVERLAP = 120
    TOP_K = 4
    SEARCH_CANDIDATES = 12
    EMBEDDING_MODEL = 'all-MiniLM-L6-v2'
    
    MIN_VECTOR_SCORE = 0.30
    MIN_HYBRID_SCORE = 0.28
    MAX_CONTEXT_TOKENS = 2200
    ANSWER_TEMPERATURE = 0.1
    ANSWER_MAX_TOKENS = 500
