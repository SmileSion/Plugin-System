import importlib.util
import sys
import os
from multiprocessing import Process, Queue
from plugin_base import PluginBase

PLUGIN_ROOT = os.path.abspath("plugins")

loaded_plugins = {}

def load_plugin(entry_path, name):
    entry_path = os.path.abspath(entry_path)
    if not entry_path.startswith(PLUGIN_ROOT + os.sep):
        raise ValueError(f"禁止加载插件目录之外的文件：{entry_path}")

    plugin_dir = os.path.dirname(entry_path)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)

    spec = importlib.util.spec_from_file_location(name, entry_path)
    mod = importlib.util.module_from_spec(spec)
    if "." in name:
        mod.__package__ = name.rpartition(".")[0]
    else:
        mod.__package__ = name

    sys.modules[name] = mod
    spec.loader.exec_module(mod)

    plugin_class = getattr(mod, "Plugin", None)
    if plugin_class and issubclass(plugin_class, PluginBase):
        plugin = plugin_class()
        loaded_plugins[name] = plugin
        return plugin
    raise ValueError("未找到 Plugin 类或未继承 PluginBase")

def enable_plugin(entry_path, name):
    plugin = load_plugin(entry_path, name)
    plugin.activate()

def disable_plugin(name):
    plugin = loaded_plugins.get(name)
    if plugin:
        plugin.deactivate()
        del loaded_plugins[name]

def call_plugin_method(name, method_name, args: dict):
    plugin = loaded_plugins.get(name)
    if not plugin:
        raise ValueError(f"插件 {name} 未启用")
    if not hasattr(plugin, method_name):
        raise AttributeError(f"插件 {name} 没有方法 {method_name}")
    method = getattr(plugin, method_name)
    return method(**args)

# 插件运行函数
def _plugin_runner(entry_path, method_name, args, output_queue):
    try:
        spec = importlib.util.spec_from_file_location("plugin", entry_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)

        plugin_class = getattr(mod, "Plugin", None)
        plugin = plugin_class()
        plugin.activate()
        result = getattr(plugin, method_name)(**args)
        output_queue.put({"result": result})
    except Exception as e:
        output_queue.put({"error": str(e)})

# 通过进程调用插件
def call_plugin_method_in_process(entry_path, method_name, args: dict, timeout=10):
    q = Queue()
    p = Process(target=_plugin_runner, args=(entry_path, method_name, args, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        raise TimeoutError("插件执行超时")

    output = q.get()
    if "error" in output:
        raise RuntimeError(output["error"])
    return output["result"]
