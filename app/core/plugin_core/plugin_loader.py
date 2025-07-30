"""
Author: SmileSion
Date: 2025-07-30
Description: 插件加载模块。
"""
import os
import sys
import importlib.util
from multiprocessing import Process, Queue

from app.core.plugin_core.plugin_base import PluginBase
from app.core.hook_core.end_hooks import add_process
from app.utils.log_utils import setup_logger

PLUGIN_ROOT = os.path.abspath("plugins")
loaded_plugins = {}
logger = setup_logger("plugin_loader")


def load_plugin(entry_path, name):
    entry_path = os.path.abspath(entry_path)
    logger.info(f"开始加载插件 {name}，路径：{entry_path}")

    if not entry_path.startswith(PLUGIN_ROOT + os.sep):
        logger.error(f"尝试加载非法路径的插件：{entry_path}")
        raise ValueError(f"禁止加载插件目录之外的文件：{entry_path}")

    plugin_dir = os.path.dirname(entry_path)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)
        logger.debug(f"将插件目录加入 sys.path：{plugin_dir}")

    try:
        spec = importlib.util.spec_from_file_location(name, entry_path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
        logger.info(f"模块 {name} 加载成功")
    except Exception as e:
        logger.exception(f"插件 {name} 模块加载失败")
        raise RuntimeError(f"插件 {name} 加载失败: {e}")

    plugin_class = getattr(mod, "Plugin", None)
    if plugin_class and issubclass(plugin_class, PluginBase):
        plugin = plugin_class()
        loaded_plugins[name] = plugin
        logger.info(f"插件 {name} 实例化并缓存成功")
        return plugin

    logger.error(f"插件 {name} 未找到 Plugin 类或未继承 PluginBase")
    raise ValueError("未找到 Plugin 类或未继承 PluginBase")


def enable_plugin(entry_path, name):
    logger.info(f"启用插件 {name}")
    plugin = load_plugin(entry_path, name)
    plugin.activate()
    logger.info(f"插件 {name} 激活完成")


def disable_plugin(name):
    logger.info(f"尝试禁用插件 {name}")
    plugin = loaded_plugins.get(name)
    if plugin:
        plugin.deactivate()
        del loaded_plugins[name]
        logger.info(f"插件 {name} 已禁用并从缓存移除")
    else:
        logger.warning(f"插件 {name} 不存在或未加载")


def call_plugin_method(name, method_name, args: dict):
    logger.info(f"调用插件 {name} 的方法 {method_name}")
    plugin = loaded_plugins.get(name)
    if not plugin:
        logger.error(f"插件 {name} 未启用")
        raise ValueError(f"插件 {name} 未启用")
    if not hasattr(plugin, method_name):
        logger.error(f"插件 {name} 不包含方法 {method_name}")
        raise AttributeError(f"插件 {name} 没有方法 {method_name}")
    method = getattr(plugin, method_name)
    try:
        result = method(**args)
        logger.info(f"插件 {name}.{method_name} 执行成功")
        return result
    except Exception as e:
        logger.exception(f"插件方法执行失败：{e}")
        raise


def _plugin_runner(entry_path, method_name, args, output_queue):
    try:
        logger = setup_logger("plugin_runner")
        logger.info(f"子进程启动，执行 {entry_path} 中的 {method_name}")

        spec = importlib.util.spec_from_file_location("plugin", entry_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        plugin_class = getattr(mod, "Plugin", None)
        plugin = plugin_class()
        plugin.activate()

        result = getattr(plugin, method_name)(**args)
        output_queue.put({"result": result})
        logger.info(f"插件方法 {method_name} 执行成功")
    except Exception as e:
        logger.exception("子进程插件执行失败")
        output_queue.put({"error": str(e)})


def call_plugin_method_in_process(entry_path, method_name, args: dict, timeout=10):
    logger.info(f"使用进程执行插件方法：{entry_path}::{method_name}")
    q = Queue()
    p = Process(target=_plugin_runner, args=(entry_path, method_name, args, q))
    add_process(p)
    p.start()
    p.join(timeout)
    if p.is_alive():
        logger.warning(f"插件方法执行超时：{method_name}")
        p.terminate()
        raise TimeoutError("插件执行超时")

    output = q.get()
    if "error" in output:
        logger.error(f"插件执行出错：{output['error']}")
        raise RuntimeError(output["error"])

    logger.info(f"插件方法 {method_name} 执行完毕，返回结果")
    return output["result"]
