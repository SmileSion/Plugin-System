"""
Author: SmileSion
Date: 2025-07-30
Description: 插件基本实现。
"""
from abc import ABC, abstractmethod

class PluginBase(ABC):
    @abstractmethod
    def activate(self):
        """插件加载后执行的初始化逻辑"""
        pass

    @abstractmethod
    def deactivate(self):
        """插件卸载前执行的清理逻辑"""
        pass
    
    def health_check(self):
        """用于检测插件运行状态"""
        return True

    def get_metadata(self):
        """返回插件信息，如版本、作者等"""
        return {}