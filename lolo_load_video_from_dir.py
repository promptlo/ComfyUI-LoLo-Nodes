import os
import cv2
import torch
import numpy as np
import folder_paths

class LoloLoadVideoFromDir:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_dir": ("STRING", {"default": "", "multiline": False}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
            },
        }

    RETURN_TYPES = ("IMAGE", "STRING")
    RETURN_NAMES = ("images", "filename")
    FUNCTION = "load_video"
    CATEGORY = "LoLo Nodes/video"

    def load_video(self, video_dir, index):
        # 去除首尾空白
        video_dir = video_dir.strip()
        if not video_dir:
            raise ValueError("视频目录路径不能为空")

        # 支持相对路径：基于 ComfyUI 根目录
        if not os.path.isabs(video_dir):
            comfy_root = os.getcwd()
            video_dir = os.path.join(comfy_root, video_dir)
            print(f"[LoloLoadVideoFromDir] 解析相对路径为: {video_dir}")

        if not os.path.isdir(video_dir):
            raise NotADirectoryError(f"视频目录不存在: {video_dir}")

        # 支持的视频扩展名（与 VideoHelperSuite 保持一致）
        video_exts = ('.mp4', '.webm', '.avi', '.mov', '.mkv', '.gif')
        files = [f for f in os.listdir(video_dir) if f.lower().endswith(video_exts)]
        files.sort()
        if not files:
            raise RuntimeError(f"目录中没有找到支持的视频文件: {video_dir}")

        if index < 0 or index >= len(files):
            raise IndexError(f"索引 {index} 超出范围 (0-{len(files)-1})")

        video_path = os.path.join(video_dir, files[index])
        base_name = os.path.splitext(files[index])[0]  # 不含后缀的文件名
        print(f"[LoloLoadVideoFromDir] 加载视频: {video_path}")

        # 使用 OpenCV 加载视频帧
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"无法打开视频文件: {video_path}")

        frames = []
        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                # OpenCV 读取的是 BGR，转换为 RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                # 归一化到 [0,1] 并转为 float32
                frame_tensor = torch.from_numpy(frame_rgb.astype(np.float32) / 255.0)
                frames.append(frame_tensor)
        finally:
            cap.release()

        if not frames:
            raise RuntimeError(f"视频文件中没有读取到任何帧: {video_path}")

        # 堆叠为 [N, H, W, C]
        images = torch.stack(frames, dim=0)
        print(f"[LoloLoadVideoFromDir] 成功加载 {len(images)} 帧，尺寸 {images.shape[1]}x{images.shape[2]}")

        return (images, base_name)