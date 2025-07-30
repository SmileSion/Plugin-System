"""
Author: SmileSion
Date: 2025-07-30
Description: 插件基本实现。
"""
class PluginBase:
    def activate(self):
        raise NotImplementedError

    def deactivate(self):
        raise NotImplementedError