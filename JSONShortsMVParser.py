import json

class JSONShortsMVByIndex:
    """
    根据索引从JSON数组中提取单个片段的字段
    输入：JSON数组字符串 + 索引（从0开始）
    输出：该索引对应的 is_lip_sync, start_time, duration, first_frame_prompt, video_prompt
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "json_str": ("STRING", {
                    "multiline": True,
                    "default": "[]",
                    "tooltip": "符合格式的JSON数组字符串"
                }),
                "index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 9999,
                    "step": 1,
                    "tooltip": "要提取的片段索引（从0开始）"
                }),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "FLOAT", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("is_lip_sync", "start_time", "duration", "first_frame_prompt", "video_prompt")
    FUNCTION = "get_segment"
    CATEGORY = "utils/parser"
    
    def get_segment(self, json_str, index):
        # 解析JSON
        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON解析失败: {e}\n请确保输入是合法的JSON数组。")
        
        if not isinstance(data, list):
            raise ValueError("JSON根元素必须是数组。")
        
        if index < 0 or index >= len(data):
            raise ValueError(f"索引 {index} 超出范围（数组长度 {len(data)}）。")
        
        item = data[index]
        if not isinstance(item, dict):
            raise ValueError(f"索引 {index} 对应的元素不是对象。")
        
        # 提取字段，提供默认值
        is_lip_sync = item.get("is_lip_sync", False)
        start_time = float(item.get("start_time", 0.0))
        duration = float(item.get("duration", 0.0))
        first_frame_prompt = item.get("first_frame_prompt", "")
        video_prompt = item.get("video_prompt", "")
        
        return (is_lip_sync, start_time, duration, first_frame_prompt, video_prompt)


class JSONArrayLength:
    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {"json_str": ("STRING", {"multiline": True, "default": "[]"})}}
    RETURN_TYPES = ("INT",)
    FUNCTION = "get_length"
    CATEGORY = "utils/parser"
    def get_length(self, json_str):
        data = json.loads(json_str)
        return (len(data) if isinstance(data, list) else 0,)