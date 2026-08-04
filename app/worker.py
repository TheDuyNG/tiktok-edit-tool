"""Lá»›p Ä‘iá»u phá»‘i xá»­ lÃ½ ná»n cho cÃ¡c bÆ°á»›c táº¡o phá»¥ Ä‘á»."""

from __future__ import annotations

import json
import shutil
import sys
import threading
import time
from dataclasses import dataclass
from importlib import metadata
from pathlib import Path
from typing import Callable

from app.settings import tai_cau_hinh
from core.ffmpeg_service import (
    doc_thong_tin_audio,
    kiem_tra_ffmpeg,
    kiem_tra_video,
    lay_thoi_luong_video,
    tach_audio_wav,
)
from core.hybrid_transcriber import HybridTranscriber
from core.ocr_subtitle_transcriber import OcrSubtitleTranscriber
from core.sensevoice_transcriber import SenseVoiceTranscriber
from core.transcriber import FasterWhisperTranscriber, TranscriberConfig, TranscriptionResult
from core.srt_writer import (
    doc_segments_tu_json,
    ghi_srt_tieng_trung,
    ghi_srt_tieng_viet,
    tao_duong_dan_khong_trung,
    tao_preview_srt,
)
from core.translator import Translator
from core.translation.base import TranslationConfig, TranslationResult
from core.translation.validator import ty_le_chu_trung


@dataclass(frozen=True)
class PipelineConfig:
    """Cáº¥u hÃ¬nh cháº¡y pipeline má»™t video."""

    model_size: str
    recognition_engine: str
    device: str
    language: str
    vad_filter: bool
    difficult_audio_mode: bool
    full_dialogue_mode: bool
    aggressive_gap_fill: bool
    ocr_fps: float
    ocr_crop_left: float
    ocr_crop_top: float
    ocr_crop_right: float
    ocr_crop_bottom: float
    ocr_use_gpu: bool
    provider: str
    translation_model: str
    api_key: str
    quality_mode: str
    glossary_text: str
    keep_wav: bool


@dataclass(frozen=True)
class PipelineResult:
    """Káº¿t quáº£ pipeline hoÃ n chá»‰nh."""

    wav_path: Path
    transcribe_json_path: Path
    translation_json_path: Path
    zh_srt_path: Path
    vi_srt_path: Path
    vi_intermediate_json_path: Path
    step_times: dict[str, float]
    preview_zh: str
    preview_vi: str
    segment_count_zh: int
    segment_count_vi: int
    warnings: list[str] | None = None


class SrtMakerWorker:
    """Äiá»u phá»‘i cÃ¡c bÆ°á»›c FFmpeg vÃ  nháº­n dáº¡ng hiá»‡n cÃ³."""

    MIN_TRANSCRIPTION_COVERAGE = 0.75

    def __init__(self) -> None:
        self.transcriber = FasterWhisperTranscriber()
        self.sensevoice_transcriber = SenseVoiceTranscriber()
        self.hybrid_transcriber = HybridTranscriber(self.transcriber, self.sensevoice_transcriber)
        self.ocr_subtitle_transcriber = OcrSubtitleTranscriber()
        self.translator = Translator()

    def lay_thong_tin_moi_truong(self) -> list[str]:
        """Tra ve dung moi truong Python ma ung dung dang chay."""

        thong_tin = [
            f"Python dang chay: {sys.executable}",
            f"Phien ban Python: {sys.version.split()[0]}",
        ]

        for ten_goi in ("rapidocr-onnxruntime", "onnxruntime", "onnxruntime-directml", "paddleocr", "paddlepaddle-gpu", "torch"):
            try:
                thong_tin.append(f"{ten_goi}: {metadata.version(ten_goi)}")
            except metadata.PackageNotFoundError:
                thong_tin.append(f"{ten_goi}: chua cai")

        try:
            import torch

            thong_tin.append(f"Torch CUDA: {torch.cuda.is_available()}")
            thong_tin.append(f"Torch CUDA version: {torch.version.cuda}")
        except Exception as loi:
            thong_tin.append(f"Khong kiem tra duoc Torch CUDA: {loi}")

        try:
            import onnxruntime as ort

            providers = list(ort.get_available_providers())
            co_rapidocr = self._co_goi("rapidocr_onnxruntime")
            co_directml = "DmlExecutionProvider" in providers
            co_azure = "AzureExecutionProvider" in providers
            thong_tin.append(f"OCR RapidOCR: {'Có' if co_rapidocr else 'Chưa cài'}")
            thong_tin.append(f"OCR DirectML GPU: {'Có' if co_directml else 'Không'}")
            thong_tin.append(f"OCR providers: {providers}")
            if co_rapidocr and co_directml:
                thong_tin.append("TOOL OCR: SẴN SÀNG GPU DirectML.")
            elif co_rapidocr:
                thong_tin.append("TOOL OCR: SẴN SÀNG CPU, CHƯA CÓ GPU DirectML.")
            elif co_azure:
                thong_tin.append("TOOL OCR: CHƯA SẴN SÀNG, thiếu RapidOCR; Azure không thay thế DirectML.")
            else:
                thong_tin.append("TOOL OCR: CHƯA SẴN SÀNG, thiếu RapidOCR.")
        except Exception as loi:
            thong_tin.append(f"Khong kiem tra duoc OCR DirectML: {loi}")

        return thong_tin

    @staticmethod
    def _co_goi(ten_goi: str) -> bool:
        try:
            metadata.version(ten_goi)
            return True
        except metadata.PackageNotFoundError:
            return False

    def kiem_tra_ffmpeg_va_video(self, duong_dan_video: str) -> list[str]:
        """Kiá»ƒm tra FFmpeg, video vÃ  thá»i lÆ°á»£ng."""

        video = Path(duong_dan_video)
        kiem_tra_video(video)
        phien_ban = kiem_tra_ffmpeg()
        thoi_luong = lay_thoi_luong_video(video)

        return [
            f"FFmpeg hoáº¡t Ä‘á»™ng: {phien_ban}",
            f"Video há»£p lá»‡: {video}",
            f"Thá»i lÆ°á»£ng video: {thoi_luong:.2f} giÃ¢y",
        ]

    def tach_audio(self, duong_dan_video: str) -> tuple[Path, list[str]]:
        """TÃ¡ch Ã¢m thanh WAV vÃ  tráº£ vá» Ä‘Æ°á»ng dáº«n cÃ¹ng log."""

        cau_hinh = tai_cau_hinh()
        video = Path(duong_dan_video)
        thu_muc_temp = Path(cau_hinh.thu_muc_temp)
        wav = tach_audio_wav(video, thu_muc_temp)
        thong_tin = doc_thong_tin_audio(wav)

        return wav, [
            f"ÄÃ£ táº¡o WAV: {wav}",
            f"Dung lÆ°á»£ng WAV: {thong_tin.dung_luong} byte",
            f"Chuáº©n audio: {thong_tin.so_kenh} kÃªnh, {thong_tin.sample_rate} Hz, codec {thong_tin.codec}",
        ]

    def nhan_dang_tieng_trung(
        self,
        duong_dan_wav: str,
        recognition_engine: str,
        model_size: str,
        device: str,
        language: str,
        vad_filter: bool,
        full_dialogue_mode: bool,
        aggressive_gap_fill: bool,
        log_callback: Callable[[str], None],
    ) -> TranscriptionResult:
        """Nháº­n dáº¡ng tiáº¿ng Trung tá»« WAV, chÆ°a dá»‹ch sang tiáº¿ng Viá»‡t."""

        wav = Path(duong_dan_wav)
        if not wav.exists():
            raise ValueError("Vui lÃ²ng tÃ¡ch Ã¢m thanh trÆ°á»›c khi nháº­n dáº¡ng.")

        config = TranscriberConfig(
            model_size=model_size,
            recognition_engine=recognition_engine,
            language=None if language == "auto" else language,
            device=device,
            vad_filter=vad_filter,
            difficult_audio_mode=False,
            full_dialogue_mode=full_dialogue_mode,
            aggressive_gap_fill=aggressive_gap_fill,
        )
        return self._chon_transcriber(config).transcribe(wav, wav.parent, config, log_callback)

    def nhan_dang_ocr_tieng_trung(
        self,
        duong_dan_video: str,
        thu_muc_dau_ra: str,
        ocr_fps: float,
        ocr_crop_left: float,
        ocr_crop_top: float,
        ocr_crop_right: float,
        ocr_crop_bottom: float,
        ocr_use_gpu: bool,
        log_callback: Callable[[str], None],
    ) -> TranscriptionResult:
        """Nhan dang phu de Trung co san tren video bang OCR."""

        video = Path(duong_dan_video)
        if not video.exists():
            raise ValueError("Vui lòng chọn video trước khi chạy OCR.")

        output = Path(thu_muc_dau_ra).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        config = TranscriberConfig(
            recognition_engine="ocr_subtitle",
            language="zh",
            ocr_fps=ocr_fps,
            ocr_crop_left=ocr_crop_left,
            ocr_crop_top=ocr_crop_top,
            ocr_crop_right=ocr_crop_right,
            ocr_crop_bottom=ocr_crop_bottom,
            ocr_use_gpu=ocr_use_gpu,
        )
        return self.ocr_subtitle_transcriber.transcribe(video, output, config, log_callback)

    def xuat_srt_tieng_trung(self, duong_dan_video: str, duong_dan_wav: str, thu_muc_dau_ra: str):
        """Xuáº¥t SRT tiáº¿ng Trung tá»« JSON nháº­n dáº¡ng Ä‘Ã£ cÃ³."""

        video = Path(duong_dan_video)
        wav = Path(duong_dan_wav)
        output = Path(thu_muc_dau_ra).expanduser().resolve()
        if not video.exists():
            raise ValueError("Vui lÃ²ng chá»n video gá»‘c Ä‘á»ƒ Ä‘áº·t tÃªn file SRT.")

        json_path = wav.parent / f"{wav.stem}_transcription_zh.json"
        if not json_path.exists():
            cac_ung_vien_ocr = [
                output / f"{video.stem}_ocr_transcription_zh.json",
                video.parent / f"{video.stem}_ocr_transcription_zh.json",
            ]
            json_path = next((ung_vien for ung_vien in cac_ung_vien_ocr if ung_vien.exists()), json_path)
        if not json_path.exists():
            if not wav.exists():
                raise ValueError("Vui lòng nhận dạng OCR hoặc tách âm thanh trước khi xuất SRT.")
            raise ValueError("ChÆ°a tÃ¬m tháº¥y JSON nháº­n dáº¡ng tiáº¿ng Trung. Vui lÃ²ng nháº­n dáº¡ng trÆ°á»›c.")

        thoi_luong = lay_thoi_luong_video(video)
        cac_doan = doc_segments_tu_json(json_path)
        srt_path, cac_doan_sach = ghi_srt_tieng_trung(cac_doan, video, output, thoi_luong)
        preview = tao_preview_srt(cac_doan_sach)
        return {
            "srt_path": srt_path,
            "json_path": json_path,
            "segment_count": len(cac_doan_sach),
            "preview": preview,
        }

    def dich_thu(
        self,
        duong_dan_wav: str,
        provider: str,
        model: str,
        api_key: str,
        quality_mode: str,
        glossary_text: str,
    ) -> TranslationResult:
        """Dá»‹ch thá»­ tá»« JSON nháº­n dáº¡ng, chÆ°a xuáº¥t SRT tiáº¿ng Viá»‡t."""

        wav = Path(duong_dan_wav)
        if not wav.exists():
            raise ValueError("Vui lÃ²ng tÃ¡ch Ã¢m thanh vÃ  nháº­n dáº¡ng trÆ°á»›c khi dá»‹ch thá»­.")

        json_path = wav.parent / f"{wav.stem}_transcription_zh.json"
        if not json_path.exists():
            raise ValueError("ChÆ°a tÃ¬m tháº¥y JSON nháº­n dáº¡ng tiáº¿ng Trung. Vui lÃ²ng nháº­n dáº¡ng trÆ°á»›c.")

        cac_doan = doc_segments_tu_json(json_path)
        config = TranslationConfig(
            provider=provider,
            model=model.strip() or self._model_dich_mac_dinh(provider),
            quality_mode=quality_mode,
            glossary_text=glossary_text,
            api_key=api_key,
        )
        ket_qua = self.translator.translate(cac_doan, config)
        self._luu_json_dich_tieng_viet(self._duong_dan_json_dich(wav, provider, config.model), ket_qua.segments)
        return ket_qua

    def xuat_srt_tieng_viet(self, duong_dan_video: str, duong_dan_wav: str, thu_muc_dau_ra: str):
        """Xuáº¥t SRT tiáº¿ng Viá»‡t tá»‘i Æ°u cho phá»¥ Ä‘á» vÃ  TTS."""

        video = Path(duong_dan_video)
        wav = Path(duong_dan_wav)
        if not video.exists():
            raise ValueError("Vui lÃ²ng chá»n video gá»‘c Ä‘á»ƒ Ä‘áº·t tÃªn file SRT.")
        if not wav.exists():
            raise ValueError("Vui lÃ²ng tÃ¡ch Ã¢m thanh, nháº­n dáº¡ng vÃ  dá»‹ch thá»­ trÆ°á»›c khi xuáº¥t SRT tiáº¿ng Viá»‡t.")

        json_path = self._tim_json_dich_moi_nhat(wav)
        if not json_path.exists():
            raise ValueError("ChÆ°a tÃ¬m tháº¥y JSON dá»‹ch tiáº¿ng Viá»‡t. Vui lÃ²ng báº¥m Dá»‹ch thá»­ trÆ°á»›c.")

        thoi_luong = lay_thoi_luong_video(video)
        cac_doan = doc_segments_tu_json(json_path)
        srt_path, vi_json_path, cac_doan_sach = ghi_srt_tieng_viet(cac_doan, video, Path(thu_muc_dau_ra), thoi_luong)
        preview = tao_preview_srt(cac_doan_sach, "cleaned_text")
        so_canh_bao = sum(1 for doan in cac_doan_sach if doan.warning)
        return {
            "srt_vi_path": srt_path,
            "json_vi_path": vi_json_path,
            "segment_count": len(cac_doan_sach),
            "warning_count": so_canh_bao,
            "preview": preview,
        }

    def _luu_json_dich_tieng_viet(self, json_path: Path, cac_doan) -> None:
        du_lieu = {
            "segments": [
                {
                    "index": doan.index,
                    "start": doan.start,
                    "end": doan.end,
                    "original_zh": doan.original_zh,
                    "translated_vi": doan.translated_vi,
                    "cleaned_text": doan.cleaned_text,
                    "status": doan.status,
                    "warning": doan.warning,
                }
                for doan in cac_doan
            ]
        }
        json_path.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding="utf-8")

    def chay_pipeline(
        self,
        duong_dan_video: str,
        thu_muc_dau_ra: str,
        config: PipelineConfig,
        log_callback: Callable[[str], None],
        progress_callback: Callable[[str, int], None],
        stop_event,
    ) -> PipelineResult:
        """Cháº¡y pipeline hoÃ n chá»‰nh cho má»™t video."""

        video = Path(duong_dan_video)
        output = Path(thu_muc_dau_ra).expanduser().resolve()
        output.mkdir(parents=True, exist_ok=True)
        log_callback(f"Nơi lưu kết quả đã chọn: {output}")
        cau_hinh = tai_cau_hinh()
        temp_root = Path(cau_hinh.thu_muc_temp)
        step_times: dict[str, float] = {}
        warnings: list[str] = []

        def bao_buoc(ten_buoc: str, phan_tram: int) -> None:
            self._kiem_tra_dung(stop_event)
            progress_callback(ten_buoc, phan_tram)
            log_callback(f"BÆ°á»›c: {ten_buoc}")

        def do_time(ten_buoc: str, ham):
            bat_dau = time.perf_counter()
            da_xong = threading.Event()

            def log_nhip_tim() -> None:
                while not da_xong.wait(30):
                    da_chay = time.perf_counter() - bat_dau
                    log_callback(f"Vẫn đang chạy bước {ten_buoc}: {da_chay:.0f} giây, chưa bị đơ.")

            threading.Thread(target=log_nhip_tim, daemon=True).start()
            try:
                ket_qua = ham()
                return ket_qua
            finally:
                da_xong.set()
                step_times[ten_buoc] = time.perf_counter() - bat_dau
                log_callback(f"HoÃ n táº¥t {ten_buoc}: {step_times[ten_buoc]:.2f} giÃ¢y")

        bao_buoc("Kiá»ƒm tra FFmpeg vÃ  video", 5)
        thoi_luong = do_time("Kiá»ƒm tra FFmpeg", lambda: self._kiem_tra_video_pipeline(video))

        is_ocr = config.recognition_engine == "ocr_subtitle"
        bao_buoc("TÃ¡ch WAV", 15)
        if is_ocr:
            wav = video
            temp_ocr = temp_root / self._ten_an_toan(video.stem)
            temp_ocr.mkdir(parents=True, exist_ok=True)
            log_callback("OCR phụ đề: bỏ qua tách WAV, đọc chữ trực tiếp trên video.")
        else:
            wav = do_time("TÃ¡ch WAV", lambda: self._lay_hoac_tach_wav(video, temp_root))
            doc_thong_tin_audio(wav)
            temp_ocr = wav.parent

        transcribe_json = temp_ocr / (f"{video.stem}_ocr_transcription_zh.json" if is_ocr else f"{wav.stem}_transcription_zh.json")
        bao_buoc("Nháº­n dáº¡ng tiáº¿ng Trung", 35)
        if config.recognition_engine == "whisper" and self._json_nhan_dang_hop_le(transcribe_json, thoi_luong):
            log_callback(f"DÃ¹ng láº¡i JSON nháº­n dáº¡ng há»£p lá»‡: {transcribe_json}")
            segments_zh = doc_segments_tu_json(transcribe_json)
            step_times["Nháº­n dáº¡ng tiáº¿ng Trung"] = 0.0
        else:
            if transcribe_json.exists():
                log_callback(f"JSON nhận dạng cũ không phủ đủ video, sẽ nhận dạng lại: {transcribe_json}")
            transcribe_config = TranscriberConfig(
                model_size=config.model_size,
                recognition_engine=config.recognition_engine,
                language=None if config.language == "auto" else config.language,
                device=config.device,
                vad_filter=False if config.difficult_audio_mode or config.full_dialogue_mode else config.vad_filter,
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
            da_thu_video_kho = transcribe_config.difficult_audio_mode
            if config.difficult_audio_mode:
                log_callback("Đang bật chế độ âm thanh khó: tắt VAD và tăng độ kỹ khi nhận dạng.")
            if config.full_dialogue_mode:
                log_callback("Đang bật chế độ nhận dạng toàn bộ hội thoại: tắt VAD và giảm bỏ sót giọng nhỏ/giọng phụ.")
            ham_nhan_dang = (
                (lambda: self._chon_transcriber(transcribe_config).transcribe(video, temp_ocr, transcribe_config, log_callback))
                if is_ocr
                else (lambda: self._chon_transcriber(transcribe_config).transcribe(wav, wav.parent, transcribe_config, log_callback))
            )
            ket_qua_nhan_dang = do_time(
                "Nháº­n dáº¡ng tiáº¿ng Trung",
                ham_nhan_dang,
            )
            segments_zh = ket_qua_nhan_dang.segments
            transcribe_json = ket_qua_nhan_dang.json_path

            if not is_ocr and self._co_lap_nhan_dang_bat_thuong(segments_zh) and not transcribe_config.difficult_audio_mode:
                log_callback("Phát hiện nhận dạng bị lặp bất thường. Tự nhận dạng lại bằng chế độ âm thanh khó.")
                transcribe_config_kho = TranscriberConfig(
                    model_size=config.model_size,
                    recognition_engine=config.recognition_engine,
                    language=None if config.language == "auto" else config.language,
                    device=config.device,
                    vad_filter=False,
                    difficult_audio_mode=True,
                    full_dialogue_mode=config.full_dialogue_mode,
                    aggressive_gap_fill=config.aggressive_gap_fill,
                )
                ket_qua_nhan_dang = do_time(
                    "Nhận dạng lại chống lặp",
                    lambda: self._chon_transcriber(transcribe_config_kho).transcribe(wav, wav.parent, transcribe_config_kho, log_callback),
                )
                segments_zh = ket_qua_nhan_dang.segments
                transcribe_json = ket_qua_nhan_dang.json_path
                da_thu_video_kho = True

            if not is_ocr and not self._segments_phu_du_video(segments_zh, thoi_luong):
                do_phu = self._do_phu_segments(segments_zh, thoi_luong)
                if config.vad_filter:
                    log_callback(
                        f"Nhận dạng mới chỉ phủ {do_phu:.1%} video. Thử nhận dạng lại với VAD tắt để tránh bị cắt mất đoạn."
                    )
                    transcribe_config_khong_vad = TranscriberConfig(
                        model_size=config.model_size,
                        recognition_engine=config.recognition_engine,
                        language=None if config.language == "auto" else config.language,
                        device=config.device,
                        vad_filter=False,
                        difficult_audio_mode=config.difficult_audio_mode,
                        full_dialogue_mode=config.full_dialogue_mode,
                        aggressive_gap_fill=config.aggressive_gap_fill,
                    )
                    ket_qua_nhan_dang = do_time(
                        "Nhận dạng tiếng Trung không VAD",
                        lambda: self._chon_transcriber(transcribe_config_khong_vad).transcribe(wav, wav.parent, transcribe_config_khong_vad, log_callback),
                    )
                    segments_zh = ket_qua_nhan_dang.segments
                    transcribe_json = ket_qua_nhan_dang.json_path
                    do_phu = self._do_phu_segments(segments_zh, thoi_luong)

                    if self._co_lap_nhan_dang_bat_thuong(segments_zh) and not transcribe_config_khong_vad.difficult_audio_mode:
                        log_callback("Kết quả không VAD vẫn bị lặp. Tự nhận dạng lại bằng chế độ âm thanh khó.")
                        transcribe_config_kho = TranscriberConfig(
                            model_size=config.model_size,
                            recognition_engine=config.recognition_engine,
                            language=None if config.language == "auto" else config.language,
                            device=config.device,
                            vad_filter=False,
                            difficult_audio_mode=True,
                            full_dialogue_mode=config.full_dialogue_mode,
                            aggressive_gap_fill=config.aggressive_gap_fill,
                        )
                        ket_qua_nhan_dang = do_time(
                            "Nhận dạng lại chống lặp",
                            lambda: self._chon_transcriber(transcribe_config_kho).transcribe(wav, wav.parent, transcribe_config_kho, log_callback),
                        )
                        segments_zh = ket_qua_nhan_dang.segments
                        transcribe_json = ket_qua_nhan_dang.json_path
                        do_phu = self._do_phu_segments(segments_zh, thoi_luong)
                        da_thu_video_kho = True

                if not self._segments_phu_du_video(segments_zh, thoi_luong) and not da_thu_video_kho:
                    log_callback(
                        f"Nhận dạng mới chỉ phủ {do_phu:.1%} video. Tự chuyển sang chế độ video khó để nhận dạng lại."
                    )
                    transcribe_config_kho = TranscriberConfig(
                        model_size=config.model_size,
                        recognition_engine=config.recognition_engine,
                        language=None if config.language == "auto" else config.language,
                        device=config.device,
                        vad_filter=False,
                        difficult_audio_mode=True,
                        full_dialogue_mode=True,
                        aggressive_gap_fill=config.aggressive_gap_fill,
                    )
                    ket_qua_nhan_dang = do_time(
                        "Nhận dạng lại video khó",
                        lambda: self._chon_transcriber(transcribe_config_kho).transcribe(wav, wav.parent, transcribe_config_kho, log_callback),
                    )
                    segments_zh = ket_qua_nhan_dang.segments
                    transcribe_json = ket_qua_nhan_dang.json_path
                    do_phu = self._do_phu_segments(segments_zh, thoi_luong)
                    da_thu_video_kho = True

                if self._co_khoang_trong_lon_bat_thuong(segments_zh, thoi_luong) and not config.full_dialogue_mode:
                    log_callback("Phát hiện nhiều khoảng trống lớn trong phụ đề. Tự nhận dạng lại chế độ toàn bộ hội thoại.")
                    transcribe_config_day_du = TranscriberConfig(
                        model_size=config.model_size,
                        recognition_engine=config.recognition_engine,
                        language=None if config.language == "auto" else config.language,
                        device=config.device,
                        vad_filter=False,
                        difficult_audio_mode=True,
                        full_dialogue_mode=True,
                        aggressive_gap_fill=config.aggressive_gap_fill,
                    )
                    ket_qua_nhan_dang = do_time(
                        "Nhận dạng lại toàn bộ hội thoại",
                        lambda: self._chon_transcriber(transcribe_config_day_du).transcribe(wav, wav.parent, transcribe_config_day_du, log_callback),
                    )
                    segments_zh = ket_qua_nhan_dang.segments
                    transcribe_json = ket_qua_nhan_dang.json_path
                    do_phu = self._do_phu_segments(segments_zh, thoi_luong)

                if not self._segments_phu_du_video(segments_zh, thoi_luong):
                    if segments_zh:
                        canh_bao = f"Cảnh báo: nhận dạng chỉ phủ {do_phu:.1%} video, SRT có thể chưa hết video."
                        warnings.append(canh_bao)
                        log_callback(canh_bao)
                    else:
                        raise ValueError("Không nhận dạng được segment nào, không thể xuất SRT.")

        bao_buoc("LÆ°u JSON nháº­n dáº¡ng", 45)
        try:
            transcribe_json_output = do_time(
                "LÆ°u JSON nháº­n dáº¡ng",
                lambda: self._copy_json_khong_trung(transcribe_json, output / f"{video.stem}_transcription_zh.json"),
            )
        except OSError as loi:
            transcribe_json_output = transcribe_json
            canh_bao = f"Cảnh báo: không lưu được JSON trung gian vào nơi lưu đã chọn, vẫn tiếp tục xuất SRT. Lỗi: {loi}"
            warnings.append(canh_bao)
            log_callback(canh_bao)

        bao_buoc("Xuáº¥t SRT tiáº¿ng Trung", 55)
        zh_srt_path, zh_segments = do_time(
            "Xuáº¥t SRT tiáº¿ng Trung",
            lambda: ghi_srt_tieng_trung(segments_zh, video, output, thoi_luong),
        )
        zh_srt_path = zh_srt_path.resolve()
        if not zh_srt_path.exists() or zh_srt_path.stat().st_size <= 0:
            raise ValueError(f"Xuất SRT thất bại, không tìm thấy file kết quả: {zh_srt_path}")
        if zh_srt_path.parent.resolve() != output:
            raise ValueError(f"File SRT không nằm trong nơi lưu đã chọn. File: {zh_srt_path}. Nơi lưu: {output}")
        log_callback(f"Đã tạo file SRT: {zh_srt_path}")
        so_doan_da_loc = len(segments_zh) - len(zh_segments)
        if so_doan_da_loc > 0:
            log_callback(f"Đã lọc {so_doan_da_loc} segment trùng/liền kề trước khi xuất SRT.")

        bao_buoc("Dá»n file táº¡m", 98)
        do_time("Dá»n file táº¡m", lambda: self._don_file_tam(wav, True if is_ocr else config.keep_wav))

        bao_buoc("HoÃ n thÃ nh", 100)
        preview_zh = tao_preview_srt(zh_segments)
        return PipelineResult(
            wav_path=wav,
            transcribe_json_path=transcribe_json_output,
            translation_json_path=transcribe_json_output,
            zh_srt_path=zh_srt_path,
            vi_srt_path=zh_srt_path,
            vi_intermediate_json_path=transcribe_json_output,
            step_times=step_times,
            preview_zh=preview_zh,
            preview_vi=preview_zh,
            segment_count_zh=len(zh_segments),
            segment_count_vi=0,
            warnings=warnings,
        )

    def _kiem_tra_video_pipeline(self, video: Path) -> float:
        kiem_tra_video(video)
        kiem_tra_ffmpeg()
        return lay_thoi_luong_video(video)

    def _chon_transcriber(self, config: TranscriberConfig):
        if config.recognition_engine == "ocr_subtitle":
            return self.ocr_subtitle_transcriber
        if config.recognition_engine == "hybrid":
            return self.hybrid_transcriber
        if config.recognition_engine == "sensevoice":
            return self.sensevoice_transcriber
        return self.transcriber

    def _lay_hoac_tach_wav(self, video: Path, temp_root: Path) -> Path:
        from core.ffmpeg_service import tao_thu_muc_temp_video

        temp_video = tao_thu_muc_temp_video(video, temp_root)
        wav = temp_video / "audio_16k_mono.wav"
        if wav.exists() and wav.stat().st_size > 0:
            return wav
        return tach_audio_wav(video, temp_root)

    def _co_lap_nhan_dang_bat_thuong(self, segments) -> bool:
        """PhÃ¡t hiá»‡n Whisper bá»‹ káº¹t má»™t cÃ¢u trong má»™t khoáº£ng ngáº¯n."""

        moc_theo_noi_dung: dict[str, list[float]] = {}
        for doan in segments:
            noi_dung = " ".join(str(getattr(doan, "original_zh", "")).split())
            if len(noi_dung) < 6:
                continue
            moc_theo_noi_dung.setdefault(noi_dung, []).append(float(doan.start))

        for cac_moc in moc_theo_noi_dung.values():
            if len(cac_moc) >= 5 and max(cac_moc) - min(cac_moc) <= 120:
                return True
        return False

    def _json_nhan_dang_hop_le(self, json_path: Path, thoi_luong_video: float | None = None) -> bool:
        if not json_path.exists():
            return False
        try:
            segments = doc_segments_tu_json(json_path)
        except Exception:
            return False
        return (
            bool(segments)
            and all(doan.original_zh.strip() and doan.start < doan.end for doan in segments)
            and self._segments_phu_du_video(segments, thoi_luong_video)
            and not self._co_lap_nhan_dang_bat_thuong(segments)
        )

    def _segments_phu_du_video(self, segments, thoi_luong_video: float | None) -> bool:
        if thoi_luong_video is None or thoi_luong_video <= 0:
            return True
        if thoi_luong_video < 90:
            return True
        if not segments:
            return False
        return self._do_phu_segments(segments, thoi_luong_video) >= self.MIN_TRANSCRIPTION_COVERAGE

    def _do_phu_segments(self, segments, thoi_luong_video: float | None) -> float:
        if not segments or not thoi_luong_video or thoi_luong_video <= 0:
            return 0.0
        moc_cuoi = max(float(doan.end) for doan in segments)
        return min(1.0, moc_cuoi / thoi_luong_video)

    def _co_khoang_trong_lon_bat_thuong(self, segments, thoi_luong_video: float | None) -> bool:
        """Phát hiện khả năng bỏ sót hội thoại giữa video do VAD/ngưỡng no-speech quá gắt."""

        if not segments or not thoi_luong_video or thoi_luong_video < 120:
            return False

        da_sap_xep = sorted(segments, key=lambda doan: (float(doan.start), float(doan.end)))
        khoang_trong_lon = 0
        tong_khoang_trong = 0.0
        moc_truoc = 0.0

        for doan in da_sap_xep:
            start = float(doan.start)
            if start > moc_truoc:
                khoang = start - moc_truoc
                tong_khoang_trong += khoang
                if khoang >= 8.0:
                    khoang_trong_lon += 1
            moc_truoc = max(moc_truoc, float(doan.end))

        if thoi_luong_video > moc_truoc:
            tong_khoang_trong += thoi_luong_video - moc_truoc

        ty_le_trong = tong_khoang_trong / thoi_luong_video
        return khoang_trong_lon >= 3 or ty_le_trong >= 0.45

    def _json_dich_hop_le(self, json_path: Path) -> bool:
        if not json_path.exists():
            return False
        try:
            segments = doc_segments_tu_json(json_path)
        except Exception:
            return False
        return bool(segments) and all(self._ban_dich_segment_hop_le(doan) for doan in segments)

    def _kiem_tra_ban_dich(self, segments) -> None:
        if not segments:
            raise ValueError("Báº£n dá»‹ch khÃ´ng cÃ³ segment.")
        for doan in segments:
            if not self._ban_dich_segment_hop_le(doan):
                raise ValueError(f"Segment {doan.index} có bản dịch tiếng Việt không hợp lệ.")

    def _ban_dich_segment_hop_le(self, doan) -> bool:
        text = doan.translated_vi.strip()
        if not text or doan.start >= doan.end:
            return False

        mau_demo_cu = (
            "Câu hỏi trong hội thoại",
            "Câu thoại tiếp theo",
            "Câu cảm thán trong hội thoại",
            "Bản dịch thử",
        )
        if text.startswith(mau_demo_cu):
            return False

        if ty_le_chu_trung(text) > 0.25:
            return False

        return True
    def _copy_json_khong_trung(self, source: Path, target: Path) -> Path:
        target = tao_duong_dan_khong_trung(target)
        shutil.copyfile(source, target)
        return target

    def _model_dich_mac_dinh(self, provider: str) -> str:
        if provider == "gemini":
            return "gemini-3.5-flash"
        if provider == "local":
            return "Helsinki-NLP/opus-mt-zh-vi"
        return "gpt-4.1"

    def _ten_an_toan(self, text: str) -> str:
        return "".join(ky_tu if ky_tu.isalnum() else "_" for ky_tu in text).strip("_") or "model"

    def _duong_dan_json_dich(self, wav: Path, provider: str, model: str) -> Path:
        return wav.parent / f"{wav.stem}_translation_{self._ten_an_toan(provider)}_{self._ten_an_toan(model)}_vi.json"

    def _tim_json_dich_moi_nhat(self, wav: Path) -> Path:
        cac_file = sorted(wav.parent.glob(f"{wav.stem}_translation_*_vi.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        if cac_file:
            return cac_file[0]
        return wav.parent / f"{wav.stem}_translation_vi.json"

    def _don_file_tam(self, wav: Path, keep_wav: bool) -> None:
        if keep_wav:
            return
        if wav.exists():
            wav.unlink()

    def _kiem_tra_dung(self, stop_event) -> None:
        if stop_event is not None and stop_event.is_set():
            raise RuntimeError("Pipeline Ä‘Ã£ dá»«ng theo yÃªu cáº§u.")

