"""Ghép timestamp của Whisper với chữ nhận dạng từ SenseVoice."""

from __future__ import annotations

import json
import re
import time
from dataclasses import asdict
from difflib import SequenceMatcher
from pathlib import Path

from core.models import SubtitleSegment
from core.sensevoice_transcriber import SenseVoiceTranscriber
from core.transcriber import FasterWhisperTranscriber, LogCallback, TranscriberConfig, TranscriberError, TranscriptionResult


class HybridTranscriber:
    """Whisper giữ mốc thời gian, SenseVoice cung cấp nội dung tiếng Trung."""

    def __init__(self, whisper: FasterWhisperTranscriber, sensevoice: SenseVoiceTranscriber) -> None:
        self.whisper = whisper
        self.sensevoice = sensevoice

    def transcribe(
        self,
        audio_path: Path,
        output_dir: Path,
        config: TranscriberConfig | None = None,
        log: LogCallback = None,
    ) -> TranscriptionResult:
        config = config or TranscriberConfig(recognition_engine="hybrid")
        bat_dau = time.perf_counter()

        self._ghi_log(log, "Hybrid: Whisper đang tạo timestamp.")
        whisper_config = TranscriberConfig(
            model_size=config.model_size if config.model_size != "sensevoice-small" else "medium",
            recognition_engine="whisper",
            language=config.language,
            device=config.device,
            vad_filter=config.vad_filter,
            difficult_audio_mode=config.difficult_audio_mode,
            full_dialogue_mode=config.full_dialogue_mode,
            aggressive_gap_fill=config.aggressive_gap_fill,
        )
        ket_qua_whisper = self.whisper.transcribe(audio_path, output_dir, whisper_config, log)

        self._ghi_log(log, "Hybrid: SenseVoice đang nhận dạng chữ Trung.")
        sense_config = TranscriberConfig(
            model_size="sensevoice-small",
            recognition_engine="sensevoice",
            language=config.language,
            device="cpu" if config.device == "auto" else config.device,
            vad_filter=False,
            difficult_audio_mode=config.difficult_audio_mode,
            full_dialogue_mode=config.full_dialogue_mode,
            aggressive_gap_fill=config.aggressive_gap_fill,
        )
        try:
            ket_qua_sense = self.sensevoice.transcribe(audio_path, output_dir, sense_config, log)
            segments = self._ghep_noi_dung(ket_qua_whisper.segments, ket_qua_sense.segments, config.aggressive_gap_fill)
        except Exception as loi:
            if config.device == "cuda":
                raise TranscriberError(
                    "Hybrid GPU thất bại ở bước SenseVoice. Vui lòng kiểm tra CUDA/PyTorch/FunASR "
                    f"cho SenseVoice. Lỗi gốc: {str(loi).splitlines()[0]}"
                ) from loi
            self._ghi_log(log, f"Hybrid: SenseVoice lỗi, dùng kết quả Whisper để tiếp tục xuất SRT: {str(loi).splitlines()[0]}")
            segments = self._dung_ket_qua_whisper_khi_sensevoice_loi(ket_qua_whisper.segments, loi)
        json_path = output_dir / f"{audio_path.stem}_transcription_zh.json"
        json_path.write_text(json.dumps({"segments": [asdict(segment) for segment in segments]}, ensure_ascii=False, indent=2), encoding="utf-8")

        return TranscriptionResult(
            segments=segments,
            json_path=json_path,
            elapsed_seconds=time.perf_counter() - bat_dau,
            device_used=f"hybrid:{ket_qua_whisper.device_used}+{ket_qua_sense.device_used}",
            compute_type=ket_qua_whisper.compute_type,
        )

    def _dung_ket_qua_whisper_khi_sensevoice_loi(
        self,
        whisper_segments: list[SubtitleSegment],
        loi: Exception,
    ) -> list[SubtitleSegment]:
        canh_bao = f"Hybrid: SenseVoice lỗi, đã dùng chữ Whisper. Lỗi: {str(loi).splitlines()[0]}"
        return [
            SubtitleSegment(
                index=index,
                start=doan.start,
                end=doan.end,
                original_zh=doan.original_zh,
                status=doan.status,
                warning=canh_bao,
            )
            for index, doan in enumerate(whisper_segments, start=1)
        ]

    def _ghep_noi_dung(
        self,
        whisper_segments: list[SubtitleSegment],
        sense_segments: list[SubtitleSegment],
        aggressive_gap_fill: bool,
    ) -> list[SubtitleSegment]:
        if not whisper_segments:
            return []

        sense_texts = [segment.original_zh.strip() for segment in sense_segments if segment.original_zh.strip()]
        if len(sense_texts) == len(whisper_segments):
            texts = sense_texts
            warning = "Hybrid: chữ từ SenseVoice, timestamp từ Whisper."
        else:
            texts = [segment.original_zh.strip() for segment in whisper_segments]
            warning = (
                "Hybrid: SenseVoice không khớp số segment Whisper, "
                "đã giữ chữ Whisper để tránh lệch phụ đề."
            )

        ket_qua: list[SubtitleSegment] = []
        for index, doan in enumerate(whisper_segments, start=1):
            text = texts[index - 1].strip() if index - 1 < len(texts) else doan.original_zh
            ket_qua.append(
                SubtitleSegment(
                    index=index,
                    start=doan.start,
                    end=doan.end,
                    original_zh=text or doan.original_zh,
                    status="transcribed",
                    warning=warning,
                )
            )
        if len(sense_texts) != len(whisper_segments):
            ket_qua = self._bo_sung_sensevoice_vao_khoang_trong(ket_qua, sense_segments, aggressive_gap_fill)
        return [
            SubtitleSegment(
                index=index,
                start=doan.start,
                end=doan.end,
                original_zh=doan.original_zh,
                status=doan.status,
                warning=doan.warning,
            )
            for index, doan in enumerate(sorted(ket_qua, key=lambda item: (item.start, item.end)), start=1)
        ]

    def _bo_sung_sensevoice_vao_khoang_trong(
        self,
        whisper_segments: list[SubtitleSegment],
        sense_segments: list[SubtitleSegment],
        aggressive_gap_fill: bool = True,
    ) -> list[SubtitleSegment]:
        """Chèn kết quả SenseVoice vào các khoảng trống lớn mà Whisper bỏ sót."""

        if not whisper_segments or not sense_segments:
            return whisper_segments

        ket_qua = list(whisper_segments)
        da_co = " ".join(doan.original_zh for doan in whisper_segments)
        khoang_da_dung: set[tuple[float, float]] = set()

        for sense in sense_segments:
            text = sense.original_zh.strip()
            if len(text) < 4 or text in da_co:
                continue

            khoang_trong = self._tim_khoang_trong_phu_hop(sense, whisper_segments)
            if not khoang_trong:
                continue
            if khoang_trong in khoang_da_dung:
                continue

            start, end = khoang_trong
            if self._co_chong_lan(start, end, ket_qua):
                continue
            if not aggressive_gap_fill and self._qua_giong_vung_lan_can(text, start, end, ket_qua):
                continue
            ket_qua.append(
                SubtitleSegment(
                    index=0,
                    start=start,
                    end=end,
                    original_zh=text,
                    status="transcribed",
                    warning="Hybrid: bổ sung từ SenseVoice vì Whisper bỏ sót khoảng hội thoại.",
                )
            )
            da_co += " " + text
            khoang_da_dung.add(khoang_trong)

        return ket_qua

    def _tim_khoang_trong_phu_hop(
        self,
        sense: SubtitleSegment,
        whisper_segments: list[SubtitleSegment],
    ) -> tuple[float, float] | None:
        moc = sorted(whisper_segments, key=lambda item: (item.start, item.end))
        cac_khoang: list[tuple[float, float]] = []
        for truoc, sau in zip(moc, moc[1:]):
            gap_start = float(truoc.end)
            gap_end = float(sau.start)
            if gap_end - gap_start >= 2.0:
                cac_khoang.append((gap_start, gap_end))

        sense_start = float(sense.start)
        sense_end = float(sense.end)
        for gap_start, gap_end in cac_khoang:
            overlap = min(sense_end, gap_end) - max(sense_start, gap_start)
            if overlap >= 0.6 or (sense_start <= gap_start and sense_end >= gap_end):
                start = max(gap_start, sense_start)
                end = min(gap_end, sense_end)
                if end - start < 0.8:
                    start, end = gap_start, gap_end
                return start, end
        return None

    def _co_chong_lan(self, start: float, end: float, segments: list[SubtitleSegment]) -> bool:
        for doan in segments:
            if start < float(doan.end) and end > float(doan.start):
                return True
        return False

    def _qua_giong_vung_lan_can(
        self,
        text: str,
        start: float,
        end: float,
        segments: list[SubtitleSegment],
    ) -> bool:
        """Tránh lấy nhầm câu gần đó để đắp vào khoảng trống."""

        vung_lan_can = [
            doan.original_zh
            for doan in segments
            if float(doan.end) >= start - 35 and float(doan.start) <= end + 35
        ]
        if not vung_lan_can:
            return False

        text_sach = self._rut_gon_text(text)
        for noi_dung in vung_lan_can:
            noi_dung_sach = self._rut_gon_text(noi_dung)
            if not text_sach or not noi_dung_sach:
                continue
            if text_sach in noi_dung_sach or noi_dung_sach in text_sach:
                return True
            if SequenceMatcher(None, text_sach, noi_dung_sach).ratio() >= 0.62:
                return True
        return False

    def _rut_gon_text(self, text: str) -> str:
        return re.sub(r"\s+", "", text.strip())

    def _chia_text_theo_so_moc(self, text: str, so_moc: int) -> list[str]:
        cau = [item.strip() for item in re.split(r"(?<=[\u3002\uff01\uff1f!?])", text) if item.strip()]
        if len(cau) == so_moc:
            return cau
        if not text:
            return [""] * so_moc

        do_dai = max(1, len(text) // so_moc)
        ket_qua = [text[i * do_dai : (i + 1) * do_dai] for i in range(so_moc - 1)]
        ket_qua.append(text[(so_moc - 1) * do_dai :])
        return ket_qua

    def _ghi_log(self, log: LogCallback, noi_dung: str) -> None:
        if log:
            log(noi_dung)
