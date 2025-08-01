"""
Author: SmileSion
Date: 2025-07-30
Description: 插件处理模块。
"""
import zipfile
import tarfile
import os
import json

from app.utils.log_utils import setup_logger

logger = setup_logger("plugin_utils")


def extract_and_parse_manifest(uploaded_file, dest_folder="./plugins"):
    filename = uploaded_file.filename.lower()
    logger.info(f"开始解析插件包：{filename}")
    
    temp_plugin_name = filename.replace(".zip", "").replace(".tar.gz", "").replace(".tgz", "")
    temp_extract_path = os.path.join(dest_folder, temp_plugin_name)

    # 先清理可能残留目录
    if os.path.exists(temp_extract_path):
        import shutil
        shutil.rmtree(temp_extract_path)

    if filename.endswith(".zip"):
        logger.debug(f"解压 zip 到临时目录：{temp_extract_path}")
        with zipfile.ZipFile(uploaded_file.file, 'r') as zip_ref:
            zip_ref.extractall(temp_extract_path)

    elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        logger.debug(f"解压 tar.gz 到临时目录：{temp_extract_path}")
        with tarfile.open(fileobj=uploaded_file.file, mode="r:gz") as tar_ref:
            tar_ref.extractall(temp_extract_path)

    else:
        logger.error("插件格式错误：只支持 zip 和 tar.gz 格式")
        raise ValueError("只支持 zip 和 tar.gz 格式的插件包")

    try:
        manifest_path = find_manifest_json(temp_extract_path)
        logger.debug(f"manifest.json 路径：{manifest_path}")
    except FileNotFoundError as e:
        logger.exception("未找到 manifest.json")
        raise e

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    manifest_name = manifest.get("name")
    if not manifest_name:
        manifest_name = temp_plugin_name

    # 如果解压目录和 manifest_name 不同，重命名目录
    final_extract_path = os.path.join(dest_folder, manifest_name)
    if final_extract_path != temp_extract_path:
        if os.path.exists(final_extract_path):
            import shutil
            shutil.rmtree(final_extract_path)
        os.rename(temp_extract_path, final_extract_path)
        logger.info(f"将解压目录 {temp_extract_path} 重命名为 {final_extract_path}")

    manifest["name"] = manifest_name
    manifest["entry_path"] = os.path.join(final_extract_path, manifest.get("entry", "plugin.py"))

    logger.info(f"插件 {manifest_name} manifest 解析成功")
    return manifest



def find_manifest_json(start_path):
    logger.debug(f"搜索 manifest.json 起始路径：{start_path}")
    for root, dirs, files in os.walk(start_path):
        if "manifest.json" in files:
            return os.path.join(root, "manifest.json")
    raise FileNotFoundError("manifest.json 未找到")
