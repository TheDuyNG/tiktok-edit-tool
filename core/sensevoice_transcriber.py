"""Nháº­n dáº¡ng tiáº¿ng Trung báº±ng SenseVoice, tÃ¡ch riÃªng khá»i Whisper."""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
import tempfile
import time
import wave
from dataclasses import asdict
from pathlib import Path

from core.models import SubtitleSegment
from core.transcriber import LogCallback, TranscriberConfig, TranscriberError, TranscriptionResult


class SenseVoiceTranscriber:
    """Engine SenseVoice thÃ´ng qua FunASR, chá»‰ táº£i khi ngÆ°á»i dÃ¹ng chá»n."""

    CAC_MODEL_HOP_LE = {
        "sensevoice-small": "iic/SenseVoiceSmall",
        "iic/SenseVoiceSmall": "iic/SenseVoiceSmall",
        "SenseVoiceSmall": "iic/SenseVoiceSmall",
    }
    TEN_MODEL_VAD = "fsmn-vad"

    def __init__(self) -> None:
        self._model = None
        self._loaded_key: tuple[str, str] | None = None
        self._device_used = ""

    def release_model(self) -> None:
        self._model = None
        self._loaded_key = None
        self._device_used = ""

    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        config: TranscriberConfig | None = None,
        log: LogCallback = None,
    ) -> TranscriptionResult:
        """Nháº­n dáº¡ng WAV vÃ  lÆ°u JSON cÃ¹ng Ä‘á»‹nh dáº¡ng vá»›i Whisper."""

        config = config or TranscriberConfig(recognition_engine="sensevoice", model_size="sensevoice-small")
        if not audio_path.exists():
            raise TranscriberError("KhÃ´ng tÃ¬m tháº¥y file WAV Ä‘á»ƒ nháº­n dáº¡ng.")

        bat_dau = time.perf_counter()
        model = self._lay_model(config, log)
        ngon_ngu = "auto" if config.language in ("auto", "", None) else "zh"
        self._ghi_log(log, f"Äang nháº­n dáº¡ng báº±ng SenseVoice ({config.model_size})...")

        try:
            ket_qua_raw = model.generate(
                input=str(audio_path),
                language=ngon_ngu,
                use_itn=True,
                batch_size_s=60 if config.difficult_audio_mode else 120,
                merge_vad=True,
                merge_length_s=15,
            )
        except Exception as loi:
            raise TranscriberError(f"SenseVoice nháº­n dáº¡ng tháº¥t báº¡i: {loi}") from loi

        segments = self._tao_segments(ket_qua_raw, audio_path)
        if not segments:
            raise TranscriberError("SenseVoice khÃ´ng tráº£ vá» segment nÃ o.")

        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / f"{audio_path.stem}_transcription_zh.json"
        self._luu_json(json_path, segments)

        return TranscriptionResult(
            segments=segments,
            json_path=json_path,
            elapsed_seconds=time.perf_counter() - bat_dau,
            device_used=self._device_used or "sensevoice",
            compute_type="auto",
        )

    def _lay_model(self, config: TranscriberConfig, log: LogCallback):
        ten_model = self.CAC_MODEL_HOP_LE.get(config.model_size, "iic/SenseVoiceSmall")
        key = (ten_model, config.device)
        if self._model is not None and self._loaded_key == key:
            self._ghi_log(log, f"DÃ¹ng láº¡i SenseVoice Ä‘Ã£ táº£i: {ten_model}")
            return self._model

        self._them_ffmpeg_vao_path()
        cache_dir = self._dat_cache_modelscope()
        ten_model_chay = self._tim_snapshot_model_local(ten_model, cache_dir) or ten_model
        vad_model_chay = self._tim_snapshot_vad_local(cache_dir) or self.TEN_MODEL_VAD
        try:
            from funasr import AutoModel
        except ImportError as loi:
            raise TranscriberError(
                "Chua cai SenseVoice/FunASR trong Python dang chay. "
                f"Python dang chay: {sys.executable}. "
                "Hay cai dung moi truong: python -m pip install funasr modelscope"
            ) from loi

        self._ghi_log(log, f"Äang táº£i SenseVoice: {ten_model}")
        device = "cuda:0" if config.device == "cuda" else "cpu"
        if config.device == "auto":
            # SenseVoice/FunASR de loi thieu DLL CUDA tren Windows neu tu ep GPU.
            # Khi chon auto, uu tien CPU de tool chay on dinh; ai can GPU thi chon cuda.
            device = "cpu"

        try:
            self._model = AutoModel(
                model=str(ten_model_chay),
                vad_model=str(vad_model_chay),
                device=device,
                disable_update=True,
            )
        except Exception as loi:
            if device != "cpu" and config.device == "auto":
                self._ghi_log(log, f"SenseVoice cháº¡y GPU lá»—i, tá»± chuyá»ƒn sang CPU: {loi}")
                self._model = AutoModel(
                    model=str(ten_model_chay),
                    vad_model=str(vad_model_chay),
                    device="cpu",
                    disable_update=True,
                )
            elif device != "cpu":
                raise TranscriberError(
                    "SenseVoice chạy GPU thất bại. Vui lòng kiểm tra CUDA/PyTorch/FunASR. "
                    f"Lỗi gốc: {loi}"
                ) from loi
            else:
                raise

        self._loaded_key = key
        self._device_used = device
        return self._model

    def _dat_cache_modelscope(self) -> Path:
        cache_dir = self._cache_modelscope_an_toan()
        try:
            cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            cache_dir = Path(tempfile.gettempdir()) / "SRT_MAKER" / "modelscope"
            cache_dir.mkdir(parents=True, exist_ok=True)
        self._dong_bo_cache_cu_sang_cache_an_toan(cache_dir)
        os.environ["MODELSCOPE_CACHE"] = str(cache_dir)
        os.environ["MODELSCOPE_HOME"] = str(cache_dir)
        return cache_dir

    def _cache_modelscope_an_toan(self) -> Path:
        cau_hinh_rieng = os.environ.get("SRT_MAKER_MODELSCOPE_CACHE")
        if cau_hinh_rieng:
            return Path(cau_hinh_rieng).expanduser()

        cache_hien_tai = os.environ.get("MODELSCOPE_CACHE")
        if cache_hien_tai and self._duong_dan_ascii(Path(cache_hien_tai)):
            return Path(cache_hien_tai).expanduser()

        if os.name == "nt":
            goc = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())
        else:
            goc = Path(os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache")
        return goc / "SRT_MAKER" / "modelscope"

    def _dong_bo_cache_cu_sang_cache_an_toan(self, cache_dir: Path) -> None:
        cache_cu = Path(__file__).resolve().parents[1] / ".cache" / "modelscope"
        if not cache_cu.exists() or cache_cu.resolve() == cache_dir.resolve():
            return

        for ten_thu_muc in (
            "iic--SenseVoiceSmall",
            "SenseVoiceSmall",
            "iic--speech_fsmn_vad_zh-cn-16k-common-pytorch",
        ):
            nguon = cache_cu / "models" / ten_thu_muc
            dich = cache_dir / "models" / ten_thu_muc
            if nguon.exists() and not dich.exists():
                try:
                    dich.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copytree(nguon, dich)
                except OSError:
                    pass

    def _tim_snapshot_model_local(self, ten_model: str, cache_dir: Path) -> Path | None:
        cac_ung_vien = [
            cache_dir / "models" / "iic--SenseVoiceSmall" / "snapshots" / "master",
            cache_dir / "models" / "SenseVoiceSmall" / "snapshots" / "master",
        ]
        if ten_model not in ("iic/SenseVoiceSmall", "SenseVoiceSmall"):
            cac_ung_vien.insert(0, Path(ten_model))
        return self._snapshot_hop_le(cac_ung_vien)

    def _tim_snapshot_vad_local(self, cache_dir: Path) -> Path | None:
        return self._snapshot_hop_le(
            [
                cache_dir / "models" / "iic--speech_fsmn_vad_zh-cn-16k-common-pytorch" / "snapshots" / "master",
            ]
        )

    def _snapshot_hop_le(self, cac_ung_vien: list[Path]) -> Path | None:
        for ung_vien in cac_ung_vien:
            if (ung_vien / "config.yaml").exists() and (ung_vien / "model.pt").exists():
                return ung_vien
        return None

    def _duong_dan_ascii(self, duong_dan: Path) -> bool:
        try:
            str(duong_dan).encode("ascii")
        except UnicodeEncodeError:
            return False
        return True

    def _them_ffmpeg_vao_path(self) -> None:
        """GiÃºp FunASR tháº¥y FFmpeg do imageio_ffmpeg cung cáº¥p."""

        try:
            from core.ffmpeg_service import tim_ffmpeg

            ffmpeg = Path(tim_ffmpeg())
            if ffmpeg.exists():
                shim_dir = Path(__file__).resolve().parents[1] / "temp" / "ffmpeg_bin"
                shim_dir.mkdir(parents=True, exist_ok=True)
                shim = shim_dir / "ffmpeg.exe"
                if not shim.exists() or shim.stat().st_size != ffmpeg.stat().st_size:
                    shutil.copyfile(ffmpeg, shim)
                os.environ["PATH"] = f"{shim_dir};{ffmpeg.parent};{os.environ.get('PATH', '')}"
        except Exception:
            return

    def _tao_segments(self, ket_qua_raw: object, audio_path: Path) -> list[SubtitleSegment]:
        cac_muc = ket_qua_raw if isinstance(ket_qua_raw, list) else [ket_qua_raw]
        segments: list[SubtitleSegment] = []
        thoi_luong_audio = self._lay_thoi_luong_wav(audio_path)

        for muc in cac_muc:
            if not isinstance(muc, dict):
                continue
            timestamps = muc.get("timestamp") or []
            text = self._lam_sach_text(str(muc.get("text", "")))
            if timestamps and isinstance(timestamps, list):
                cac_cau = self._tach_cau(text, len(timestamps))
                for timestamp, cau in zip(timestamps, cac_cau):
                    if not cau or not isinstance(timestamp, (list, tuple)) or len(timestamp) < 2:
                        continue
                    start = float(timestamp[0]) / 1000
                    end = float(timestamp[1]) / 1000
                    if end <= start:
                        continue
                    segments.append(SubtitleSegment(index=len(segments) + 1, start=start, end=end, original_zh=cau, status="transcribed"))
            elif text:
                segments.extend(self._tao_segments_theo_cau(text, thoi_luong_audio, len(segments)))

        return segments

    def _tao_segments_theo_cau(self, text: str, thoi_luong_audio: float, offset_index: int) -> list[SubtitleSegment]:
        cac_cau = [cau.strip() for cau in re.split(r"(?<=[\u3002\uff01\uff1f!?])", text) if cau.strip()]
        if not cac_cau:
            cac_cau = [text]

        tong_ky_tu = max(1, sum(len(cau) for cau in cac_cau))
        ket_qua: list[SubtitleSegment] = []
        start = 0.0
        for vi_tri, cau in enumerate(cac_cau, start=1):
            if vi_tri == len(cac_cau):
                end = thoi_luong_audio
            else:
                thoi_luong = max(0.8, thoi_luong_audio * len(cau) / tong_ky_tu)
                end = min(thoi_luong_audio, start + thoi_luong)
            if end <= start:
                end = start + 0.8
            ket_qua.append(
                SubtitleSegment(
                    index=offset_index + len(ket_qua) + 1,
                    start=start,
                    end=end,
                    original_zh=cau,
                    status="transcribed",
                    warning="SenseVoice không trả timestamp chi tiết; thời gian được chia gần đúng theo câu.",
                )
            )
            start = end
        return ket_qua

    def _lay_thoi_luong_wav(self, audio_path: Path) -> float:
        try:
            with wave.open(str(audio_path), "rb") as wav:
                return max(1.0, wav.getnframes() / float(wav.getframerate()))
        except Exception:
            return 1.0

    def _tach_cau(self, text: str, so_luong: int) -> list[str]:
        cac_cau = [cau.strip() for cau in re.split(r"(?<=[\u3002\uff01\uff1f!?])", text) if cau.strip()]
        if len(cac_cau) == so_luong:
            return cac_cau
        if so_luong <= 1:
            return [text]
        return [text] + [""] * (so_luong - 1)

    def _lam_sach_text(self, text: str) -> str:
        text = re.sub(r"<\|[^>]+?\|>", "", text)
        return " ".join(text.split()).strip()

    def _luu_json(self, json_path: Path, segments: list[SubtitleSegment]) -> None:
        json_path.write_text(json.dumps({"segments": [asdict(segment) for segment in segments]}, ensure_ascii=False, indent=2), encoding="utf-8")

    def _ghi_log(self, log: LogCallback, noi_dung: str) -> None:
        if log:
            try:
                log(noi_dung)
            except UnicodeEncodeError:
                log(noi_dung.encode("ascii", errors="replace").decode("ascii"))
