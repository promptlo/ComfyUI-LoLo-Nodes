# ComfyUI-LoLo-Nodes/lolo_generate_filename.py
import hashlib
import datetime

class LoloGenerateFilename:
    """
    生成唯一文件名的节点（更新版）。
    输入：前缀。
    输出：生成的文件名。
    """
    @classmethod
    def INPUT_TYPES(cls):
        """
        定义节点的输入参数和UI控件。
        """
        return {
            "required": {
                "prefix": ("STRING", {
                    "default": "prompts_",
                    "multiline": False
                }),
                "seed": ("INT", {
                    "default": 0
                }),
            },
            "optional": {}
        }

    CATEGORY = "LoLo Nodes/Utils"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "generate_filename"

    def generate_filename(self, prefix, seed):
        """
        根据前缀和当前时间生成文件名。
        
        参数:
            prefix: 文件前缀名。
            
        返回:
            tuple: (生成的文件名,)
        """
        # 1. 获取当前时间
        now = datetime.datetime.now()
        
        # 2. 按照 yyMMDDmmss 格式格式化时间
        # yy: 两位年份，MM: 两位月份，DD: 两位日期，mm: 两位分钟，ss: 两位秒钟
        # 注意：这里的 "mm" 是分钟，不是月份（月份用 "MM" 表示）
        # 格式说明: %y=两位年份，%m=两位月份，%d=两位日期，%M=两位分钟，%S=两位秒钟
        time_str = now.strftime("%y%m%d%M%S")
        
        # 3. 组合前缀和时间部分
        filename = f"{prefix}{time_str}"
        
        return (filename,)