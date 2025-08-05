"""
Author: SmileSion
Date: 2025-07-30
Description: 插件启动钩子。
"""
from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.db.models import PluginInfo, PluginStatus
from app.core.plugin.plugin_loader import enable_plugin
from app.utils.log_utils import setup_logger

logger = setup_logger("plugin_startup")

def register_startup_event(app):
    @app.on_event("startup")
    def load_enabled_plugins():
        db: Session = SessionLocal()
        logger.info("应用启动，开始加载已启用插件...")
        try:
            plugins = db.query(PluginInfo).filter(PluginInfo.status == PluginStatus.ENABLED).all()
            if not plugins:
                logger.info("未发现启用状态的插件，跳过加载")
            for p in plugins:
                try:
                    enable_plugin(p.entry_path, p.name)
                    logger.info(f"插件 {p.name} 启动加载成功")
                except Exception as e:
                    logger.exception(f"插件 {p.name} 启动加载失败: {e}")
        finally:
            db.close()
            logger.info("插件加载流程完成，数据库连接关闭")
