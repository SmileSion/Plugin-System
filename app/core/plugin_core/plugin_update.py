"""
Author: SmileSion
Date: 2025-07-30
Description: 插件更新模块。
"""
import os
import shutil
import subprocess
import tempfile
from sqlalchemy.orm import Session

from app.db.models import PluginInfo, PluginStatus
from app.utils.file_utils import extract_and_parse_manifest
from app.utils.log_utils import setup_logger

logger = setup_logger("plugin_update")

class UploadedFileWrapper:
    def __init__(self, file_path, filename):
        self.file = open(file_path, "rb")
        self.filename = filename
    def close(self):
        if not self.file.closed:
            self.file.close()
    def __del__(self):
        self.close()

def update_plugin(db: Session, plugin_name: str, uploaded_file):
    logger.info(f"开始更新插件：{plugin_name}")
    
    plugin = db.query(PluginInfo).filter_by(name=plugin_name).first()
    if not plugin:
        logger.error(f"插件 {plugin_name} 不存在，无法更新")
        raise ValueError(f"插件 '{plugin_name}' 不存在，无法更新")

    plugins_root = os.path.abspath("plugins")
    dest_folder = os.path.join(plugins_root, plugin_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, uploaded_file.filename)
        logger.debug(f"写入临时文件：{temp_path}")
        
        with open(temp_path, "wb") as f:
            uploaded_file.file.seek(0)
            f.write(uploaded_file.file.read())

        wrapper = UploadedFileWrapper(temp_path, uploaded_file.filename)
        try:
            manifest = extract_and_parse_manifest(wrapper, dest_folder=tmpdir)
            logger.debug(f"解析 manifest 成功：{manifest}")
        finally:
            wrapper.close()

        new_version = manifest.get("version")
        if new_version == plugin.version:
            logger.warning(f"插件 {plugin_name} 版本未变（{new_version}），更新被拒绝")
            raise ValueError(f"插件 '{plugin_name}' 版本相同 ({new_version})，不允许重复更新")

        from app.core.plugin_core.plugin_loader import disable_plugin
        if plugin.status == PluginStatus.ENABLED:
            logger.info(f"插件 {plugin_name} 已启用，先进行停用处理")
            disable_plugin(plugin_name)

        if os.path.exists(dest_folder):
            logger.info(f"删除旧插件目录：{dest_folder}")
            shutil.rmtree(dest_folder)

        logger.info(f"复制插件新版本至：{dest_folder}")
        shutil.copytree(os.path.join(tmpdir, plugin_name), dest_folder)

    requirements_path = os.path.join(dest_folder, "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            logger.info(f"检测到依赖文件，开始安装：{requirements_path}")
            subprocess.check_call(["pip", "install", "-r", requirements_path])
        except subprocess.CalledProcessError as e:
            logger.exception("插件依赖安装失败")
            raise RuntimeError(f"安装插件依赖失败: {e}")

    plugin.version = new_version
    plugin.description = manifest.get("description", plugin.description)
    plugin.entry_path = os.path.join(dest_folder, manifest.get("entry", "plugin.py"))
    plugin.status = PluginStatus.INSTALLED
    db.commit()

    logger.info(f"插件 {plugin_name} 更新成功为版本：{new_version}")
    return plugin
