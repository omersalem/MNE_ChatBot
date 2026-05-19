import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path
from flask import Flask, send_from_directory
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.config['WTF_CSRF_ENABLED'] = False

    setup_logging(app)

    Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per day", "50 per hour"],
        storage_uri="memory://",
    )

    from routes.chat import chat_bp
    from routes.admin import admin_bp
    from routes.upload import upload_bp
    from routes.auth import auth_bp
    from routes.settings import settings_bp
    app.register_blueprint(chat_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(upload_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(settings_bp)

    client_dist = Path(__file__).resolve().parent / 'client' / 'dist'

    @app.route('/')
    def index():
        if client_dist.exists():
            return send_from_directory(str(client_dist), 'index.html')
        return {'status': 'ok', 'message': 'RAG API running. Frontend not built yet.'}, 200

    @app.route('/<path:path>')
    def static_files(path):
        if client_dist.exists():
            file_path = client_dist / path
            if file_path.exists():
                return send_from_directory(str(client_dist), path)
            return send_from_directory(str(client_dist), 'index.html')
        return {'error': 'Not found'}, 404

    @app.route('/health')
    def health():
        return {'status': 'ok'}, 200

    return app


def setup_logging(app):
    log_dir = Path(app.config.get('LOG_DIR', 'logs'))
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'app.log'

    file_handler = RotatingFileHandler(log_file, maxBytes=10485760, backupCount=5)
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    ))
    file_handler.setLevel(logging.INFO)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] %(message)s'
    ))
    console_handler.setLevel(logging.DEBUG)

    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)
