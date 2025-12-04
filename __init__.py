# ComfyUI-LoLo-Nodes/__init__.py
from .lolo_save_string import LoloSaveString2File
from .lolo_generate_filename import LoloGenerateFilename
from .lolo_load_string_from_dir import LoloLoadStringFromDir,LoloLoadStringFromFile

# 节点类映射
NODE_CLASS_MAPPINGS = {
    "LoloSaveString2File": LoloSaveString2File,
    "LoloGenerateFilename": LoloGenerateFilename,
    "LoloLoadStringFromDir": LoloLoadStringFromDir,
    "LoloLoadStringFromFile":LoloLoadStringFromFile
}

# 节点显示名称映射
NODE_DISPLAY_NAME_MAPPINGS = {
    "LoloSaveString2File": "LoLo Save String to File",
    "LoloGenerateFilename": "LoLo Generate Filename",
    "LoloLoadStringFromDir": "LoLo Load String From Dir",
    "LoloLoadStringFromFile": "LoLo Load String From File"
}

# 导出变量供ComfyUI主程序发现和加载
__all__ = ['NODE_CLASS_MAPPINGS', 'NODE_DISPLAY_NAME_MAPPINGS']