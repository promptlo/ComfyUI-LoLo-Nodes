import sys
import time

# 尝试导入 psutil，用于获取内存信息
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    print("[DebugMemoryNode] Warning: psutil not installed. Memory info will not be printed.")

class DebugMemoryNode:
    """
    调试节点：接收任意输入，直接输出，并在控制台打印当前系统内存使用情况。
    可用于定位内存增长发生的节点。
    """
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "anything": ("*",),  # 接收任意类型
            }
        }

    RETURN_TYPES = ("*",)
    FUNCTION = "pass_through"
    CATEGORY = "utils/debug"

    def pass_through(self, anything):
        # 打印内存信息
        if HAS_PSUTIL:
            mem = psutil.virtual_memory()
            print(f"\n[DebugMemoryNode] {time.strftime('%H:%M:%S')} RAM: {mem.used/1024**3:.2f} GB / {mem.total/1024**3:.2f} GB ({mem.percent:.1f}%)")
        else:
            print("[DebugMemoryNode] psutil not installed, cannot get memory info.")
        
        # 原样返回输入
        return (anything,)