import os
import shutil
import folder_paths

try:
    from imageio_ffmpeg import get_ffmpeg_exe
    IMAGEIO_FFMPEG_AVAILABLE = True
except ImportError:
    IMAGEIO_FFMPEG_AVAILABLE = False
    get_ffmpeg_exe = None

def get_ffmpeg_path():
    """获取 ffmpeg 可执行文件路径（参考 VideoHelperSuite 的逻辑）"""
    # 1. 优先使用 imageio-ffmpeg 自动下载的版本
    if IMAGEIO_FFMPEG_AVAILABLE:
        try:
            path = get_ffmpeg_exe()
            if path and os.path.exists(path):
                return path
        except:
            pass

    # 2. 回退到系统 PATH
    path = shutil.which("ffmpeg")
    if path:
        return path

    # 3. 如果都找不到，抛出友好错误
    raise RuntimeError(
        "❌ 找不到 ffmpeg 可执行文件。\n"
        "请安装 imageio-ffmpeg：pip install imageio[ffmpeg]\n"
        "或将 ffmpeg 添加到系统 PATH 中。"
    )