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
    
    plugin_name = None

    if filename.endswith(".zip"):
        plugin_name = filename.replace(".zip", "")
        extract_path = os.path.join(dest_folder, plugin_name)
        logger.debug(f"解压 zip 到：{extract_path}")
        with zipfile.ZipFile(uploaded_file.file, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

    elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        plugin_name = filename.replace(".tar.gz", "").replace(".tgz", "")
        extract_path = os.path.join(dest_folder, plugin_name)
        logger.debug(f"解压 tar.gz 到：{extract_path}")
        with tarfile.open(fileobj=uploaded_file.file, mode="r:gz") as tar_ref:
            tar_ref.extractall(extract_path)

    else:
        logger.error("插件格式错误：只支持 zip 和 tar.gz 格式")
        raise ValueError("只支持 zip 和 tar.gz 格式的插件包")

    try:
        manifest_path = find_manifest_json(extract_path)
        logger.debug(f"manifest.json 路径：{manifest_path}")
    except FileNotFoundError as e:
        logger.exception("未找到 manifest.json")
        raise e

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    manifest["entry_path"] = os.path.join(extract_path, manifest.get("entry", "plugin.py"))
    manifest["name"] = plugin_name

    logger.info(f"插件 {plugin_name} manifest 解析成功")
    return manifest


def find_manifest_json(start_path):
    logger.debug(f"搜索 manifest.json 起始路径：{start_path}")
    for root, dirs, files in os.walk(start_path):
        if "manifest.json" in files:
            return os.path.join(root, "manifest.json")
    raise FileNotFoundError("manifest.json 未找到")
