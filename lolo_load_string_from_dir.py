# ComfyUI-LoLo-Nodes/lolo_load_string_from_dir.py
import os
import glob
import time
import datetime

class LoloLoadStringFromDir:
    """
    从目录中加载字符串文件的节点。
    输入：目录路径、文件后缀、加载文件个数、文件索引。
    输出：从文件中读取的字符串内容。
    """
    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数和UI控件。
        """
        return {
            "required": {
                "dir": ("STRING", {
                    "default": "./input",
                    "multiline": False
                }),
                "suffix": ("STRING", {
                    "default": ".txt",
                    "multiline": False
                }),
                "load": ("INT", {
                    "default": 10,
                    "min": 0,
                    "max": 1000,
                    "step": 1,
                    "display": "number"
                }),
                "index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 1000,
                    "step": 1,
                    "display": "number"
                }),
                "refresh_seed": ("INT", {  # 新增参数
                "default": 0,
                "min": 0,
                "max": 0xffffffffffffffff
                }),
            },
            "optional": {}
        }

    CATEGORY = "LoLo Nodes/Utils"
    RETURN_TYPES = ("STRING", "STRING",)
    RETURN_NAMES = ("str", "file_name",)
    FUNCTION = "load_string"

    def load_string(self, dir, suffix=".txt", load=10, index=0, refresh_seed=0):
        """
        从指定目录加载字符串文件内容。
        
        参数:
            dir: 目录路径。
            suffix: 文件后缀，默认".txt"。
            load: 预加载的文件个数，>=0。
            index: 要读取的文件索引，>=0。
            
        返回:
            tuple: (文件内容字符串,)
        """
        # 1. 检查目录是否存在
        if not os.path.isdir(dir):
            print(f"[LoLo Nodes] 目录不存在: {dir}")
            return ("", "",)
        
        # 2. 确保suffix以点开头（如果不是）
        if suffix and not suffix.startswith('.'):
            suffix = '.' + suffix
        
        # 3. 构建文件匹配模式并查找文件
        # 使用glob查找匹配后缀的文件
        pattern = os.path.join(dir, f"*{suffix}")
        all_files = glob.glob(pattern)
        
        # 4. 按文件名排序以确保一致性
        all_files.sort()
        
        # 5. 根据load参数限制文件数量
        if load > 0:
            files = all_files[:load]
        else:
            files = all_files
        
        # 6. 检查文件数量是否足够
        if len(files) == 0:
            print(f"[LoLo Nodes] 在目录 {dir} 中未找到 {suffix} 文件")
            return ("","",)
        
        # 7. 检查索引是否在有效范围内
        if index >= len(files):
            print(f"[LoLo Nodes] 索引 {index} 超出范围 (0-{len(files)-1})")
            # 如果索引超出范围，返回最后一个文件的内容
            index = len(files) - 1
        
        # 8. 读取指定索引的文件内容
        target_file = files[index]

        # 获取不带路径的完整文件名（含后缀）
        filename_with_ext = os.path.basename(target_file)

        # 分离文件名和后缀
        filename_without_ext, file_ext = os.path.splitext(filename_with_ext)

        # 现在：
        # - filename_without_ext 是不包含路径和后缀的纯文件名
        # - file_ext 是后缀（例如 ".txt"、".json" 等，包含点号）

        try:
            with open(target_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"[LoLo Nodes] 从 {target_file} 加载了 {len(content)} 个字符")
            return (content,filename_without_ext,)
            
        except IOError as e:
            print(f"[LoLo Nodes] 读取文件时出错: {e}")
            return ("", "",)
        except UnicodeDecodeError:
            print(f"[LoLo Nodes] 文件编码错误，尝试使用其他编码")
            try:
                with open(target_file, 'r', encoding='gbk') as f:
                    content = f.read()
                return (content, filename_without_ext,)
            except:
                print(f"[LoLo Nodes] 无法读取文件: {target_file}")
                return ("", "",)


class LoloLoadStringFromFile:
    """
    从指定文件路径加载字符串内容的节点。
    输入：目录路径、文件名、后缀、随机种子（用于触发重新读取）。
    输出：文件中的字符串内容。
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dir": ("STRING", {
                    "default": "./input",
                    "multiline": False
                }),
                "filename": ("STRING", {
                    "default": "example",
                    "multiline": False
                }),
                "suffix": ("STRING", {
                    "default": ".txt",
                    "multiline": False
                }),
                "seed": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 0xffffffffffffffff,
                    "step": 1,
                    "display": "number"
                }),
            },
            "optional": {}
        }

    CATEGORY = "LoLo Nodes/Utils"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("str",)
    FUNCTION = "load_file"

    def load_file(self, dir, filename, suffix=".txt", seed=0):
        """
        从拼接的完整文件路径读取内容。
        参数seed用于触发重新读取，其值本身不参与逻辑。
        """
        # 1. 确保后缀以点开头
        if suffix and not suffix.startswith('.'):
            suffix = '.' + suffix

        # 2. 拼接完整文件路径
        full_filename = f"{filename}{suffix}"
        file_full_path = os.path.join(dir, full_filename)

        # 3. 检查文件是否存在
        if not os.path.isfile(file_full_path):
            print(f"[LoLo Nodes] 文件不存在: {file_full_path}")
            return ("",)

        # 4. 读取文件内容
        try:
            with open(file_full_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"[LoLo Nodes] 从 {file_full_path} 加载了 {len(content)} 个字符")
            return (content,)
        except IOError as e:
            print(f"[LoLo Nodes] 读取文件时出错 ({file_full_path}): {e}")
            return ("",)
        except UnicodeDecodeError:
            # 尝试GBK编码作为备选
            try:
                with open(file_full_path, 'r', encoding='gbk') as f:
                    content = f.read()
                return (content,)
            except Exception as e:
                print(f"[LoLo Nodes] 无法解码文件 ({file_full_path}): {e}")
                return ("",)