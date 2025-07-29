class PluginBase:
    def activate(self):
        raise NotImplementedError

    def deactivate(self):
        raise NotImplementedError