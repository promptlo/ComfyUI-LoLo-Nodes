# ComfyUI-LoLo-Nodes/lolo_save_string.py
import os
import comfy

class LoloSaveString2File:
    """
    将字符串保存到文件的节点（更新版）。
    输入：字符串、文件名、后缀、路径、模式、分隔符。
    输出：原始字符串和文件完整路径。
    """
    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数和UI控件。
        mode现在是枚举类型：all_in_one 或 everyone。
        """
        return {
            "required": {
                "str": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "dynamicPrompts": False
                }),
                "filename": ("STRING", {
                    "default": "saved_text",
                    "multiline": False
                }),
                "path": ("STRING", {
                    "default": "./output",
                    "multiline": False
                }),
                "mode": (["all_in_one", "everyone"], {
                    "default": "everyone"
                }),
            },
            "optional": {
                "ext": ("STRING", {
                    "default": "txt",
                    "multiline": False
                }),
                "separator": ("STRING", {
                    "default": "---",
                    "multiline": False
                }),
            }
        }

    CATEGORY = "LoLo Nodes/Utils"
    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("init_str", "file_full_path")
    FUNCTION = "save_string"

    def save_string(self, str, filename, path, mode="everyone", ext="txt", separator="---"):
        """
        核心业务逻辑：根据模式处理字符串并保存到文件。
        
        参数:
            str: 要保存的字符串。
            filename: 文件名（不带后缀）。
            path: 存储文件的绝对或相对路径。
            mode: 保存模式，"all_in_one"或"everyone"。
            ext: 文件后缀，默认为'txt'。
            separator: 在all_in_one模式中使用的分隔符。
            
        返回:
            tuple: (原始字符串, 生成的完整文件路径)
        """
        # 1. 处理文件路径：拼接路径、文件名和后缀
        if ext and not ext.startswith('.'):
            ext = '.' + ext
        elif not ext:
            ext = '.txt'
            
        full_filename = f"{filename}{ext}"
        file_full_path = os.path.join(path, full_filename)
        
        # 2. 确保目标目录存在
        os.makedirs(os.path.dirname(file_full_path), exist_ok=True)
        
        # 3. 根据mode标志执行不同的文件操作
        try:
            if mode == "all_in_one" and os.path.exists(file_full_path):
                # all_in_one模式：追加内容，使用指定的分隔符
                with open(file_full_path, 'a', encoding='utf-8') as f:
                    f.write(f"\n{separator}\n{str}")
            else:
                # everyone模式：总是创建新文件（覆盖旧文件）
                with open(file_full_path, 'w', encoding='utf-8') as f:
                    f.write(str)
                    
        except IOError as e:
            print(f"[LoLo Nodes] 写入文件时出错: {e}")
            return (str, file_full_path)
        
        # 4. 返回结果
        return (str, file_full_path)