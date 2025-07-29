from fastapi import FastAPI
from app.api.plugin_router import router as plugin_router
from app.db.database import Base, engine

app = FastAPI(title="插件管理系统")
app.include_router(plugin_router, prefix="/plugins")
Base.metadata.create_all(bind=engine)