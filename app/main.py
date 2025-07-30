"""
Author: SmileSion
Date: 2025-07-30
Description: 主函数，启动入口。
"""
from fastapi import FastAPI
from app.api.plugin_router import router as plugin_router
from app.core.startup_hooks import register_startup_event
from app.db.database import Base, engine

app = FastAPI(title="插件管理系统")
app.include_router(plugin_router, prefix="/plugins")
Base.metadata.create_all(bind=engine)
register_startup_event(app)