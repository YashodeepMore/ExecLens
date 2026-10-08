# Logging configuration for AI Observatory.
# Call setup_logging() once at app startup (in main.py).
# Log files are saved in backend/logs/ with date-time as filename.

import logging
import os
from datetime import datetime


def setup_logging():
    """
    Configures logging for the whole app.
    Creates a log file in backend/logs/ with timestamp name.
    Call this once at startup — all modules then use logging.getLogger(__name__).
    """

    # backend/logs/ directory
    backend_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    )
    log_dir = os.path.join(backend_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Log file: logs/2026-10-08_11-18-11.log
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_file = os.path.join(log_dir, f"{timestamp}.log")

    # Simple readable format
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Write to file (captures everything — DEBUG and above)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Print to console (only INFO and above)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Root logger — all loggers inherit from this
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.addHandler(file_handler)
    root.addHandler(console_handler)

    logging.getLogger("app.main").info(f"Logging started → {log_file}")

    return log_file
