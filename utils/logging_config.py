import logging
import os
import time
from collections import deque
import queue
import datetime

# Cola para almacenar logs en tiempo real para SSE
log_queue = queue.Queue(maxsize=100)

# Cache volátil para las últimas 6 horas
# Almacena tuplas (timestamp, mensaje)
log_cache = deque()
SIX_HOURS_IN_SECONDS = 6 * 60 * 60

class DailyRotatingFileHandler(logging.FileHandler):
    def __init__(self, log_dir, prefix="logs_", suffix=".txt", backupCount=30, encoding='utf-8'):
        self.log_dir = log_dir
        self.prefix = prefix
        self.suffix = suffix
        self.backupCount = backupCount
        self.current_date = datetime.datetime.now().strftime("%Y%m%d")
        
        filename = os.path.join(log_dir, f"{prefix}{self.current_date}{suffix}")
        super().__init__(filename, encoding=encoding)

    def emit(self, record):
        current_date_check = datetime.datetime.now().strftime("%Y%m%d")
        if self.current_date != current_date_check:
            self.current_date = current_date_check
            self.close()
            self.baseFilename = os.path.join(self.log_dir, f"{self.prefix}{self.current_date}{self.suffix}")
            self.stream = self._open()
            self._cleanup()
        super().emit(record)

    def _cleanup(self):
        try:
            now = time.time()
            sixty_days_in_seconds = 60 * 24 * 60 * 60
            files = [f for f in os.listdir(self.log_dir) if f.startswith(self.prefix) and f.endswith(self.suffix)]
            
            for file_name in files:
                file_path = os.path.join(self.log_dir, file_name)
                try:
                    # Si la fecha de modificación es mayor a 60 días
                    if os.path.getmtime(file_path) < now - sixty_days_in_seconds:
                        os.remove(file_path)
                except Exception:
                    pass
        except Exception:
            pass

class QueueHandler(logging.Handler):
    def emit(self, record):
        try:
            msg = self.format(record)
            now = time.time()
            
            # Añadir a la cola SSE
            if log_queue.full():
                log_queue.get_nowait()
            log_queue.put_nowait(msg)
            
            # Añadir al cache de 6 horas
            log_cache.append((now, msg))
            
            # Limpiar logs antiguos (mayores a 6 horas)
            while log_cache and log_cache[0][0] < now - SIX_HOURS_IN_SECONDS:
                log_cache.popleft()
                
        except Exception:
            self.handleError(record)

def setup_logging(app):
    log_dir = os.path.join(app.root_path, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # Handler para rotación diaria
    file_handler = DailyRotatingFileHandler(log_dir)
    file_handler.setFormatter(logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    ))
    
    # Handler para la cola SSE
    q_handler = QueueHandler()
    q_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

    # Configuración del logger raíz
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(q_handler)
    
    # También añadir a Flask app logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(q_handler)

def get_log_stream():
    while True:
        try:
            # Esperar como máximo 15 segundos para evitar que Gunicorn detecte un "worker timeout"
            msg = log_queue.get(timeout=15)
            yield f"data: {msg}\n\n"
        except queue.Empty:
            # Enviar un comentario SSE vacío para mantener la conexión viva y reiniciar el contador de timeout de Gunicorn
            yield ": keepalive\n\n"

def get_recent_logs():
    """Devuelve los logs de las últimas 6 horas almacenados en el cache volátil."""
    now = time.time()
    return [msg for ts, msg in log_cache if ts >= now - SIX_HOURS_IN_SECONDS]
