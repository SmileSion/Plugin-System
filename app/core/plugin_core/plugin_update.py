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
    plugin = db.query(PluginInfo).filter_by(name=plugin_name).first()
    if not plugin:
        raise ValueError(f"插件 '{plugin_name}' 不存在，无法更新")

    # 插件根目录
    plugins_root = os.path.abspath("plugins")
    dest_folder = os.path.join(plugins_root, plugin_name)

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_path = os.path.join(tmpdir, uploaded_file.filename)
        with open(temp_path, "wb") as f:
            uploaded_file.file.seek(0)
            f.write(uploaded_file.file.read())

        wrapper = UploadedFileWrapper(temp_path, uploaded_file.filename)
        try:
            # 解压到临时目录，解析manifest
            manifest = extract_and_parse_manifest(wrapper, dest_folder=tmpdir)
        finally:
            wrapper.close()

        new_version = manifest.get("version")
        if new_version == plugin.version:
            raise ValueError(f"插件 '{plugin_name}' 版本相同 ({new_version})，不允许重复更新")

        from app.core.plugin_core.plugin_loader import disable_plugin
        if plugin.status == PluginStatus.ENABLED:
            disable_plugin(plugin_name)

        # 删除旧插件目录（plugins/插件名）
        if os.path.exists(dest_folder):
            shutil.rmtree(dest_folder)

        # 将解压后的插件从临时目录复制到 plugins 目录
        shutil.copytree(os.path.join(tmpdir, plugin_name), dest_folder)

    # 安装依赖
    requirements_path = os.path.join(dest_folder, "requirements.txt")
    if os.path.exists(requirements_path):
        try:
            subprocess.check_call(["pip", "install", "-r", requirements_path])
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"安装插件依赖失败: {e}")

    # 更新数据库插件信息，entry_path 指向 plugins 目录下的文件绝对路径
    plugin.version = new_version
    plugin.description = manifest.get("description", plugin.description)
    plugin.entry_path = os.path.join(dest_folder, manifest.get("entry", "plugin.py"))
    plugin.status = PluginStatus.INSTALLED
    db.commit()

    return plugin
