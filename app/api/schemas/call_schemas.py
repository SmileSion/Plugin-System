# 定义调用的参数

from pydantic import BaseModel
from typing import Dict, Any

class PluginCallRequest(BaseModel):
    method: str
    args: Dict[str, Any] = {}
