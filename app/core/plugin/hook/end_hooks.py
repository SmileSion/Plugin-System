"""
Author: SmileSion
Date: 2025-07-30
Description: 插件关闭钩子。
"""
import atexit
from multiprocessing import Process
from app.utils.log_utils import setup_logger

logger = setup_logger("plugin_shutdown")

_running_processes = []

def add_process(p: Process):
    _running_processes.append(p)
    logger.debug(f"已添加子进程 {p.pid} 到管理列表")

def cleanup_processes():
    logger.info("应用关闭中，开始清理子进程...")
    for p in _running_processes:
        if p.is_alive():
            logger.warning(f"[清理] 正在终止子进程 {p.pid}")
            p.terminate()
    logger.info("子进程清理完毕")

atexit.register(cleanup_processes)
