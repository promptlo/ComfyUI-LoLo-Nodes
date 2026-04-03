import os

class LoloGetFileCount:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dir": ("STRING", {"default": "", "multiline": False}),
                "suffix": ("STRING", {"default": "*", "multiline": False}),
            },
        }

    RETURN_TYPES = ("INT",)
    RETURN_NAMES = ("count",)
    FUNCTION = "get_count"
    CATEGORY = "LoLo Nodes/utils"

    def get_count(self, dir, suffix):
        # 去除首尾空白字符（防止其他节点传入带换行或空格的字符串）
        dir = dir.strip()
        if not dir:
            raise ValueError("目录路径不能为空")

        # 支持相对路径：如果路径不是绝对路径，则基于 ComfyUI 根目录拼接
        if not os.path.isabs(dir):
            comfy_root = os.getcwd()  # ComfyUI 启动目录（根目录）
            dir = os.path.join(comfy_root, dir)
            print(f"[LoloGetFileCount] 解析相对路径为: {dir}")

        if not os.path.isdir(dir):
            raise NotADirectoryError(f"目录不存在: {dir}")

        if suffix == "*":
            files = [f for f in os.listdir(dir) if os.path.isfile(os.path.join(dir, f))]
        else:
            suffixes = [s.strip().lower() for s in suffix.split('|')]
            files = []
            for f in os.listdir(dir):
                if os.path.isfile(os.path.join(dir, f)):
                    ext = os.path.splitext(f)[1].lower()
                    if ext in suffixes:
                        files.append(f)

        count = len(files)
        print(f"[LoloGetFileCount] 目录 {dir} 中共有 {count} 个匹配的文件")
        return (count,)