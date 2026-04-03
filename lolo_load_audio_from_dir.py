import os
import torch
import torchaudio

class LoloLoadAudioFromDir:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_dir": ("STRING", {"default": "", "multiline": False}),
                "index": ("INT", {"default": 0, "min": 0, "max": 999999}),
            },
        }

    RETURN_TYPES = ("AUDIO",)
    RETURN_NAMES = ("audio",)
    FUNCTION = "load_audio"
    CATEGORY = "LoLo Nodes/audio"

    def load_audio(self, audio_dir, index):
        audio_dir = audio_dir.strip()
        if not audio_dir:
            raise ValueError("音频目录路径不能为空")

        if not os.path.isabs(audio_dir):
            comfy_root = os.getcwd()
            audio_dir = os.path.join(comfy_root, audio_dir)
            print(f"[LoloLoadAudioFromDir] 解析相对路径为: {audio_dir}")

        if not os.path.isdir(audio_dir):
            raise NotADirectoryError(f"音频目录不存在: {audio_dir}")

        supported_exts = ('.wav', '.mp3', '.flac', '.ogg', '.m4a', '.aac')
        files = [f for f in os.listdir(audio_dir) if f.lower().endswith(supported_exts)]
        files.sort()
        if not files:
            raise RuntimeError(f"目录中没有找到支持的音频文件: {audio_dir}")

        if index < 0 or index >= len(files):
            raise IndexError(f"索引 {index} 超出范围 (0-{len(files)-1})")

        file_path = os.path.join(audio_dir, files[index])
        print(f"[LoloLoadAudioFromDir] 加载音频: {file_path}")

        try:
            waveform, sample_rate = torchaudio.load(file_path)
        except Exception as e:
            raise RuntimeError(f"加载音频文件失败: {file_path}\n错误: {e}")

        # 转换为 ComfyUI 标准格式: [1, channels, samples]
        if waveform.dim() == 1:
            waveform = waveform.unsqueeze(0).unsqueeze(0)
        elif waveform.dim() == 2:
            waveform = waveform.unsqueeze(0)

        return ({"waveform": waveform, "sample_rate": sample_rate},)