import logging
from logging.handlers import TimedRotatingFileHandler
import os
import gzip
import shutil

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "plugin.log")

def compress_old_log(filename):
    if os.path.exists(filename):
        with open(filename, 'rb') as f_in:
            with gzip.open(f"{filename}.gz", 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        os.remove(filename)

class CompressingTimedRotatingFileHandler(TimedRotatingFileHandler):
    def doRollover(self):
        super().doRollover()
        # 压缩最近切割出来的日志
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("plugin.log.") and not filename.endswith(".gz"):
                compress_old_log(os.path.join(LOG_DIR, filename))

def setup_logger(name="plugin_logger"):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = CompressingTimedRotatingFileHandler(
            LOG_FILE, when="midnight", interval=1, backupCount=7, encoding="utf-8"
        )
        formatter = logging.Formatter(
            '[%(asctime)s] %(levelname)s [%(name)s] %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
