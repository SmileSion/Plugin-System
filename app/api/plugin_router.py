import os
import subprocess
from fastapi import APIRouter, Body, HTTPException, UploadFile, Depends, Query
from app.utils.file_utils import extract_and_parse_manifest
from app.core.plugin_loader import call_plugin_method, enable_plugin, disable_plugin, loaded_plugins
from app.db.database import get_db
from app.db.models import PluginInfo, PluginStatus
from sqlalchemy.orm import Session
import shutil
import inspect

router = APIRouter()

@router.post("/upload")
def upload_plugin(file: UploadFile, db: Session = Depends(get_db)):
    manifest = extract_and_parse_manifest(file)
    existing_plugin = db.query(PluginInfo).filter_by(name=manifest["name"]).first()
    if existing_plugin:
        raise HTTPException(status_code=400, detail=f"插件名 '{manifest['name']}' 已存在，请更换名称")

    plugin = PluginInfo(
        name=manifest["name"],
        version=manifest.get("version"),
        description=manifest.get("description", ""),
        entry_path=manifest["entry_path"],
        status=PluginStatus.INSTALLED  
    )
    db.add(plugin)
    db.commit()

    requirements_path = os.path.join(os.path.dirname(manifest["entry_path"]), "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            subprocess.check_call(["pip", "install", "-r", requirements_path])
        except subprocess.CalledProcessError:
            raise HTTPException(status_code=500, detail="插件上传失败：requirements 安装出错")

    return {"msg": "上传成功", "plugin": plugin.name}

@router.post("/enable/{name}")
def enable(name: str, db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    enable_plugin(plugin.entry_path, name)
    plugin.status = PluginStatus.ENABLED
    db.commit()
    return {"msg": f"插件 {name} 已启用"}

@router.post("/disable/{name}")
def disable(name: str, db: Session = Depends(get_db)):
    disable_plugin(name)
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    plugin.status = PluginStatus.DISABLED
    db.commit()
    return {"msg": f"插件 {name} 已停用"}

@router.get("/list")
def list_plugins(db: Session = Depends(get_db)):
    return db.query(PluginInfo).all()

@router.post("/call/{name}")
def call(name: str, 
         payload: dict = Body(...),
         db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    if not plugin or plugin.status != PluginStatus.ENABLED:
        raise HTTPException(status_code=400, detail="插件未启用或不存在")

    method = payload.get("method")
    args = payload.get("args", {})

    try:
        result = call_plugin_method(name, method, args)
        return {"result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/uninstall/{name}")
def uninstall_plugin(name: str, db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="插件不存在")

    # 如果插件启用中，先停用
    if plugin.status == PluginStatus.ENABLED:
        disable_plugin(name)

    # 删除插件记录
    db.delete(plugin)
    db.commit()

    # 删除插件文件夹（假设插件路径格式固定）
    plugin_folder = os.path.dirname(plugin.entry_path)
    if os.path.exists(plugin_folder):
        shutil.rmtree(plugin_folder)

    return {"msg": f"插件 {name} 已卸载并删除"}

@router.get("/methods/{name}")
def get_plugin_methods(name: str):
    plugin = loaded_plugins.get(name)
    if not plugin:
        raise HTTPException(status_code=400, detail="插件未启用或不存在")

    methods_info = {}
    for attr_name in dir(plugin):
        if attr_name.startswith("_"):
            continue  # 跳过私有和特殊方法
        attr = getattr(plugin, attr_name)
        if callable(attr):
            sig = inspect.signature(attr)
            # 过滤掉 self 参数，只展示外部调用需要传的参数
            params = [p.name for p in sig.parameters.values() if p.name != "self"]
            methods_info[attr_name] = params

    return {"plugin": name, "methods": methods_info}

@router.get("/status/{name}")
def check_plugin_status(name: str, db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    if not plugin:
        raise HTTPException(status_code=404, detail="插件不存在")

    # 是否已加载（启用）
    is_enabled = name in loaded_plugins

    return {
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "status_db": plugin.status.name,  # 数据库中状态（比如 INSTALLED, ENABLED, DISABLED）
        "is_loaded_in_memory": is_enabled  # 是否内存中已启用
    }
