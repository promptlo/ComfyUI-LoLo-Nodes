import os
import subprocess
import re
import torch
import numpy as np
import folder_paths
from .lolo_ffmpeg_utils import get_ffmpeg_path

class LoloVideoSaveOutput:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),
                "filename_prefix": ("STRING", {"default": "video/ComfyUI"}),
                "output_last_frame_count": ("INT", {"default": 1, "min": 1, "max": 999999}),
                "fps": ("FLOAT", {"default": 30.0, "min": 1.0, "max": 120.0, "step": 1.0}),
                "format": (["mp4", "webm"], {"default": "mp4"}),
                "codec": (["auto", "libx264", "libx265", "libvpx", "h264_nvenc"], {"default": "auto"}),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("output_last_frames",)
    FUNCTION = "save_video"
    CATEGORY = "LoLo Nodes/video"
    OUTPUT_NODE = True

    def save_video(self, images, filename_prefix, output_last_frame_count, fps, format, codec):
        # 检查输入批次是否为空
        if images.shape[0] == 0:
            print("[LoloVideoSaveOutput] 警告：输入的 images 批次为空，跳过视频保存。")
            return (torch.zeros((0, images.shape[1], images.shape[2], images.shape[3])) if images.ndim == 4 else torch.zeros((0,0,0,0)),)

        batch_size, height, width, channels = images.shape
        if channels != 3:
            print(f"[LoloVideoSaveOutput] 警告：图像通道数为 {channels}，期望 3 (RGB)。")

        # 自动选择编解码器
        if codec == "auto":
            codec = "libx264" if format == "mp4" else "libvpx"

        # 使用 ComfyUI 标准方法获取输出目录和基础文件名（忽略计数器缓存）
        full_output_folder, base_filename, _, subfolder, _ = folder_paths.get_save_image_path(
            filename_prefix,
            folder_paths.get_output_directory(),
            width,
            height
        )

        # 手动生成下一个可用的文件名（避免缓存问题）
        output_file, next_counter = self._get_next_available_filename(full_output_folder, base_filename, format)
        print(f"[LoloVideoSaveOutput] 正在保存视频到: {output_file}")

        # 转换图像并编码
        try:
            images_np = (images.cpu().numpy() * 255).astype(np.uint8)
            self._encode_with_ffmpeg(images_np, output_file, fps, format, codec)
        except Exception as e:
            print(f"[LoloVideoSaveOutput] 视频编码失败: {e}")
            raise e

        # 提取尾部帧
        last_count = min(output_last_frame_count, batch_size)
        if last_count > 0:
            last_frames = images[-last_count:]
        else:
            last_frames = torch.zeros((0, height, width, channels))

        return (last_frames,)

    def _get_next_available_filename(self, directory, base_name, extension):
        """扫描目录，找到下一个可用的文件名（如 base_name_00001.extension）"""
        max_num = 0
        pattern = re.compile(rf"^{re.escape(base_name)}_(\d+)\.{re.escape(extension)}$")
        for f in os.listdir(directory):
            match = pattern.match(f)
            if match:
                num = int(match.group(1))
                if num > max_num:
                    max_num = num
        next_num = max_num + 1
        filename = f"{base_name}_{next_num:05d}.{extension}"
        return os.path.join(directory, filename), next_num

    def _encode_with_ffmpeg(self, images_np, output_file, fps, format, codec):
        ffmpeg_path = get_ffmpeg_path()
        batch_size, height, width, _ = images_np.shape

        cmd = [
            ffmpeg_path,
            "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{width}x{height}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "-",
        ]
        if format == "mp4":
            cmd += ["-c:v", codec, "-pix_fmt", "yuv420p"]
        else:  # webm
            cmd += ["-c:v", codec, "-pix_fmt", "yuv420p"]
        cmd.append(output_file)

        print(f"[LoloVideoSaveOutput] 执行 ffmpeg 命令: {' '.join(cmd)}")

        # 将所有图像数据合并为一个 bytes 对象
        raw_data = images_np.tobytes()
        
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        stdout, stderr = proc.communicate(input=raw_data)
        
        if proc.returncode != 0:
            raise RuntimeError(f"ffmpeg 编码失败 (返回码 {proc.returncode}):\n{stderr.decode('utf-8', errors='ignore')}")

        if not os.path.exists(output_file):
            raise RuntimeError(f"ffmpeg 执行成功但未生成输出文件: {output_file}")