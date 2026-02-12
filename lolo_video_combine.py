import os
import subprocess
import tempfile
import shutil

import torch
import torchaudio
import folder_paths

class LoloVideoCombine:
    """
    输入：
        - any              (*)      ：仅用于触发执行
        - video_dir        (STRING) ：视频片段所在目录（支持两种格式）：
                                   1. 绝对路径（如 /root/output/segments）
                                   2. 相对路径（如 "segments"）→ 自动拼接输出目录
        - audio            (AUDIO)  ：波形 = [1, channels, samples]
        - filename_prefix  (STRING) ：输出文件名前缀
    输出：
        - result_path      (STRING) ：最终视频绝对路径
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "any": ("*", {"optional": True}),
                "video_dir": ("STRING", {"default": "segments", "multiline": False}),
                "audio": ("AUDIO",),
                "filename_prefix": ("STRING", {"default": "combined_video"}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result_path",)
    FUNCTION = "combine"
    CATEGORY = "LoLo Nodes/video"

    def combine(self, any, video_dir, audio, filename_prefix):
        # ---------- 智能路径解析：自动补全输出目录 ----------
        if not os.path.isabs(video_dir):
            # 相对路径 → 相对于 ComfyUI 输出目录
            base_dir = folder_paths.get_output_directory()
            video_dir = os.path.join(base_dir, video_dir)
            print(f"[LoloVideoCombine] 解析为相对路径: {video_dir}")

        # ---------- 1. 检查视频目录 ----------
        if not os.path.isdir(video_dir):
            raise NotADirectoryError(f"目录不存在: {video_dir}")

        files = [f for f in os.listdir(video_dir) if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm'))]
        files.sort()
        if not files:
            raise RuntimeError(f"目录中没有视频文件: {video_dir}")

        # ---------- 2. 自动生成输出路径 ----------
        output_dir = folder_paths.get_output_directory()
        os.makedirs(output_dir, exist_ok=True)
        counter = 1
        while True:
            out_path = os.path.join(output_dir, f"{filename_prefix}_{counter:05d}.mp4")
            if not os.path.exists(out_path):
                break
            counter += 1

        # ---------- 3. 跨平台 ffmpeg ----------
        ffmpeg = shutil.which("ffmpeg") or "ffmpeg"

        # ---------- 4. 临时文件变量预定义 ----------
        list_file = None
        temp_video = None
        audio_file = None

        try:
            # ========== 智能路径引号处理 ==========
            with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                list_file = f.name
                for file in files:
                    full_path = os.path.join(video_dir, file)
                    # 仅当路径包含空格时才加双引号（Windows/Linux均兼容）
                    if ' ' in full_path:
                        f.write(f'file "{full_path}"\n')
                    else:
                        f.write(f'file {full_path}\n')

            # 临时无音频视频
            with tempfile.NamedTemporaryFile(suffix='.mp4', delete=False) as tmp:
                temp_video = tmp.name

            # ---------- 尝试快速拼接（流复制）----------
            try:
                print(f"[LoloVideoCombine] 尝试快速拼接（流复制）...")
                subprocess.run([ffmpeg, "-f", "concat", "-safe", "0",
                               "-i", list_file, "-c", "copy", "-y", temp_video],
                               check=True, capture_output=True)
                print(f"[LoloVideoCombine] 流复制成功")
            except subprocess.CalledProcessError as e:
                print(f"[LoloVideoCombine] 流复制失败，错误信息:")
                print(e.stderr.decode())
                print(f"[LoloVideoCombine] 降级为重新编码（兼容模式）...")
                subprocess.run([ffmpeg, "-f", "concat", "-safe", "0",
                               "-i", list_file,
                               "-c:v", "libx264", "-crf", "18", "-preset", "fast",
                               "-c:a", "aac", "-b:a", "192k",
                               "-y", temp_video],
                               check=True, capture_output=True)
                print(f"[LoloVideoCombine] 重新编码成功")

            # ---------- 5. 处理音频 ----------
            waveform = audio["waveform"]
            sample_rate = audio["sample_rate"]

            # 转换为 [channels, samples] 用于 torchaudio.save
            if waveform.dim() == 3:
                waveform = waveform.squeeze(0)       # [1, C, S] → [C, S]
            elif waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)     # [S] → [1, S]

            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_audio:
                audio_file = tmp_audio.name
            torchaudio.save(audio_file, waveform, sample_rate)

            # ---------- 6. 合并音频到最终视频 ----------
            subprocess.run([ffmpeg, "-i", temp_video, "-i", audio_file,
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