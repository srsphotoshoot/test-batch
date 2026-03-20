"""
Shared logging utilities
"""
import logging
import json
from typing import Optional
import uuid

# ==================================================
# LOGGING CONFIG
# ==================================================
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s - %(message)s"
logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)

class ContextLogger:
    """Logger with request_id and batch_id context"""
    
    def __init__(self, name: str, request_id: Optional[str] = None, batch_id: Optional[str] = None):
        self.logger = logging.getLogger(name)
        self.request_id = request_id or str(uuid.uuid4())[:8]
        self.batch_id = batch_id
    
    def _format_context(self, message: str) -> str:
        context = f"[REQ:{self.request_id}]"
        if self.batch_id:
            context += f"[BATCH:{self.batch_id[:8]}]"
        return f"{context} {message}"
    
    def info(self, message: str):
        self.logger.info(self._format_context(message))
    
    def error(self, message: str):
        self.logger.error(self._format_context(message))
    
    def warning(self, message: str):
        self.logger.warning(self._format_context(message))
    
    def debug(self, message: str):
        self.logger.debug(self._format_context(message))
    
    def json_log(self, event: str, **kwargs):
        """Log structured JSON for monitoring"""
        log_data = {
            "event": event,
            "request_id": self.request_id,
            "batch_id": self.batch_id,
            **kwargs
        }
        self.logger.info(json.dumps(log_data))
