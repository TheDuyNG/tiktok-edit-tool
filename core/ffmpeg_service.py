"""Dịch vụ kiểm tra FFmpeg và tách âm thanh từ video."""

from __future__ import annotations

import json
import os
import re
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path


class FfmpegError(RuntimeError):
    """Lỗi dễ đọc cho các thao tác FFmpeg."""


@dataclass(frozen=True)
class AudioInfo:
    """Thông tin kỹ thuật của file âm thanh đã tạo."""

    duong_dan: Path
    so_kenh: int
    sample_rate: int
    codec: str
    dung_luong: int


def _co_che_an_terminal() -> int:
    """Ẩn cửa sổ terminal phụ khi chạy FFmpeg trên Windows."""

    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        return subprocess.CREATE_NO_WINDOW
    return 0


def tim_ffmpeg() -> str:
    """Tìm FFmpeg, ưu tiên bản đi kèm project/imageio_ffmpeg rồi fallback sang PATH."""

    thu_muc_goc = Path(__file__).resolve().parents[1]
    ten_ffmpeg = "ffmpeg.exe" if os.name == "nt" else "ffmpeg"
    for ung_vien in (
        thu_muc_goc / "temp" / "ffmpeg_bin" / ten_ffmpeg,
        thu_muc_goc / "ffmpeg_bin" / ten_ffmpeg,
    ):
        if ung_vien.exists():
            return str(ung_vien)

    try:
        import imageio_ffmpeg

        duong_dan = imageio_ffmpeg.get_ffmpeg_exe()
        if duong_dan:
            return duong_dan
    except Exception:
        pass

    return "ffmpeg"


def tim_ffprobe() -> str:
    """Tìm FFprobe gần FFmpeg, nếu không có thì fallback sang PATH."""

    ffmpeg = Path(tim_ffmpeg())
    if ffmpeg.name.lower().startswith("ffmpeg"):
        ten = "ffprobe.exe" if ffmpeg.suffix.lower() == ".exe" else "ffprobe"
        ung_vien = ffmpeg.with_name(ten)
        if ung_vien.exists():
            return str(ung_vien)

    return "ffprobe"


def _rut_gon_loi(noi_dung: str) -> str:
    """Rút gọn stderr để log dễ hiểu hơn."""

    dong_loi = [dong.strip() for dong in noi_dung.splitlines() if dong.strip()]
    if not dong_loi:
        return "Không có thông tin lỗi chi tiết."
    return dong_loi[-1]


def chay_lenh(lenh: list[str], timeout: int = 60) -> subprocess.CompletedProcess[str]:
    """Chạy lệnh FFmpeg/FFprobe với timeout và hỗ trợ đường dẫn Unicode."""

    try:
        return subprocess.run(
            lenh,
            text=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            check=False,
            creationflags=_co_che_an_terminal(),
        )
    except FileNotFoundError as loi:
        raise FfmpegError("Không tìm thấy FFmpeg/FFprobe. Vui lòng cài FFmpeg hoặc thêm vào PATH.") from loi
    except subprocess.TimeoutExpired as loi:
        raise FfmpegError(f"FFmpeg chạy quá thời gian cho phép ({timeout} giây).") from loi
    except OSError as loi:
        raise FfmpegError(f"Không chạy được FFmpeg: {loi}") from loi


def kiem_tra_ffmpeg(timeout: int = 15) -> str:
    """Kiểm tra FFmpeg có hoạt động và trả về dòng phiên bản."""

    ffmpeg = tim_ffmpeg()
    ket_qua = chay_lenh([ffmpeg, "-version"], timeout=timeout)
    if ket_qua.returncode != 0:
        raise FfmpegError(f"FFmpeg không hoạt động: {_rut_gon_loi(ket_qua.stderr)}")

    dong_dau = ket_qua.stdout.splitlines()[0] if ket_qua.stdout else "FFmpeg hoạt động."
    return f"{ffmpeg} | {dong_dau}"


def kiem_tra_video(duong_dan_video: Path) -> None:
    """Kiểm tra file video đầu vào trước khi xử lý."""

    if not str(duong_dan_video).strip():
        raise ValueError("Vui lòng chọn video đầu vào.")

    if not duong_dan_video.exists():
        raise ValueError("File video không tồn tại.")

    if not duong_dan_video.is_file():
        raise ValueError("Đường dẫn video không phải là file.")


def lay_thoi_luong_video(duong_dan_video: Path, timeout: int = 30) -> float:
    """Lấy thời lượng video bằng FFprobe, fallback sang FFmpeg nếu cần."""

    kiem_tra_video(duong_dan_video)
    ffprobe = tim_ffprobe()
    lenh = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        str(duong_dan_video),
    ]
    loi_ffprobe = ""
    try:
        ket_qua = chay_lenh(lenh, timeout=timeout)
        if ket_qua.returncode == 0:
            try:
                du_lieu = json.loads(ket_qua.stdout)
                thoi_luong = float(du_lieu["format"]["duration"])
                if thoi_luong > 0:
                    return thoi_luong
            except (KeyError, TypeError, ValueError, json.JSONDecodeError):
                pass
        loi_ffprobe = _rut_gon_loi(ket_qua.stderr)
    except FfmpegError as loi:
        loi_ffprobe = str(loi)

    ffmpeg = tim_ffmpeg()
    ket_qua_ffmpeg = chay_lenh([ffmpeg, "-i", str(duong_dan_video)], timeout=timeout)
    noi_dung = f"{ket_qua_ffmpeg.stdout}\n{ket_qua_ffmpeg.stderr}"
    khop = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", noi_dung)
    if not khop:
        raise FfmpegError(f"Không đọc được thời lượng video: {loi_ffprobe or _rut_gon_loi(ket_qua_ffmpeg.stderr)}")

    gio, phut, giay = khop.groups()
    return int(gio) * 3600 + int(phut) * 60 + float(giay)


def tao_thu_muc_temp_video(duong_dan_video: Path, thu_muc_temp_goc: Path) -> Path:
    """Tạo thư mục tạm riêng theo tên video, không đụng vào video gốc."""

    ten_an_toan = re.sub(r"[^0-9A-Za-zÀ-ỹ._-]+", "_", duong_dan_video.stem, flags=re.UNICODE).strip("._")
    if not ten_an_toan:
        ten_an_toan = "video"

    thu_muc = thu_muc_temp_goc / ten_an_toan
    thu_muc.mkdir(parents=True, exist_ok=True)
    return thu_muc


def tach_audio_wav(duong_dan_video: Path, thu_muc_temp_goc: Path, timeout: int = 300) -> Path:
    """Tách audio WAV mono 16 kHz PCM 16-bit từ video."""

    kiem_tra_video(duong_dan_video)
    kiem_tra_ffmpeg()

    thu_muc_video = tao_thu_muc_temp_video(duong_dan_video, thu_muc_temp_goc)
    duong_dan_wav = thu_muc_video / "audio_16k_mono.wav"
    ffmpeg = tim_ffmpeg()
    lenh = [
        ffmpeg,
        "-y",
        "-i",
        str(duong_dan_video),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
        str(duong_dan_wav),
    ]

    ket_qua = chay_lenh(lenh, timeout=timeout)
    if ket_qua.returncode != 0:
        raise FfmpegError(f"Không tách được âm thanh: {_rut_gon_loi(ket_qua.stderr)}")

    if not duong_dan_wav.exists() or duong_dan_wav.stat().st_size <= 0:
        raise FfmpegError("FFmpeg đã chạy xong nhưng file WAV không được tạo hoặc rỗng.")

    return duong_dan_wav


def doc_thong_tin_audio(duong_dan_audio: Path, timeout: int = 30) -> AudioInfo:
    """Đọc thông tin audio để xác nhận WAV đúng chuẩn."""

    ffprobe = tim_ffprobe()
    lenh = [
        ffprobe,
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=channels,sample_rate,codec_name",
        "-of",
        "json",
        str(duong_dan_audio),
    ]
    try:
        ket_qua = chay_lenh(lenh, timeout=timeout)
        if ket_qua.returncode == 0:
            stream = json.loads(ket_qua.stdout)["streams"][0]
            return AudioInfo(
                duong_dan=duong_dan_audio,
                so_kenh=int(stream["channels"]),
                sample_rate=int(stream["sample_rate"]),
                codec=str(stream["codec_name"]),
                dung_luong=duong_dan_audio.stat().st_size,
            )
    except (FfmpegError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError):
        pass

    try:
        with wave.open(str(duong_dan_audio), "rb") as tep_wav:
            codec = "pcm_s16le" if tep_wav.getsampwidth() == 2 else f"pcm_{tep_wav.getsampwidth() * 8}"
            return AudioInfo(
                duong_dan=duong_dan_audio,
                so_kenh=tep_wav.getnchannels(),
                sample_rate=tep_wav.getframerate(),
                codec=codec,
                dung_luong=duong_dan_audio.stat().st_size,
            )
    except (OSError, wave.Error) as loi:
        raise FfmpegError("Không phân tích được thông tin kỹ thuật của WAV.") from loi
