"""Nhận dạng lời nói tiếng Trung bằng faster-whisper."""

from __future__ import annotations

import json
import os
import site
import sys
import sysconfig
import time
import ctypes
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from core.models import SubtitleSegment


LogCallback = Callable[[str], None] | None


class TranscriberError(RuntimeError):
    """Lỗi dễ hiểu cho bước nhận dạng."""


@dataclass(frozen=True)
class TranscriberConfig:
    """Cấu hình tải và chạy model faster-whisper."""

    model_size: str = "medium"
    recognition_engine: str = "whisper"
    language: str | None = "zh"
    device: str = "auto"
    vad_filter: bool = True
    difficult_audio_mode: bool = False
    full_dialogue_mode: bool = False
    aggressive_gap_fill: bool = True
    ocr_fps: float = 3.0
    ocr_crop_left: float = 0.0
    ocr_crop_top: float = 0.75
    ocr_crop_right: float = 1.0
    ocr_crop_bottom: float = 1.0
    ocr_use_gpu: bool = True


@dataclass(frozen=True)
class TranscriptionResult:
    """Kết quả nhận dạng và file JSON đi kèm."""

    segments: list[SubtitleSegment]
    json_path: Path
    elapsed_seconds: float
    device_used: str
    compute_type: str


class FasterWhisperTranscriber:
    """Bộ nhận dạng có cache model theo cấu hình."""

    CAC_MODEL_HOP_LE = {"small", "medium", "large-v3"}
    CAC_DEVICE_HOP_LE = {"auto", "cuda", "cpu"}

    def __init__(self) -> None:
        self._model = None
        self._loaded_key: tuple[str, str, str] | None = None
        self._device_used = ""
        self._compute_type = ""
        self._cuda_dll_handles: list[object] = []
        self._cuda_loaded_dlls: list[object] = []

    def release_model(self) -> None:
        """Giải phóng model đang giữ trong bộ nhớ."""

        self._model = None
        self._loaded_key = None
        self._device_used = ""
        self._compute_type = ""

    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        config: TranscriberConfig | None = None,
        log: LogCallback = None,
    ) -> TranscriptionResult:
        """Nhận dạng WAV và lưu kết quả JSON UTF-8."""

        config = config or TranscriberConfig()
        self._kiem_tra_cau_hinh(config)
        if not audio_path.exists():
            raise TranscriberError("Không tìm thấy file WAV để nhận dạng.")

        bat_dau = time.perf_counter()
        try:
            segments = self._nhan_dang_voi_config(audio_path, config, log)
        except Exception as loi:
            if self._device_used == "cuda" and config.device == "auto":
                self._ghi_log(log, f"CUDA lỗi khi nhận dạng, tự chuyển sang CPU: {loi}")
                self.release_model()
                cpu_config = TranscriberConfig(
                    model_size=config.model_size,
                    recognition_engine=config.recognition_engine,
                    language=config.language,
                    device="cpu",
                    vad_filter=config.vad_filter,
                    difficult_audio_mode=config.difficult_audio_mode,
                    full_dialogue_mode=config.full_dialogue_mode,
                    aggressive_gap_fill=config.aggressive_gap_fill,
                    ocr_fps=config.ocr_fps,
                    ocr_crop_left=config.ocr_crop_left,
                    ocr_crop_top=config.ocr_crop_top,
                    ocr_crop_right=config.ocr_crop_right,
                    ocr_crop_bottom=config.ocr_crop_bottom,
                    ocr_use_gpu=config.ocr_use_gpu,
                )
                try:
                    segments = self._nhan_dang_voi_config(audio_path, cpu_config, log)
                except Exception as loi_cpu:
                    raise TranscriberError(f"Nhận dạng thất bại sau khi chuyển sang CPU: {loi_cpu}") from loi_cpu
            elif self._device_used == "cuda" and config.device == "cuda":
                raise TranscriberError(
                    "Nhận dạng bằng GPU thất bại. Vui lòng kiểm tra CUDA/cuDNN/cuBLAS cho faster-whisper. "
                    f"Lỗi gốc: {loi}"
                ) from loi
            else:
                raise TranscriberError(f"Nhận dạng thất bại: {loi}") from loi

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{audio_path.stem}_transcription_zh.json"
        self._luu_json(json_path, segments)

        return TranscriptionResult(
            segments=segments,
            json_path=json_path,
            elapsed_seconds=time.perf_counter() - bat_dau,
            device_used=self._device_used,
            compute_type=self._compute_type,
        )

    def _nhan_dang_voi_config(
        self,
        audio_path: Path,
        config: TranscriberConfig,
        log: LogCallback = None,
    ) -> list[SubtitleSegment]:
        model = self._lay_model(config, log)
        ngon_ngu = None if config.language in ("auto", "", None) else config.language

        self._ghi_log(log, f"Đang nhận dạng bằng thiết bị {self._device_used}, compute_type {self._compute_type}.")
        if self._device_used == "cuda":
            self._nap_truoc_cuda_dll(log)

        tuy_chon_chong_lap = self._tao_tuy_chon_chong_lap(config)
        segments_iter, _info = model.transcribe(
            str(audio_path),
            language=ngon_ngu,
            vad_filter=False if config.full_dialogue_mode else config.vad_filter,
            beam_size=5 if config.difficult_audio_mode or config.full_dialogue_mode else 1,
            temperature=(0.0, 0.2, 0.4) if config.full_dialogue_mode else ((0.0, 0.2) if config.difficult_audio_mode else 0.0),
            condition_on_previous_text=False if config.difficult_audio_mode or config.full_dialogue_mode else True,
            vad_parameters=self._tao_tuy_chon_vad(config),
            **tuy_chon_chong_lap,
        )
        return self._tao_segments(segments_iter, log)

    def _kiem_tra_cau_hinh(self, config: TranscriberConfig) -> None:
        if config.model_size not in self.CAC_MODEL_HOP_LE:
            raise TranscriberError("Model chỉ hỗ trợ small, medium hoặc large-v3.")
        if config.device not in self.CAC_DEVICE_HOP_LE:
            raise TranscriberError("Thiết bị chỉ hỗ trợ auto, cuda hoặc cpu.")

    def _lay_model(self, config: TranscriberConfig, log: LogCallback):
        """Tải model nếu cấu hình đổi, ưu tiên GPU rồi tự fallback CPU khi lỗi."""

        self._them_duong_dan_cuda_dll(log)
        from faster_whisper import WhisperModel

        cac_lua_chon = self._chon_thiet_bi(config.device)
        loi_cuoi: Exception | None = None

        for device, compute_type in cac_lua_chon:
            key = (config.model_size, device, compute_type)
            if self._model is not None and self._loaded_key == key:
                self._ghi_log(log, f"Dùng lại model {config.model_size} đã tải.")
                return self._model

            self._ghi_log(log, f"Đang tải model {config.model_size} trên {device} ({compute_type})...")

            try:
                model = WhisperModel(config.model_size, device=device, compute_type=compute_type)
            except Exception as loi:
                loi_cuoi = loi
                if device == "cuda":
                    if config.device == "cuda":
                        self._ghi_log(log, f"CUDA lỗi với compute_type {compute_type}, thử cấu hình CUDA khác: {loi}")
                    else:
                        self._ghi_log(log, f"CUDA lỗi, tự chuyển sang CPU nếu không còn cấu hình GPU phù hợp: {loi}")
                continue

            self._model = model
            self._loaded_key = key
            self._device_used = device
            self._compute_type = compute_type
            return model

        raise TranscriberError(f"Không tải được model faster-whisper: {loi_cuoi}")

    def _them_duong_dan_cuda_dll(self, log: LogCallback) -> None:
        """Thêm thư mục DLL CUDA vào Windows search path trước khi tải ctranslate2."""

        if os.name != "nt":
            return

        cac_thu_muc_tim_kiem: list[Path] = []

        # 1. Thêm từ biến môi trường CUDA_PATH (cài đặt hệ thống)
        cuda_path_env = os.environ.get("CUDA_PATH")
        if cuda_path_env:
            cuda_path = Path(cuda_path_env)
            if cuda_path.exists():
                cac_thu_muc_tim_kiem.append(cuda_path / "bin")

        # 2. Thêm từ các gói trong môi trường Python
        cac_goc: list[Path] = []
        for key in ("purelib", "platlib"):
            duong_dan = sysconfig.get_paths().get(key)
            if duong_dan:
                cac_goc.append(Path(duong_dan))
        try:
            cac_goc.extend(Path(p) for p in site.getsitepackages())
        except Exception:
            pass
        cac_goc.extend(Path(p) for p in sys.path if p)

        for goc in dict.fromkeys(cac_goc):
            cac_thu_muc_tim_kiem.extend(
                [
                    goc / "torch" / "lib",
                    goc / "nvidia" / "cublas" / "bin",
                    goc / "nvidia" / "cudnn" / "bin",
                    goc / "nvidia" / "cuda_runtime" / "bin",
                ]
            )
            nvidia_root = goc / "nvidia"
            if nvidia_root.exists():
                cac_thu_muc_tim_kiem.extend(path for path in nvidia_root.glob("*\\bin") if path.is_dir())

        da_them = 0
        for thu_muc in dict.fromkeys(cac_thu_muc_tim_kiem):
            if not thu_muc or not thu_muc.exists():
                continue
            try:
                handle = os.add_dll_directory(str(thu_muc))
                self._cuda_dll_handles.append(handle)
                # Thêm vào PATH để các tiến trình con cũng thấy
                os.environ["PATH"] = f"{thu_muc};{os.environ.get('PATH', '')}"
                da_them += 1
            except (OSError, AttributeError):
                continue

        if da_them:
            self._ghi_log(log, f"Đã thêm {da_them} thư mục CUDA DLL vào đường dẫn tìm kiếm.")

    def _nap_truoc_cuda_dll(self, log: LogCallback) -> None:
        """Nạp trước DLL CUDA vì ctranslate2 có thể lazy-load khi bắt đầu nhận dạng."""

        if os.name != "nt" or self._cuda_loaded_dlls:
            return

        cac_ten = (
            "cublas64_12.dll",
            "cublasLt64_12.dll",
            "cudnn64_9.dll",
            "cudnn_ops64_9.dll",
            "cudnn_cnn64_9.dll",
            "cudnn_adv64_9.dll",
        )
        cac_goc: list[Path] = []
        for key in ("purelib", "platlib"):
            duong_dan = sysconfig.get_paths().get(key)
            if duong_dan:
                cac_goc.append(Path(duong_dan))
        try:
            cac_goc.extend(Path(p) for p in site.getsitepackages())
        except Exception:
            pass
        cac_goc.extend(Path(p) for p in sys.path if p)

        da_nap = 0
        for ten in cac_ten:
            dll_path = self._tim_cuda_dll(ten, cac_goc)
            if not dll_path:
                continue
            try:
                self._cuda_loaded_dlls.append(ctypes.WinDLL(str(dll_path)))
                da_nap += 1
            except OSError as loi:
                self._ghi_log(log, f"Không nạp trước được {ten}: {loi}")

        if da_nap:
            self._ghi_log(log, f"Đã nạp trước {da_nap} CUDA DLL.")

    def _tim_cuda_dll(self, ten: str, cac_goc: list[Path]) -> Path | None:
        for goc in dict.fromkeys(cac_goc):
            cac_duong_dan = (
                goc / "nvidia" / "cublas" / "bin" / ten,
                goc / "nvidia" / "cudnn" / "bin" / ten,
                goc / "torch" / "lib" / ten,
                goc / "ctranslate2" / ten,
            )
            for duong_dan in cac_duong_dan:
                if duong_dan.exists():
                    return duong_dan
        return None

    def _chon_thiet_bi(self, device: str) -> list[tuple[str, str]]:
        if device == "cpu":
            return [("cpu", "int8")]
        if device == "cuda":
            return [("cuda", "float16"), ("cuda", "int8_float16"), ("cuda", "float32"), ("cuda", "int8")]
        return [("cuda", "float16"), ("cuda", "int8_float16"), ("cuda", "float32"), ("cuda", "int8"), ("cpu", "int8")]

    def _tao_tuy_chon_chong_lap(self, config: TranscriberConfig) -> dict[str, object]:
        """Giáº£m lá»—i Whisper bá»‹ káº¹t má»™t cÃ¢u khi Ã¢m thanh ná»n khÃ³."""

        if config.full_dialogue_mode:
            return {
                "compression_ratio_threshold": 2.8,
                "log_prob_threshold": -1.5,
                "no_speech_threshold": 0.95,
            }

        if not config.difficult_audio_mode:
            return {
                "compression_ratio_threshold": 2.4,
                "log_prob_threshold": -1.0,
                "no_speech_threshold": 0.6,
            }

        return {
            "compression_ratio_threshold": 2.0,
            "log_prob_threshold": -0.8,
            "no_speech_threshold": 0.5,
        }

    def _tao_tuy_chon_vad(self, config: TranscriberConfig) -> dict[str, object] | None:
        """Làm VAD bớt gắt để không bỏ sót giọng hội thoại nhỏ hoặc xa mic."""

        if config.full_dialogue_mode:
            return {
                "threshold": 0.25,
                "min_speech_duration_ms": 80,
                "min_silence_duration_ms": 250,
                "speech_pad_ms": 500,
            }
        if config.difficult_audio_mode:
            return {
                "threshold": 0.35,
                "min_speech_duration_ms": 120,
                "min_silence_duration_ms": 350,
                "speech_pad_ms": 400,
            }
        return None

    def _tao_segments(self, segments_iter: object, log: LogCallback = None) -> list[SubtitleSegment]:
        ket_qua: list[SubtitleSegment] = []
        lan_log_cuoi = time.perf_counter()

        for segment in segments_iter:
            van_ban = str(getattr(segment, "text", "")).strip()
            if not van_ban:
                continue

            ket_qua.append(
                SubtitleSegment(
                    index=len(ket_qua) + 1,
                    start=float(segment.start),
                    end=float(segment.end),
                    original_zh=van_ban,
                    status="transcribed",
                )
            )
            bay_gio = time.perf_counter()
            if len(ket_qua) == 1 or len(ket_qua) % 25 == 0 or bay_gio - lan_log_cuoi >= 30:
                self._ghi_log(log, f"Nhận dạng vẫn chạy: đã có {len(ket_qua)} segment, đến {float(segment.end):.2f} giây audio.")
                lan_log_cuoi = bay_gio

        return ket_qua

    def _luu_json(self, json_path: Path, segments: list[SubtitleSegment]) -> None:
        du_lieu = {
            "segments": [asdict(segment) for segment in segments],
        }
        json_path.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ghi_log(self, log: LogCallback, noi_dung: str) -> None:
        """Ghi log nếu callback hoạt động; không để lỗi console làm dừng nhận dạng."""

        if not log:
            return

        try:
            log(noi_dung)
        except UnicodeEncodeError:
            log(noi_dung.encode("ascii", errors="replace").decode("ascii"))


Transcriber = FasterWhisperTranscriber
