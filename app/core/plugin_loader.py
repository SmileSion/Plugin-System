import importlib.util
import sys
import os
from plugin_base import PluginBase

loaded_plugins = {}  # name: instance of Plugin

# 插件根目录绝对路径
PLUGIN_ROOT = os.path.abspath("plugins")

def load_plugin(entry_path, name):
    entry_path = os.path.abspath(entry_path)
    # 限制插件入口必须在插件根目录下
    if not entry_path.startswith(PLUGIN_ROOT + os.sep):
        raise ValueError(f"禁止加载插件目录之外的文件：{entry_path}")

    plugin_dir = os.path.dirname(entry_path)
    if plugin_dir not in sys.path:
        sys.path.insert(0, plugin_dir)  # 仅添加插件目录到 sys.path，避免导入其他目录模块

    spec = importlib.util.spec_from_file_location(name, entry_path)
    mod = importlib.util.module_from_spec(spec)

    # 设置 __package__ 以支持相对导入
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
