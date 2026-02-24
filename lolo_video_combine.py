import os
import subprocess
import tempfile
import re
import numpy as np
import torch
import folder_paths
from .lolo_ffmpeg_utils import get_ffmpeg_path

class LoloVideoCombine:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_dir": ("STRING", {"default": "segments", "multiline": False}),
                "audio": ("AUDIO",),
                "filename_prefix": ("STRING", {"default": "combined_video"}),
            },
            "optional": {
                "any": ("*",),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result_path",)
    FUNCTION = "combine"
    CATEGORY = "LoLo Nodes/video"

    def __init__(self):
        self.ffmpeg_path = None
        self._init_ffmpeg()

    def _init_ffmpeg(self):
        try:
            self.ffmpeg_path = get_ffmpeg_path()
            print(f"[LoloVideoCombine] ffmpeg: {self.ffmpeg_path}")
        except RuntimeError as e:
            raise RuntimeError(f"节点初始化失败: {e}")

    def combine(self, video_dir, audio, filename_prefix, any=None):
        # ---------- 智能路径解析 ----------
        if not os.path.isabs(video_dir):
            video_dir = os.path.join(folder_paths.get_output_directory(), video_dir)
            print(f"[LoloVideoCombine] 解析相对路径为: {video_dir}")

        if not os.path.isdir(video_dir):
            raise NotADirectoryError(f"目录不存在: {video_dir}")

        # ---------- 获取视频文件列表 ----------
        files = [f for f in os.listdir(video_dir) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]
        files.sort()
        if not files:
            raise RuntimeError(f"目录中没有视频文件: {video_dir}")

        # ---------- 自动生成输出路径 ----------
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        counter = 1
        while True:
            out_path = os.path.join(output_dir, f"{filename_prefix}_{counter:05d}.mp4")
            if not os.path.exists(out_path):
                break
            counter += 1

        # ---------- 临时文件变量预定义 ----------
        list_file = None
        temp_video = None
        audio_file = None

        try:
            # ---------- 创建 concat 列表文件（智能引号 + 正斜杠）----------
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                list_file = f.name
                for file in files:
                    full_path = os.path.join(video_dir, file)
                    full_path = full_path.replace('\\', '/')
                    if ' ' in full_path:
                        f.write(f'file "{full_path}"\n')
                    else:
                        f.write(f'file {full_path}\n')

            # ---------- 临时无音频视频 ----------
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                temp_video = tmp.name

            # ---------- 尝试快速拼接（流复制）----------
            try:
                print(f"[LoloVideoCombine] 尝试快速拼接（流复制）...")
                subprocess.run([self.ffmpeg_path, "-f", "concat", "-safe", "0",
                               "-i", list_file, "-c", "copy", "-y", temp_video],
                               check=True, capture_output=True)
                print(f"[LoloVideoCombine] 流复制成功")
            except subprocess.CalledProcessError as e:
                print(f"[LoloVideoCombine] 流复制失败，错误信息:")
                print(e.stderr.decode('utf-8', errors='ignore'))
                print(f"[LoloVideoCombine] 降级为重新编码（兼容模式）...")

                try:
                    subprocess.run([self.ffmpeg_path, "-f", "concat", "-safe", "0",
                                   "-i", list_file,
                                   "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                                   "-pix_fmt", "yuv420p",
                                   "-c:a", "aac", "-b:a", "192k",
                                   "-y", temp_video],
                                   check=True, capture_output=True)
                    print(f"[LoloVideoCombine] 重新编码成功")
                except subprocess.CalledProcessError as e2:
                    error_msg = f"[LoloVideoCombine] 重新编码失败！\n"
                    error_msg += f"ffmpeg 命令: {' '.join(e2.cmd)}\n"
                    error_msg += f"错误输出:\n{e2.stderr.decode('utf-8', errors='ignore')}\n"
                    error_msg += "请检查视频片段是否损坏，或尝试手动运行上述命令诊断。"
                    print(error_msg)
                    raise RuntimeError(error_msg)

            # ---------- 处理音频（使用 ffmpeg 直接编码为 wav）----------
            waveform = audio["waveform"]
            sample_rate = audio["sample_rate"]

            # 确保波形为 [channels, samples] 2D 格式，并转换为 float32 NumPy 数组
            if waveform.dim() == 3:
                waveform = waveform.squeeze(0)               # [1, C, S] → [C, S]
            elif waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)             # [S] → [1, S]

            samples = waveform.shape[1]
            channels = waveform.shape[0]
            # 转换为 [samples, channels] 并转为 float32 bytes
            audio_data = waveform.t().contiguous().numpy().astype(np.float32)

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
                audio_file = tmp_audio.name

            ffmpeg_audio_cmd = [
                self.ffmpeg_path,
                "-y",
                "-f", "f32le",
                "-ar", str(sample_rate),
                "-ac", str(channels),
                "-i", "-",
                "-c:a", "pcm_s16le",
                "-f", "wav",
                audio_file
            ]
            proc_audio = subprocess.Popen(ffmpeg_audio_cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
            proc_audio.stdin.write(audio_data.tobytes())
            proc_audio.stdin.close()
            proc_audio.wait()
            if proc_audio.returncode != 0:
                stderr = proc_audio.stderr.read().decode('utf-8', errors='ignore')
                raise RuntimeError(f"ffmpeg 音频编码失败 (返回码 {proc_audio.returncode}):\n{stderr}")

            # ---------- 合并音频到最终视频 ----------
            subprocess.run([self.ffmpeg_path, "-i", temp_video, "-i", audio_file,
                           "-c:v", "copy", "-c:a", "aac",
                           "-map", "0:v:0", "-map", "1:a:0",
                           "-shortest", "-y", out_path],
                           check=True, capture_output=True)

        except Exception as e:
            print(f"[LoloVideoCombine] 处理失败: {e}")
            raise e
        finally:
            for f in [list_file, temp_video, audio_file]:
                if f is not None and os.path.exists(f):
                    try:
                        os.remove(f)
                    except Exception as e:
                        print(f"[LoloVideoCombine] 临时文件删除失败（可忽略）: {e}")

        return (out_path,)