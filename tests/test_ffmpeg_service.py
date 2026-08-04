"""Kiểm tra dịch vụ FFmpeg bằng video thật khi có cấu hình."""

from __future__ import annotations

import shutil
import wave
from pathlib import Path

from core.ffmpeg_service import doc_thong_tin_audio, kiem_tra_ffmpeg, lay_thoi_luong_video, tach_audio_wav


def _tim_video_that() -> Path:
    """Tìm video thật trong workspace hoặc dùng biến môi trường SRT_MAKER_TEST_VIDEO."""

    import os

    bien_moi_truong = os.environ.get("SRT_MAKER_TEST_VIDEO")
    if bien_moi_truong:
        return Path(bien_moi_truong)

    thu_muc_goc = Path(__file__).resolve().parents[2]
    for mau in ("*.mp4", "*.mkv", "*.avi", "*.mov", "*.wmv"):
        for duong_dan in thu_muc_goc.rglob(mau):
            if "SRT_MAKER" not in duong_dan.parts and duong_dan.is_file() and duong_dan.stat().st_size > 0:
                return duong_dan

    raise AssertionError("Không tìm thấy video thật để kiểm tra.")


def test_ffmpeg_tach_wav_bang_video_that(tmp_path: Path) -> None:
    """Kiểm tra FFmpeg, thời lượng, WAV mono 16 kHz và xóa được file tạm."""

    video = _tim_video_that()

    assert "ffmpeg" in kiem_tra_ffmpeg().lower()
    assert lay_thoi_luong_video(video) > 0

    wav = tach_audio_wav(video, tmp_path)
    assert wav.exists()
    assert wav.stat().st_size > 0

    thong_tin = doc_thong_tin_audio(wav)
    assert thong_tin.so_kenh == 1
    assert thong_tin.sample_rate == 16000
    assert thong_tin.codec == "pcm_s16le"

    with wave.open(str(wav), "rb") as tep_wav:
        assert tep_wav.getnchannels() == 1
        assert tep_wav.getframerate() == 16000
        assert tep_wav.getsampwidth() == 2

    thu_muc_tam = wav.parent
    shutil.rmtree(thu_muc_tam)
    assert not thu_muc_tam.exists()
