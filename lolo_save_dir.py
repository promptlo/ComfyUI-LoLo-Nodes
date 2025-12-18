import os
import glob
import zipfile
import time
import urllib.parse
from server import PromptServer

class LoloSaveDirToZip:
    """
    将目录中的文件压缩为ZIP文件的节点。
    使用 hidden 的 UNIQUE_ID 与前端通信。
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dir": ("STRING", {
                    "default": "./input",
                    "multiline": False,
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                }),
                "suffix": ("STRING", {
                    "default": ".txt|.jpg|.png",
                    "multiline": False,
                }),
                "limit": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 10000,
                    "step": 1,
                }),
            },
            "optional": {
                "any_input": ("*", {}),
            },
            # ========== 核心修改：通过 hidden 字段获取系统生成的唯一节点ID ==========
            "hidden": {
                "unique_id": "UNIQUE_ID",  # 系统会自动注入此值
                # 也可同时获取其他信息，如 "prompt": "PROMPT"
            }
        }

    CATEGORY = "LoLo Nodes/Utils"
    RETURN_TYPES = ("STRING", "FLOAT")
    RETURN_NAMES = ("file_path", "file_size")
    FUNCTION = "save_to_zip"

    def save_to_zip(self, dir, seed, suffix=".txt|.jpg|.png", limit=-1, any_input=None, unique_id=None):
        """
        核心处理函数：筛选、压缩文件，并使用 unique_id 通知前端。
        """
        # --- 参数校验与转换 ---
        try:
            limit_int = int(limit) if limit is not None else -1
        except (ValueError, TypeError):
            print(f"[LoLo Nodes] 警告: limit参数值 '{limit}' 无效，将使用默认值 -1")
            limit_int = -1

        # 1. 检查目录
        if not os.path.isdir(dir):
            print(f"[LoLo Nodes] 后端错误: 目录不存在: {dir}")
            return ("", 0.0)

        # 2. 查找匹配文件
        suffix_list = [s.strip() for s in suffix.split("|") if s.strip()] or [".txt", ".jpg", ".png"]
        matched_files = set()
        for pattern in suffix_list:
            matched_files.update(glob.glob(os.path.join(dir, f"*{pattern}")))

        matched_files = sorted(matched_files)
        if limit_int > 0:
            matched_files = matched_files[:limit_int]

        if not matched_files:
            print(f"[LoLo Nodes] 后端错误: 在目录 {dir} 中未找到后缀为 {suffix} 的文件")
            return ("", 0.0)

        # 3. 准备输出
        output_dir = os.path.join(".", "output", "zip")
        os.makedirs(output_dir, exist_ok=True)
        timestamp = str(int(time.time()))
        zip_filename = f"{timestamp}.zip"
        zip_path = os.path.join(output_dir, zip_filename)

        # 4. 创建ZIP文件
        try:
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in matched_files:
                    zipf.write(file_path, os.path.basename(file_path))

            # 5. 计算文件信息
            file_size_bytes = os.path.getsize(zip_path)
            file_size_mb = file_size_bytes / (1024 * 1024)

            # 构建Web可访问路径
            output_root = os.path.abspath("./output")
            zip_abs_path = os.path.abspath(zip_path)
            if zip_abs_path.startswith(output_root):
                relative_path = os.path.relpath(zip_abs_path, output_root)
                subfolder = os.path.dirname(relative_path)
                filename = os.path.basename(relative_path)
                web_path = f"/view?filename={urllib.parse.quote(filename)}"
                if subfolder and subfolder != '.':
                    web_path += f"&subfolder={urllib.parse.quote(subfolder)}"
            else:
                web_path = zip_path
                print(f"[LoLo Nodes] 后端警告: 输出文件不在标准输出目录，Web路径可能无法直接访问。")

            # ========== 核心修改：使用系统提供的 unique_id 发送消息 ==========
            message_data = {
                "file_path": web_path,
                "file_size_mb": round(file_size_mb, 2),
                "node_id": unique_id,  # 使用系统注入的 unique_id
                "file_count": len(matched_files),
            }
            try:
                PromptServer.instance.send_sync("lolo.zip_ready", message_data)
                print(f"[LoLo Nodes] 后端成功: 已处理 {len(matched_files)} 个文件。节点ID: {unique_id}")
            except Exception as e:
                print(f"[LoLo Nodes] 后端警告: 文件压缩成功，但发送消息到前端时出错: {e}")
            # ==============================================================

            return (web_path, file_size_mb)

        except Exception as e:
            print(f"[LoLo Nodes] 后端错误: 创建ZIP文件过程中出错: {e}")
            return ("", 0.0)
        
    @classmethod
    def VALIDATE_INPUTS(cls, input_types):
    # 对于包含通配符 "*" 类型输入的节点，此方法必须返回 True
     return True