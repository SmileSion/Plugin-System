from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import PluginInfo, PluginStatus
from app.core.plugin_loader import enable_plugin

def register_startup_event(app):
    @app.on_event("startup")
    def load_enabled_plugins():
        db: Session = SessionLocal()
        try:
            plugins = db.query(PluginInfo).filter(PluginInfo.status == PluginStatus.ENABLED).all()
            for p in plugins:
                try:
                    enable_plugin(p.entry_path, p.name)
                    print(f"插件 {p.name} 启动时加载成功")
                except Exception as e:
                    print(f"插件 {p.name} 启动时加载失败: {e}")
        finally:
            db.close()
