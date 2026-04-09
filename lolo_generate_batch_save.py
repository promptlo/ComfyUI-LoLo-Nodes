import datetime

class LoloGenerateBatchSave:
    """
    ComfyUI Custom Node: Lolo_generate_batch_save
    根据 index 值决定生成新文件名还是复用上次生成的文件名。
    """
    
    # 类变量：用于跨调用记忆最后生成的文件名（所有实例共享）
    _last_generated_filename = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "prefix": ("STRING", {"default": "image_", "multiline": False}),
                "index": ("INT", {"default": 0, "min": -9999, "max": 9999}),
            }
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("filename",)
    FUNCTION = "generate_filename"
    CATEGORY = "LoLo Nodes/Utils"

    def generate_filename(self, prefix, index):
        """
        核心逻辑：
        - index <= 0 : 生成新文件名，更新类变量
        - index > 0  : 返回类变量中记忆的文件名（若为空则自动生成一个）
        """
        if index <= 0:
            # 生成新文件名：prefix + 当前时间 (yyMMddHHmmss)
            timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
            new_filename = f"{prefix}{timestamp}"
            LoloGenerateBatchSave._last_generated_filename = new_filename
            print(f"[Lolo_generate_batch_save] 生成新文件名: {new_filename}")
            return (new_filename,)
        else:
            # 复用上次的文件名
            if LoloGenerateBatchSave._last_generated_filename is None:
                # 若从未生成过，则自动生成一个并提示
                timestamp = datetime.datetime.now().strftime("%y%m%d%H%M%S")
                fallback_filename = f"{prefix}{timestamp}"
                LoloGenerateBatchSave._last_generated_filename = fallback_filename
                print(f"[Lolo_generate_batch_save] 警告: 未找到记忆文件名，自动生成: {fallback_filename}")
            else:
                print(f"[Lolo_generate_batch_save] 复用上次文件名: {LoloGenerateBatchSave._last_generated_filename}")
            return (LoloGenerateBatchSave._last_generated_filename,)

