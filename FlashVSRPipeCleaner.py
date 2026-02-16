import torch
import gc
import time

# 尝试导入 psutil 以获取系统内存信息（可选）
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[FlashVSRPipeCleaner] psutil not installed, memory logging will be limited.")

class FlashVSRPipeCleaner:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pipe": ("PIPE",),   # 来自 Init 节点的 pipe
                "image": ("IMAGE",), # 来自 FlashVSRNodeAdv 的输出图像
            }
        }
    
    RETURN_TYPES = ("IMAGE",)
    FUNCTION = "clean"
    CATEGORY = "FlashVSR/utils"

    def log_memory(self, prefix=""):
        """打印当前系统内存和显存使用情况"""
        lines = []
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            lines.append(f"{prefix} RAM: {mem.used/1024**3:.2f} GB / {mem.total/1024**3:.2f} GB ({mem.percent:.1f}%)")
        if torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated() / 1024**3
            reserved = torch.cuda.memory_reserved() / 1024**3
            lines.append(f"{prefix} VRAM: allocated {allocated:.2f} GB, reserved {reserved:.2f} GB")
        if lines:
            print("\n".join(lines))
        else:
            print(f"{prefix} No memory info available.")

    def clean(self, pipe, image):
        print("\n=== [FlashVSRPipeCleaner] Start cleaning ===")
        self.log_memory("Before cleaning")

        # pipe 是一个元组 (_pipeline, force_offload)
        _pipeline = pipe[0]
        
        # 调用模型内部缓存清理方法
        if hasattr(_pipeline, 'dit') and hasattr(_pipeline.dit, 'LQ_proj_in'):
            print("  Clearing LQ_proj_in cache...")
            _pipeline.dit.LQ_proj_in.clear_cache()
        if hasattr(_pipeline, 'TCDecoder'):
            print("  Cleaning TCDecoder memory...")
            _pipeline.TCDecoder.clean_mem()
        
        # 强制 Python 垃圾回收
        print("  Running gc.collect()...")
        gc.collect()
        
        # 清空 PyTorch 的 CUDA 缓存
        if torch.cuda.is_available():
            print("  Emptying CUDA cache...")
            torch.cuda.empty_cache()
        
        self.log_memory("After cleaning ")
        print("=== [FlashVSRPipeCleaner] Clean completed ===\n")
        
        # 原样返回图像，不影响流程
        return (image,)