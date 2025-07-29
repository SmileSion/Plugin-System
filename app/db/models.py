import enum
from sqlalchemy import Column, Enum, String, Integer, DateTime
from datetime import datetime
from .database import Base

class PluginStatus(enum.Enum):
    INSTALLED = "installed"
    ENABLED = "enabled"
    DISABLED = "disabled"
    UNINSTALLED = "uninstalled"

class PluginInfo(Base):
    __tablename__ = "plugins"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True)
    version = Column(String)
    description = Column(String)
    entry_path = Column(String)
    status = Column(Enum(PluginStatus), default=PluginStatus.INSTALLED)
    install_time = Column(DateTime, default=datetime.utcnow)
