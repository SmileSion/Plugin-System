"""
Author: SmileSion
Date: 2025-07-30
Description: 插件关闭钩子。
"""
import atexit
from multiprocessing import Process

_running_processes = []

def add_process(p: Process):
    _running_processes.append(p)

def cleanup_processes():
    for p in _running_processes:
        if p.is_alive():
            print(f"[清理] 终止子进程 {p.pid}")
            p.terminate()

atexit.register(cleanup_processes)
