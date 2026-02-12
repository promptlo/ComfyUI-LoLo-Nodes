import os
import subprocess
import tempfile
import shutil

import torch
import torchaudio
import folder_paths

class LoloGetVideoInfo:
    """
    输入：视频文件（标准ComfyUI上传）
    输出：
        - frames_count (INT)
        - fps (FLOAT)
        - audio (AUDIO) : 波形 = [1, channels, samples], sample_rate = int
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

    def get_info(self, video):
        video_path = folder_paths.get_annotated_filepath(video)
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"视频文件不存在: {video_path}")

        self.ffmpeg_path = shutil.which("ffmpeg") or "ffmpeg"
        self.ffprobe_path = shutil.which("ffprobe") or "ffprobe"

        frames_count = self._get_frame_count(video_path)
        fps = self._get_fps(video_path)
        audio_data = self._extract_audio(video_path)

        return (frames_count, fps, audio_data)

    def _get_frame_count(self, video_path):
        try:
            cmd = [self.ffprobe_path, "-v", "error", "-select_streams", "v:0",
                   "-count_packets", "-show_entries", "stream=nb_read_packets",
                   "-of", "csv=p=0", video_path]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return int(result.stdout.strip())
        except:
            duration = self._get_duration(video_path)
            fps = self._get_fps(video_path)
            return int(duration * fps)

    def _get_duration(self, video_path):
        cmd = [self.ffprobe_path, "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        return float(result.stdout.strip() or 0)

    def _get_fps(self, video_path):
        cmd = [self.ffprobe_path, "-v", "error", "-select_streams", "v:0",
               "-show_entries", "stream=r_frame_rate",
               "-of", "default=noprint_wrappers=1:nokey=1", video_path]
        result = subprocess.run(cmd, capture_output=True, text=True)
        fps_str = result.stdout.strip()
        if '/' in fps_str:
            num, den = map(int, fps_str.split('/'))
            return num / den
        return float(fps_str)

    def _extract_audio(self, video_path):
        """提取音频，输出波形形状 = [1, channels, samples]"""
        waveform = torch.zeros(1, 44100)   # 默认静音，[channels, samples]
        sample_rate = 44100

        # 检查是否有音频流
        cmd_check = [self.ffprobe_path, "-v", "error", "-select_streams", "a:0",
                     "-show_entries", "stream=codec_type", "-of", "csv=p=0", video_path]
        check_res = subprocess.run(cmd_check, capture_output=True, text=True)

        if check_res.stdout.strip():
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

        # 强制转换为 [1, channels, samples] 标准格式
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).unsqueeze(0)   # [S] → [1, 1, S]
        elif waveform.dim() == 2:
            waveform = waveform.unsqueeze(0)                # [C, S] → [1, C, S]
        # 已经是 3维，确保 batch 维度在第一个

        return {"waveform": waveform, "sample_rate": sample_rate}

    @classmethod
    def IS_CHANGED(cls, video):
        path = folder_paths.get_annotated_filepath(video)
        return os.path.getmtime(path) if os.path.exists(path) else float("nan")