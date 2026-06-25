"""File + console logging configuration."""
from __future__ import annotations
import logging
import os

def configure_logging(reports_dir: str, level: str = "INFO") -> None:
    os.makedirs(reports_dir, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(name)s: %(message)s"
    handlers = [
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(reports_dir, "app.log"), encoding="utf-8"),
    ]
    logging.basicConfig(level=getattr(logging, level), format=fmt, handlers=handlers, force=True)
