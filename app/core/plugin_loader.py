import importlib.util, sys
from plugin_base import PluginBase

loaded_plugins = {}  # name: instance of Plugin

def load_plugin(entry_path, name):
    spec = importlib.util.spec_from_file_location(name, entry_path)
    mod = importlib.util.module_from_spec(spec)
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
