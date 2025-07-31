"""
Author: SmileSion
Date: 2025-07-30
Description: 接口路由注册模块。
"""
import os
import shutil
import subprocess
import inspect

from fastapi import APIRouter, Body, HTTPException, UploadFile, Depends, Query
from sqlalchemy.orm import Session

from app.utils.file_utils import extract_and_parse_manifest
from app.utils.log_utils import setup_logger
from app.core.plugin_core.plugin_loader import (
    call_plugin_method_in_process,
    enable_plugin,
    disable_plugin,
    loaded_plugins,
)
from app.core.plugin_core.plugin_update import update_plugin
from app.db.database import get_db
from app.db.models import PluginInfo, PluginStatus
from .schemas.call_schemas import PluginCallRequest

router = APIRouter()
logger = setup_logger("plugin_router")

MAX_PLUGIN_SIZE = 3 * 1024 * 1024  # 3MB
CHUNK_SIZE = 1024 * 1024  # 每次最多读取 1MB

@router.post("/upload")
def upload_plugin(file: UploadFile, db: Session = Depends(get_db)):
    logger.info(f"收到插件上传请求：{file.filename}")
    temp_path = f"/tmp/{file.filename}"
    save_upload_file_limited(file, temp_path)

    with open(temp_path, "rb") as f:
        file.file = f
        manifest = extract_and_parse_manifest(file)

    existing_plugin = db.query(PluginInfo).filter_by(name=manifest["name"]).first()
    if existing_plugin:
        os.remove(temp_path)
        logger.warning(f"上传失败，插件已存在：{manifest['name']}")
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
            logger.error(f"插件 {plugin.name} 安装 requirements 失败")
            raise HTTPException(status_code=500, detail="插件上传失败：requirements 安装出错")

    os.remove(temp_path)
    logger.info(f"插件上传成功：{plugin.name}")
    return {"msg": "上传成功", "plugin": plugin.name}

@router.post("/enable/{name}")
def enable(name: str, db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    
    if not plugin:
        logger.warning(f"启用失败，插件不存在：{name}")
        raise HTTPException(status_code=404, detail="插件不存在")
    
    enable_plugin(plugin.entry_path, name)
    plugin.status = PluginStatus.ENABLED
    db.commit()
    logger.info(f"插件已启用：{name}")
    return {"msg": f"插件 {name} 已启用"}

@router.post("/disable/{name}")
def disable(name: str, db: Session = Depends(get_db)):
    disable_plugin(name)
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    plugin.status = PluginStatus.DISABLED
    db.commit()
    logger.info(f"插件已停用：{name}")
    return {"msg": f"插件 {name} 已停用"}

@router.get("/list")
def list_plugins(db: Session = Depends(get_db)):
    logger.info("获取插件列表")
    return db.query(PluginInfo).all()

@router.post("/call/{name}")
def call(name: str,
         payload: PluginCallRequest = Body(...),
         db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    if not plugin or plugin.status != PluginStatus.ENABLED:
        logger.warning(f"插件调用失败，未启用或不存在：{name}")
        raise HTTPException(status_code=400, detail="插件未启用或不存在")

    method = payload.method
    args = payload.args
    logger.info(f"调用插件 {name} 方法 {method}，参数：{args}")

    try:
        result = call_plugin_method_in_process(plugin.entry_path, method, args)
        logger.info(f"插件调用成功：{name}.{method} 返回 {result}")
        return {"result": result}
    except Exception as e:
        logger.exception(f"插件调用出错：{name}.{method}")
        raise HTTPException(status_code=500, detail=str(e))
    
@router.delete("/uninstall/{name}")
def uninstall_plugin(name: str, db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    if not plugin:
        logger.warning(f"卸载失败，插件不存在：{name}")
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
    logger.info(f"插件已卸载并删除：{name}")
    return {"msg": f"插件 {name} 已卸载并删除"}

@router.get("/methods/{name}")
def get_plugin_methods(name: str):
    plugin = loaded_plugins.get(name)
    if not plugin:
        logger.warning(f"获取方法失败，插件未启用或不存在：{name}")
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
    logger.info(f"插件方法获取成功：{name}")
    return {"plugin": name, "methods": methods_info}

@router.get("/status/{name}")
def check_plugin_status(name: str, db: Session = Depends(get_db)):
    plugin = db.query(PluginInfo).filter_by(name=name).first()
    if not plugin:
        logger.warning(f"插件状态查询失败，不存在：{name}")
        raise HTTPException(status_code=404, detail="插件不存在")

    # 是否已加载（启用）
    is_enabled = name in loaded_plugins
    logger.info(f"插件状态查询：{name}，启用状态：{is_enabled}")
    return {
        "name": plugin.name,
        "version": plugin.version,
        "description": plugin.description,
        "status_db": plugin.status.name,  # 数据库中状态（比如 INSTALLED, ENABLED, DISABLED）
        "is_loaded_in_memory": is_enabled  # 是否内存中已启用
    }

@router.post("/update/{name}")
def update(name: str, file: UploadFile, db: Session = Depends(get_db)):
    logger.info(f"收到插件更新请求：{name}")
    temp_path = f"/tmp/update_{file.filename}"
    save_upload_file_limited(file, temp_path)
    try:
        plugin = update_plugin(db, name, file)
        logger.info(f"插件更新成功：{name} -> 版本 {plugin.version}")
        return {"msg": f"插件 {name} 更新成功", "version": plugin.version}
    except ValueError as ve:
        logger.warning(f"插件更新失败：{name}，原因：{ve}")
        # 版本相同或插件不存在等业务错误，返回 400 或自定义状态码
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.exception(f"插件更新异常：{name}")
        # 其他未处理异常，返回 500
        raise HTTPException(status_code=500, detail=str(e))



# 限制上传大小函数
def save_upload_file_limited(file: UploadFile, dest_path: str):
    total_size = 0
    with open(dest_path, "wb") as out_file:
        while chunk := file.file.read(CHUNK_SIZE):
            total_size += len(chunk)
            if total_size > MAX_PLUGIN_SIZE:
                out_file.close()
                os.remove(dest_path)
                size_mb = MAX_PLUGIN_SIZE / (1024 * 1024)
                logger.warning(f"上传失败，插件文件过大：{file.filename} 大小超过 {size_mb:.2f} MB")
                raise HTTPException(status_code=413, detail=f"文件过大，不能超过 {size_mb:.2f} MB")
            out_file.write(chunk)