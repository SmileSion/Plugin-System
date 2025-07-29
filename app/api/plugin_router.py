import os
import subprocess
from fastapi import APIRouter, Body, HTTPException, UploadFile, Depends
from app.utils.file_utils import extract_and_parse_manifest
from app.core.plugin_loader import call_plugin_method, enable_plugin, disable_plugin
from app.db.database import get_db
from app.db.models import PluginInfo, PluginStatus
from sqlalchemy.orm import Session
import shutil

router = APIRouter()

@router.post("/upload")
def upload_plugin(file: UploadFile, db: Session = Depends(get_db)):
    manifest = extract_and_parse_manifest(file)
    plugin = PluginInfo(
        name=manifest["name"],
        version=manifest.get("version"),
        description=manifest.get("description", ""),
        entry_path=manifest["entry_path"]
    )
    db.add(plugin)
    db.commit()
    requirements_path = os.path.join(os.path.dirname(manifest["entry_path"]), "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            subprocess.check_call(["pip", "install", "-r", requirements_path])
        except subprocess.CalledProcessError:
            return {"msg": "插件上传失败：requirements 安装出错"}

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