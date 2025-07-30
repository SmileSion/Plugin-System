"""
Author: SmileSion
Date: 2025-07-30
Description: 插件处理模块。
"""
import zipfile
import tarfile
import os
import json

def extract_and_parse_manifest(uploaded_file, dest_folder="./plugins"):
    filename = uploaded_file.filename.lower()
    if filename.endswith(".zip"):
        with zipfile.ZipFile(uploaded_file.file, 'r') as zip_ref:
            plugin_name = filename.replace(".zip", "")
            extract_path = os.path.join(dest_folder, plugin_name)
            zip_ref.extractall(extract_path)
    elif filename.endswith(".tar.gz") or filename.endswith(".tgz"):
        with tarfile.open(fileobj=uploaded_file.file, mode="r:gz") as tar_ref:
            plugin_name = filename.replace(".tar.gz", "").replace(".tgz", "")
            extract_path = os.path.join(dest_folder, plugin_name)
            tar_ref.extractall(extract_path)
    else:
        raise ValueError("只支持 zip 和 tar.gz 格式的插件包")

    manifest_path = find_manifest_json(extract_path)
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    manifest["entry_path"] = os.path.join(extract_path, manifest.get("entry", "plugin.py"))
    manifest["name"] = plugin_name
    return manifest

def find_manifest_json(start_path):
    for root, dirs, files in os.walk(start_path):
        if "manifest.json" in files:
            return os.path.join(root, "manifest.json")
    raise FileNotFoundError("manifest.json 未找到")
