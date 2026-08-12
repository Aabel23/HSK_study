"""On-demand Chinese pronunciation audio, generated once and cached on disk."""

from __future__ import annotations

import hashlib
from pathlib import Path

import edge_tts

from backend.config import get_audio_cache_dir
from backend.services.errors import InvalidOperationError

VOICES = {
    "female": "zh-CN-XiaoxiaoNeural",
    "male": "zh-CN-YunxiNeural",
}
DEFAULT_VOICE = "female"


def _cache_path(text: str, voice: str) -> Path:
    digest = hashlib.sha256(f"{voice}|{text}".encode("utf-8")).hexdigest()[:24]
    return get_audio_cache_dir() / f"{digest}.mp3"


def get_or_create_audio(text: str, voice: str = DEFAULT_VOICE) -> Path:
    clean_text = text.strip()
    if not clean_text:
        raise InvalidOperationError("Không có nội dung để phát âm.")
    voice_name = VOICES.get(voice, VOICES[DEFAULT_VOICE])
    path = _cache_path(clean_text, voice)
    if path.exists() and path.stat().st_size > 0:
        return path
    try:
        communicate = edge_tts.Communicate(clean_text, voice_name)
        communicate.save_sync(str(path))
    except Exception as error:
        if path.exists():
            path.unlink(missing_ok=True)
        raise InvalidOperationError(
            "Không thể tạo âm thanh phát âm. Cần có kết nối Internet cho lần phát đầu tiên "
            "của mỗi từ, sau đó âm thanh sẽ được lưu lại để dùng ngoại tuyến."
        ) from error
    return path
