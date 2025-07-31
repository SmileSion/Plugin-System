"""
Author: SmileSion
Date: 2025-07-31
Description: 日志处理模块。
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import tarfile
import threading

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "plugin.log")

def compress_to_tar_gz(filename):
    """
    压缩指定日志文件为 .tar.gz 格式，压缩完成后删除原文件。
    """
    if not os.path.exists(filename):
        return
    tar_gz_name = f"{filename}.tar.gz"
    with tarfile.open(tar_gz_name, "w:gz") as tar:
        tar.add(filename, arcname=os.path.basename(filename))
    try:
        os.remove(filename)
    except PermissionError:
        pass

class CompressingRotatingFileHandler(RotatingFileHandler):
    """
    按大小切割日志，切割后异步压缩为 tar.gz 格式。
    """
    def doRollover(self):
        super().doRollover()
        threading.Thread(target=self.compress_logs, daemon=True).start()

    def compress_logs(self):
        for filename in os.listdir(LOG_DIR):
            if filename.startswith("plugin.log.") and not filename.endswith(".tar.gz"):
                compress_to_tar_gz(os.path.join(LOG_DIR, filename))

def setup_logger(name="plugin_logger", max_bytes=50*1024*1024, backup_count=7):

    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        handler = CompressingRotatingFileHandler(
            LOG_FILE,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
            delay=True
        )
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s [%(name)s] %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger

def close_logger(logger):
    for handler in logger.handlers[:]:
        try:
            handler.close()
        except Exception:
            pass
        logger.removeHandler(handler)

