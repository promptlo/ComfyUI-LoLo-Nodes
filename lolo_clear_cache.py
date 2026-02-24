"""
LoLolClearCache - 透明缓存清理节点
===================================

功能：
- 接收任意输入
- 输出相同的输入（透传）
- 执行后清理 ComfyUI 的缓存（显存、内存、未使用的模型等）
- 保持工作流其他节点不受影响

使用场景：
- 在工作流中插入此节点来自动清理缓存
- 可以添加到任何工作流的任意位置
"""

import torch
import gc
import time
import logging

# 尝试导入 ComfyUI 的 model_management，以便清理未使用的模型
try:
    import comfy.model_management
except ImportError:
    comfy.model_management = None

logger = logging.getLogger("LoLolClearCache")

class LoLolClearCache:
    """
    透明缓存清理节点（基础版）
    功能：透传输入，可清理 CUDA 缓存、执行垃圾回收、清理未使用的模型。
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "clean_cuda": ("BOOLEAN", {"default": True, "label": "清空 CUDA 缓存"}),
                "clean_memory": ("BOOLEAN", {"default": True, "label": "强制垃圾回收"}),
                "clean_unused_models": ("BOOLEAN", {"default": False, "label": "清理未使用的模型"}),
            },
            "optional": {
                "input_1": ("*",),
                "input_2": ("*",),
                "input_3": ("*",),
                "input_4": ("*",),
                "input_5": ("*",),
            }
        }

    RETURN_TYPES = ("*",) * 5
    RETURN_NAMES = ("output_1", "output_2", "output_3", "output_4", "output_5")
    FUNCTION = "process"
    CATEGORY = "LoLoNodes"
    DESCRIPTION = "透传节点，执行后可清理显存、内存和未使用的模型。接收最多5个任意输入，原样输出。"

    def clear_cache(self, clean_cuda, clean_memory, clean_unused_models):
        """执行缓存清理"""
        try:
            logger.info("[LoLolClearCache] 开始清理缓存...")

            if clean_cuda and torch.cuda.is_available():
                torch.cuda.empty_cache()
                logger.info("  - CUDA 缓存已清空")

            if clean_memory:
                # 多次垃圾回收可能更彻底
                for _ in range(3):
                    gc.collect()
                logger.info("  - 垃圾回收已执行")

            if clean_unused_models and comfy.model_management is not None:
                if hasattr(comfy.model_management, 'cleanup_models'):
                    comfy.model_management.cleanup_models()
                    logger.info("  - 未使用的模型已清理")
                else:
                    logger.warning("  - comfy.model_management.cleanup_models 不存在，跳过")

            logger.info("[LoLolClearCache] 缓存清理完成")
            return True
        except Exception as e:
            logger.error(f"[LoLolClearCache] 清理缓存时出错: {e}")
            return False

    def process(self, clean_cuda, clean_memory, clean_unused_models, **kwargs):
        """
        处理函数：
        - 接收可选输入（input_1 ~ input_5）
        - 执行清理
        - 返回与输入顺序对应的5个输出（未提供的输入对应 None）
        """
        inputs = [kwargs.get(f"input_{i}") for i in range(1, 6)]
        non_none_inputs = [f"input_{i}" for i, v in enumerate(inputs, start=1) if v is not None]
        logger.info(f"[LoLolClearCache] 收到输入: {', '.join(non_none_inputs) or '无'}")

        self.clear_cache(clean_cuda, clean_memory, clean_unused_models)

        return tuple(inputs)

    @classmethod
    def IS_CHANGED(cls, clean_cuda, clean_memory, clean_unused_models, **kwargs):
        """每次执行都视为变化，避免被缓存"""
        return float(time.time())


class LoLolClearCacheWithLabel(LoLolClearCache):
    """
    带标签的缓存清理节点
    增加一个标签参数，用于在日志中标识清理操作。
    """

    @classmethod
    def INPUT_TYPES(cls):
        parent_input = super().INPUT_TYPES()
        parent_input["required"] = {
            "label": ("STRING", {"default": "Cache Cleared", "multiline": False}),
            **parent_input["required"]
        }
        return parent_input

    RETURN_TYPES = ("*",) * 5
    RETURN_NAMES = ("output_1", "output_2", "output_3", "output_4", "output_5")
    FUNCTION = "process"
    CATEGORY = "LoLoNodes"
    DESCRIPTION = "透传节点，带自定义标签，执行后可清理显存、内存和未使用的模型。"

    def process(self, label, clean_cuda, clean_memory, clean_unused_models, **kwargs):
        inputs = [kwargs.get(f"input_{i}") for i in range(1, 6)]
        non_none_inputs = [f"input_{i}" for i, v in enumerate(inputs, start=1) if v is not None]
        logger.info(f"[LoLolClearCache] ({label}) 收到输入: {', '.join(non_none_inputs) or '无'}")

        self.clear_cache(clean_cuda, clean_memory, clean_unused_models)
        logger.info(f"[LoLolClearCache] ({label}) 清理完成")

        return tuple(inputs)