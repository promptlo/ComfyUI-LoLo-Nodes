import os
import subprocess
import tempfile
import re

import torch
import torchaudio
import folder_paths

from .lolo_ffmpeg_utils import get_ffmpeg_path

class LoloGetVideoInfo:
    """
    输入：视频文件（标准ComfyUI上传）
    输出：
        - frames_count (INT)   : 视频总帧数（通过 duration * fps 估算）
        - fps (FLOAT)         : 视频帧率
        - audio (AUDIO)       : 波形 = [1, channels, samples], sample_rate = int
    """

    @classmethod
    def INPUT_TYPES(cls):
        input_dir = folder_paths.get_input_directory()
        files = []
        video_exts = ('.mp4', '.webm', '.avi', '.mov', '.mkv',
                      '.flv', '.m4v', '.mpg', '.mpeg', '.ts', '.wmv', '.gif')
        for f in os.listdir(input_dir):
            if os.path.isfile(os.path.join(input_dir, f)) and f.lower().endswith(video_exts):
                files.append(f)
        return {
            "required": {
                "video": (sorted(files), {"video_upload": True}),
            },
        }

    RETURN_TYPES = ("INT", "FLOAT", "AUDIO")
    RETURN_NAMES = ("frames_count", "fps", "audio")
    FUNCTION = "get_info"
    CATEGORY = "LoLo Nodes/video"

    def __init__(self):
        self.ffmpeg_path = None
        self._init_ffmpeg()

    def _init_ffmpeg(self):
        """初始化ffmpeg路径"""
        try:
            self.ffmpeg_path = get_ffmpeg_path()
            print(f"[LoloGetVideoInfo] ffmpeg: {self.ffmpeg_path}")
        except RuntimeError as e:
            raise RuntimeError(f"节点初始化失败: {e}")

    def get_info(self, video):
        video_path = folder_paths.get_annotated_filepath(video)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        # ---------- 通过 ffmpeg -i 解析视频信息 ----------
        duration, fps = self._probe_video(video_path)
        frames_count = int(duration * fps)
        audio_data = self._extract_audio(video_path)

        return (frames_count, fps, audio_data)

    def _probe_video(self, video_path):
        """
        运行 ffmpeg -i 并解析输出，获取时长（秒）和帧率（浮点数）
        返回 (duration, fps)
        """
        cmd = [self.ffmpeg_path, "-i", video_path, "-f", "null", "-"]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=False)
            output = result.stderr  # ffmpeg 输出到 stderr
        except Exception as e:
            raise RuntimeError(f"运行 ffmpeg 失败: {e}")

        # 解析时长 Duration: HH:MM:SS.milliseconds
        duration = 0.0
        duration_match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", output)
        if duration_match:
            h, m, s = duration_match.groups()
            duration = int(h) * 3600 + int(m) * 60 + float(s)

        # 解析帧率，寻找类似 "25 fps" 或 "30000/1001 fps"
        fps = 0.0
        fps_match = re.search(r"(\d+(?:\.\d+)?|\d+/\d+)\s+fps", output)
        if fps_match:
            fps_str = fps_match.group(1)
            if '/' in fps_str:
                num, den = map(int, fps_str.split('/'))
                fps = num / den
            else:
                fps = float(fps_str)

        if duration == 0 or fps == 0:
            raise RuntimeError(f"无法从视频中解析出时长或帧率:\n{output}")

        return duration, fps

    def _extract_audio(self, video_path):
        """提取音频，输出波形形状 = [1, channels, samples]（与之前相同）"""
        waveform = torch.zeros(1, 44100)  # 默认静音，[channels, samples]
        sample_rate = 44100

        # 检查是否有音频流（可选，不检查也能提取，失败回退静音）
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp_wav = tmp.name
        try:
            cmd = [self.ffmpeg_path, "-i", video_path, "-vn",
                   "-acodec", "pcm_s16le", "-y", tmp_wav]
            subprocess.run(cmd, check=True, capture_output=True)
            waveform, sample_rate = torchaudio.load(tmp_wav)  # [channels, samples]
        except Exception as e:
            print(f"[LoloGetVideoInfo] 音频提取失败: {e} → 使用静音")
        finally:
            if os.path.exists(tmp_wav):
                os.remove(tmp_wav)

        # 强制转换为 [1, channels, samples]
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).unsqueeze(0)   # [S] → [1, 1, S]
        elif waveform.dim() == 2:
            waveform = waveform.unsqueeze(0)                # [C, S] → [1, C, S]
        # 已经是3维，确保batch在第一维

        return {"waveform": waveform, "sample_rate": sample_rate}

    @classmethod
    def IS_CHANGED(cls, video):
        path = folder_paths.get_annotated_filepath(video)
        return os.path.getmtime(path) if os.path.exists(path) else float("nan")