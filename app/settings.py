"""Quản lý cấu hình cơ bản cho ứng dụng."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


THU_MUC_GOC = Path(__file__).resolve().parents[1]
DUONG_DAN_CAU_HINH = THU_MUC_GOC / "settings.json"


@dataclass
class AppSettings:
    """Cấu hình có thể mở rộng ở các giai đoạn sau."""

    ngon_ngu_nguon: str = "zh"
    ngon_ngu_dich: str = "vi"
    thu_muc_output: str = "output"
    thu_muc_temp: str = "temp"
    recognition_engine: str = "whisper"
    model_size: str = "medium"
    device: str = "auto"
    language: str = "zh"
    vad_filter: bool = True
    difficult_audio_mode: bool = False
    full_dialogue_mode: bool = True
    aggressive_gap_fill: bool = True
    ocr_fps: float = 3.0
    ocr_crop_left: float = 0.0
    ocr_crop_top: float = 0.75
    ocr_crop_right: float = 1.0
    ocr_crop_bottom: float = 1.0
    ocr_use_gpu: bool = True
    translation_provider: str = "gemini"
    translation_model: str = "gemini-3.5-flash"
    translation_quality: str = "balanced"
    translation_api_key: str = ""
    glossary_text: str = ""
    keep_wav: bool = True
    shutdown_when_done: bool = False


def tai_cau_hinh() -> AppSettings:
    """Đọc cấu hình từ settings.json, nếu lỗi thì dùng mặc định."""

    if not DUONG_DAN_CAU_HINH.exists():
        return AppSettings()

    try:
        du_lieu = json.loads(DUONG_DAN_CAU_HINH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return AppSettings()

    mac_dinh = asdict(AppSettings())
    gia_tri_hop_le = {key: value for key, value in {**mac_dinh, **du_lieu}.items() if key in mac_dinh}
    return AppSettings(**gia_tri_hop_le)


def luu_cau_hinh(cau_hinh: AppSettings) -> None:
    """Lưu cấu hình hiện tại ra settings.json."""

    DUONG_DAN_CAU_HINH.write_text(
        json.dumps(asdict(cau_hinh), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
