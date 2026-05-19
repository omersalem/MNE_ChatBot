import logging
import time
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from config import Config
from sync.processor import DocumentProcessor

logger = logging.getLogger(__name__)


class DocChangeHandler(FileSystemEventHandler):
    def __init__(self, processor):
        self.processor = processor
        self._debounce = {}
        self._lock = threading.Lock()

    def _should_process(self, path):
        p = Path(path)
        return p.suffix.lower().lstrip('.') in Config.ALLOWED_EXTENSIONS

    def _debounce_process(self, path):
        with self._lock:
            path_str = str(path)
            if path_str in self._debounce:
                self._debounce[path_str].cancel()

            timer = threading.Timer(2.0, self._process_file, args=[path])
            self._debounce[path_str] = timer
            timer.start()

    def _process_file(self, path):
        try:
            self.processor.process_file(path)
        except Exception as e:
            logger.error(f"Watchdog processing error for {path}: {e}")
        finally:
            with self._lock:
                self._debounce.pop(str(path), None)

    def on_created(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            logger.info(f"File created: {event.src_path}")
            self._debounce_process(event.src_path)

    def on_modified(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            logger.info(f"File modified: {event.src_path}")
            self._debounce_process(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self._should_process(event.src_path):
            filename = Path(event.src_path).name
            logger.info(f"File deleted: {filename}")
            try:
                self.processor.delete_file(filename)
            except Exception as e:
                logger.error(f"Error deleting vectors for {filename}: {e}")


class DocWatcher:
    def __init__(self):
        self.processor = DocumentProcessor()
        self.observer = Observer()
        self.handler = DocChangeHandler(self.processor)
        self._running = False

    def start(self):
        if self._running:
            return
        Config.COMPANY_DOCS_DIR.mkdir(parents=True, exist_ok=True)
        self.observer.schedule(self.handler, str(Config.COMPANY_DOCS_DIR), recursive=False)
        self.observer.start()
        self._running = True
        logger.info(f"Document watcher started on {Config.COMPANY_DOCS_DIR}")

    def stop(self):
        if self._running:
            self.observer.stop()
            self.observer.join()
            self._running = False
            logger.info("Document watcher stopped")

    def is_running(self):
        return self._running
