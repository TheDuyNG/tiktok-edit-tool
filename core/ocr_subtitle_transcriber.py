"""Nhan dang phu de tieng Trung co san tren video bang OCR."""

from __future__ import annotations

import json
import hashlib
import os
import re
import shutil
import site
import sys
import sysconfig
import time
from dataclasses import asdict
from difflib import SequenceMatcher
from pathlib import Path

from core.ffmpeg_service import chay_lenh, lay_thoi_luong_video, tim_ffmpeg
from core.models import SubtitleSegment
from core.transcriber import LogCallback, TranscriberConfig, TranscriberError, TranscriptionResult


class OcrSubtitleTranscriber:
    """Engine OCR doc lap, chi dung khi video co phu de Trung dot cung."""

    SMART_SIGNATURE_SIZE = (64, 36)
    SMART_SIMILARITY_THRESHOLD = 0.8
    SMART_MAX_REUSE_FRAMES = 2
    SMART_WARMUP_FRAMES = 200
    SMART_MIN_SKIP_RATIO = 0.2

    def __init__(self) -> None:
        self._ocr = None
        self._ocr_use_gpu: bool | None = None
        self._dll_handles: list[object] = []

    def release_model(self) -> None:
        self._ocr = None
        self._ocr_use_gpu = None

    def transcribe(
        self,
        video_path: Path,
        output_dir: Path,
        config: TranscriberConfig | None = None,
        log: LogCallback = None,
    ) -> TranscriptionResult:
        """Quet vung 1/4 duoi video, gom chu trung va luu JSON UTF-8."""

        config = config or TranscriberConfig(recognition_engine="ocr_subtitle")
        if not video_path.exists():
            raise TranscriberError("Khong tim thay video de OCR phu de.")

        bat_dau = time.perf_counter()
        output_dir.mkdir(parents=True, exist_ok=True)
        frame_dir = output_dir / f"{video_path.stem}_ocr_frames"
        if frame_dir.exists():
            shutil.rmtree(frame_dir)
        frame_dir.mkdir(parents=True, exist_ok=True)

        fps = max(0.5, float(config.ocr_fps or 3.0))
        thoi_luong = lay_thoi_luong_video(video_path)
        self._ghi_log(
            log,
        f"OCR: trich frame vung phu de x={config.ocr_crop_left:.2f}-{config.ocr_crop_right:.2f}, "
        f"y={config.ocr_crop_top:.2f}-{config.ocr_crop_bottom:.2f}, {fps:.1f} fps.",
        )
        self._trich_frame(video_path, frame_dir, fps, config)

        ocr = self._lay_ocr(config, log)
        frame_paths = sorted(frame_dir.glob("*.png"))
        if not frame_paths:
            raise TranscriberError("OCR khong trich duoc frame nao tu video.")

        ket_qua_frame, thong_ke_smart = self._doc_cac_frame_thong_minh(ocr, frame_paths, fps, log)
        self._ghi_log(
            log,
            "OCR smart-frame: "
            f"goi OCR {thong_ke_smart['ocr_calls']} frame, "
            f"dung cache {thong_ke_smart['cache_hits']} frame, "
            f"bo qua gan giong {thong_ke_smart['similar_reuse']} frame.",
        )

        ket_qua_frame = self._bo_cum_lap_cuoi_dong(ket_qua_frame, log)
        segments = self._gom_frame_thanh_segment(ket_qua_frame, thoi_luong, fps)
        if not segments:
            raise TranscriberError(
                "OCR khong doc duoc phu de Trung nao. Hay kiem tra video co phu de cung va vung crop 1/4 duoi."
            )

        json_path = output_dir / f"{video_path.stem}_ocr_transcription_zh.json"
        json_path.write_text(
            json.dumps({"segments": [asdict(s) for s in segments]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return TranscriptionResult(
            segments=segments,
            json_path=json_path,
            elapsed_seconds=time.perf_counter() - bat_dau,
            device_used="ocr_subtitle_gpu" if self._ocr_use_gpu else "ocr_subtitle_cpu",
            compute_type=getattr(ocr, "engine_name", "ocr"),
        )

    def _lay_ocr(self, config: TranscriberConfig, log: LogCallback):
        if self._ocr is not None:
            return self._ocr

        if config.ocr_use_gpu:
            try:
                self._ocr = self._lay_rapidocr(log)
                self._ocr_use_gpu = True
                return self._ocr
            except Exception as loi:
                self._ghi_log(log, f"OCR RapidOCR/DirectML loi, thu PaddleOCR: {loi}")

        self._dat_cache_paddle()
        self._them_duong_dan_paddle_dll()
        sys.modules.pop("paddle", None)
        try:
            from paddleocr import PaddleOCR
        except Exception as loi:
            sys.modules.pop("paddle", None)
            raise TranscriberError(
                "Khong tai duoc PaddleOCR/Paddle de doc phu de tren video. "
                f"Loi goc: {loi}"
            ) from loi

        use_gpu = bool(config.ocr_use_gpu)
        if use_gpu and not self._paddle_co_cuda(log):
            self._ghi_log(log, "OCR: Paddle trong Python hien tai chua ho tro CUDA, tu chuyen OCR sang CPU.")
            use_gpu = False

        self._ghi_log(log, f"OCR: dang tai PaddleOCR tieng Trung tren {'GPU' if use_gpu else 'CPU'}.")
        try:
            self._ocr = self._tao_paddle_ocr(PaddleOCR, use_gpu)
            self._ocr_use_gpu = use_gpu
        except Exception as loi:
            if use_gpu:
                self._ghi_log(log, f"OCR GPU loi, tu chuyen sang CPU: {loi}")
                self._ocr = self._tao_paddle_ocr(PaddleOCR, False)
                self._ocr_use_gpu = False
            else:
                raise TranscriberError(f"Khong tai duoc PaddleOCR: {loi}") from loi
        return self._ocr

    def _lay_rapidocr(self, log: LogCallback):
        try:
            import onnxruntime as ort
            from rapidocr_onnxruntime import RapidOCR
        except Exception as loi:
            raise TranscriberError(f"Chua tai duoc RapidOCR/ONNXRuntime: {loi}") from loi

        providers = list(ort.get_available_providers())
        self._ghi_log(log, f"OCR: RapidOCR providers: {providers}")
        if "DmlExecutionProvider" in providers:
            self._ghi_log(log, "OCR: dang tai RapidOCR bang DirectML GPU.")
            ocr = RapidOCR()
            self._bat_directml_cho_rapidocr(ocr)
            return RapidOcrAdapter(
                ocr,
                providers,
            )
        else:
            self._ghi_log(log, "OCR: khong co DirectML, tam dung RapidOCR tren CPU de doi chieu.")
        return RapidOcrAdapter(RapidOCR(), providers)

    def _bat_directml_cho_rapidocr(self, ocr) -> None:
        """Chuyen cac ONNX session cua RapidOCR 1.x sang DirectML."""

        da_chuyen = 0
        for ten_thanh_phan in ("text_detector", "text_cls", "text_recognizer"):
            thanh_phan = getattr(ocr, ten_thanh_phan, None)
            infer = getattr(thanh_phan, "infer", None) or getattr(thanh_phan, "session", None)
            session = getattr(infer, "session", None)
            if session is None or not hasattr(session, "set_providers"):
                continue
            session.set_providers(["DmlExecutionProvider", "CPUExecutionProvider"])
            if "DmlExecutionProvider" in session.get_providers():
                da_chuyen += 1

        if da_chuyen == 0:
            raise TranscriberError("RapidOCR khong tao duoc ONNX session DirectML.")

    def _paddle_co_cuda(self, log: LogCallback) -> bool:
        try:
            import paddle

            co_cuda = bool(paddle.device.is_compiled_with_cuda())
            if co_cuda:
                self._ghi_log(log, "OCR: Paddle co CUDA, se uu tien GPU.")
            return co_cuda
        except Exception as loi:
            self._ghi_log(log, f"OCR: khong kiem tra duoc CUDA cua Paddle, se chay CPU: {loi}")
            return False

    def _tao_paddle_ocr(self, PaddleOCR, use_gpu: bool):
        cac_cau_hinh = [
            # PaddleOCR 3.x
            {
                "lang": "ch",
                "use_textline_orientation": True,
                "use_doc_orientation_classify": False,
                "use_doc_unwarping": False,
                "device": "gpu" if use_gpu else "cpu",
                "enable_mkldnn": False,
            },
            # PaddleOCR 2.x
            {"use_angle_cls": True, "lang": "ch", "show_log": False, "enable_mkldnn": False, "use_gpu": use_gpu},
            {"use_angle_cls": True, "lang": "ch", "show_log": False, "use_gpu": use_gpu},
            {"use_angle_cls": True, "lang": "ch", "enable_mkldnn": False, "use_gpu": use_gpu},
            {"use_angle_cls": True, "lang": "ch", "use_gpu": use_gpu},
            {"use_angle_cls": True, "lang": "ch"},
        ]
        loi_cuoi: Exception | None = None
        for cau_hinh in cac_cau_hinh:
            try:
                return PaddleOCR(**cau_hinh)
            except (TypeError, ValueError) as loi:
                loi_cuoi = loi
                continue
        if loi_cuoi:
            raise loi_cuoi
        raise TranscriberError("Khong khoi tao duoc PaddleOCR.")

    def _dat_cache_paddle(self) -> None:
        cache_dir = Path(__file__).resolve().parents[1] / ".cache" / "paddle"
        cache_dir.mkdir(parents=True, exist_ok=True)
        os.environ["PADDLE_HOME"] = str(cache_dir)
        os.environ["PPNLP_HOME"] = str(cache_dir / "paddlenlp")
        os.environ["XDG_CACHE_HOME"] = str(cache_dir)
        os.environ["HOME"] = str(cache_dir)
        os.environ["USERPROFILE"] = str(cache_dir)
        os.environ["FLAGS_use_mkldnn"] = "0"
        os.environ["FLAGS_use_onednn"] = "0"
        os.environ["FLAGS_use_pir_api"] = "0"

    def _them_duong_dan_paddle_dll(self) -> None:
        if os.name != "nt":
            return

        cac_goc: list[Path] = []
        for key in ("purelib", "platlib"):
            duong_dan = sysconfig.get_paths().get(key)
            if duong_dan:
                cac_goc.append(Path(duong_dan))
        try:
            cac_goc.append(Path(site.getusersitepackages()))
            cac_goc.extend(Path(p) for p in site.getsitepackages())
        except Exception:
            pass

        cac_thu_muc: list[Path] = []
        for goc in dict.fromkeys(cac_goc):
            nvidia = goc / "nvidia"
            cac_thu_muc.extend(
                [
                    nvidia / "cuda_runtime" / "bin",
                    nvidia / "cuda_nvrtc" / "bin",
                    nvidia / "nvjitlink" / "bin",
                    nvidia / "cublas" / "bin",
                    nvidia / "cudnn" / "bin",
                    nvidia / "cufft" / "bin",
                    nvidia / "curand" / "bin",
                    nvidia / "cusolver" / "bin",
                    nvidia / "cusparse" / "bin",
                ]
            )

        cac_thu_muc_hop_le = [thu_muc for thu_muc in dict.fromkeys(cac_thu_muc) if thu_muc.exists()]
        for thu_muc in dict.fromkeys(cac_thu_muc):
            if not thu_muc.exists():
                continue
            try:
                self._dll_handles.append(os.add_dll_directory(str(thu_muc)))
            except (OSError, AttributeError):
                pass
        if cac_thu_muc_hop_le:
            os.environ["PATH"] = f"{';'.join(str(p) for p in cac_thu_muc_hop_le)};{os.environ.get('PATH', '')}"

    def _trich_frame(self, video_path: Path, frame_dir: Path, fps: float, config: TranscriberConfig) -> None:
        ffmpeg = tim_ffmpeg()
        left = min(0.95, max(0.0, float(config.ocr_crop_left)))
        top = min(0.95, max(0.0, float(config.ocr_crop_top)))
        right = min(1.0, max(left + 0.05, float(config.ocr_crop_right)))
        bottom = min(1.0, max(top + 0.05, float(config.ocr_crop_bottom)))
        crop_w = right - left
        crop_h = bottom - top
        vf = f"fps={fps},crop=iw*{crop_w}:ih*{crop_h}:iw*{left}:ih*{top}"
        lenh = [ffmpeg, "-y", "-i", str(video_path), "-vf", vf, str(frame_dir / "%06d.png")]
        ket_qua = chay_lenh(lenh, timeout=900)
        if ket_qua.returncode != 0:
            raise TranscriberError(f"Khong trich duoc frame OCR: {ket_qua.stderr[-500:]}")

    def _doc_frame(self, ocr, frame: Path) -> str:
        if hasattr(ocr, "doc_frame"):
            return ocr.doc_frame(frame, self._lam_sach_text, self._co_chu_trung)

        try:
            ket_qua = ocr.ocr(str(frame), cls=True)
        except TypeError:
            ket_qua = ocr.ocr(str(frame))
        except Exception:
            return ""

        cac_dong: list[str] = []
        for dong in self._flatten_ocr_result(ket_qua):
            if not isinstance(dong, (list, tuple)) or len(dong) < 2:
                continue
            thong_tin = dong[1]
            if isinstance(thong_tin, (list, tuple)) and thong_tin:
                text = str(thong_tin[0]).strip()
                score = float(thong_tin[1]) if len(thong_tin) > 1 else 1.0
                if score >= 0.45 and self._co_chu_trung(text):
                    cac_dong.append(text)
        return self._lam_sach_text(" ".join(cac_dong))

    def _doc_cac_frame_thong_minh(
        self,
        ocr,
        frame_paths: list[Path],
        fps: float,
        log: LogCallback = None,
    ) -> tuple[list[tuple[float, str]], dict[str, int]]:
        ket_qua_frame: list[tuple[float, str]] = []
        cache_text: dict[str, str] = {}
        chu_ky_truoc: bytes | None = None
        text_truoc = ""
        so_frame_dung_lai_lien_tiep = 0
        lan_log = time.perf_counter()
        smart_da_tat = False
        thong_ke = {"ocr_calls": 0, "cache_hits": 0, "similar_reuse": 0, "smart_disabled": 0}

        for vi_tri, frame in enumerate(frame_paths):
            thoi_diem = vi_tri / fps
            chu_ky = None if smart_da_tat else self._tao_chu_ky_anh(frame)
            khoa_cache = hashlib.sha1(chu_ky).hexdigest() if chu_ky is not None else ""
            text: str

            if smart_da_tat:
                text = self._doc_frame(ocr, frame)
                thong_ke["ocr_calls"] += 1
            elif khoa_cache and khoa_cache in cache_text:
                text = cache_text[khoa_cache]
                thong_ke["cache_hits"] += 1
                so_frame_dung_lai_lien_tiep = 0
            elif (
                chu_ky is not None
                and chu_ky_truoc is not None
                and so_frame_dung_lai_lien_tiep < self.SMART_MAX_REUSE_FRAMES
                and self._anh_gan_giong(chu_ky_truoc, chu_ky)
            ):
                text = text_truoc
                if khoa_cache:
                    cache_text[khoa_cache] = text
                thong_ke["similar_reuse"] += 1
                so_frame_dung_lai_lien_tiep += 1
            else:
                text = self._doc_frame(ocr, frame)
                if khoa_cache:
                    cache_text[khoa_cache] = text
                thong_ke["ocr_calls"] += 1
                so_frame_dung_lai_lien_tiep = 0

            if text:
                ket_qua_frame.append((thoi_diem, text))
            if chu_ky is not None:
                chu_ky_truoc = chu_ky
            text_truoc = text

            da_xu_ly = vi_tri + 1
            if (
                not smart_da_tat
                and da_xu_ly >= self.SMART_WARMUP_FRAMES
                and thong_ke["cache_hits"] + thong_ke["similar_reuse"] < int(da_xu_ly * self.SMART_MIN_SKIP_RATIO)
            ):
                smart_da_tat = True
                thong_ke["smart_disabled"] = 1
                self._ghi_log(
                    log,
                    "OCR smart-frame: ty le bo qua thap, tu tat so anh cho cac frame con lai.",
                )

            if vi_tri == 0 or vi_tri % 100 == 0 or time.perf_counter() - lan_log >= 30:
                self._ghi_log(
                    log,
                    f"OCR van chay: {vi_tri + 1}/{len(frame_paths)} frame "
                    f"(goi OCR {thong_ke['ocr_calls']}, cache {thong_ke['cache_hits']}, bo qua {thong_ke['similar_reuse']}).",
                )
                lan_log = time.perf_counter()

        return ket_qua_frame, thong_ke

    def _tao_chu_ky_anh(self, frame: Path) -> bytes | None:
        try:
            from PIL import Image
        except Exception:
            return None

        try:
            resampling = getattr(getattr(Image, "Resampling", Image), "BILINEAR")
            with Image.open(frame) as image:
                image = image.convert("L").resize(self.SMART_SIGNATURE_SIZE, resampling)
                return image.tobytes()
        except Exception:
            return None

    def _anh_gan_giong(self, a: bytes, b: bytes) -> bool:
        if len(a) != len(b) or not a:
            return False
        tong_lech = sum(abs(x - y) for x, y in zip(a, b))
        lech_trung_binh = tong_lech / len(a)
        return lech_trung_binh <= self.SMART_SIMILARITY_THRESHOLD

    def _flatten_ocr_result(self, ket_qua):
        if not ket_qua:
            return []
        if len(ket_qua) == 1 and isinstance(ket_qua[0], list):
            return ket_qua[0]
        return ket_qua

    def _gom_frame_thanh_segment(
        self,
        ket_qua_frame: list[tuple[float, str]],
        thoi_luong: float,
        fps: float,
    ) -> list[SubtitleSegment]:
        segments: list[SubtitleSegment] = []
        text_hien_tai = ""
        start = 0.0
        end = 0.0

        for thoi_diem, text in ket_qua_frame:
            if not text:
                continue
            if not text_hien_tai:
                text_hien_tai = text
                start = thoi_diem
                end = min(thoi_luong, thoi_diem + 1 / fps)
                continue
            if self._giong_nhau(text_hien_tai, text):
                end = min(thoi_luong, thoi_diem + 1 / fps)
                if len(text) > len(text_hien_tai):
                    text_hien_tai = text
                continue
            self._them_segment(segments, start, end, text_hien_tai)
            text_hien_tai = text
            start = thoi_diem
            end = min(thoi_luong, thoi_diem + 1 / fps)

        if text_hien_tai:
            self._them_segment(segments, start, end, text_hien_tai)

        return [
            SubtitleSegment(index=i, start=s.start, end=s.end, original_zh=s.original_zh, status="ocr")
            for i, s in enumerate(segments, start=1)
        ]

    def _bo_cum_lap_cuoi_dong(
        self,
        ket_qua_frame: list[tuple[float, str]],
        log: LogCallback = None,
    ) -> list[tuple[float, str]]:
        if len(ket_qua_frame) < 8:
            return ket_qua_frame

        dem: dict[str, int] = {}
        for _thoi_diem, text in ket_qua_frame:
            parts = text.split()
            if len(parts) < 2:
                continue
            ung_vien = parts[-1].strip()
            if 2 <= len(ung_vien) <= 8 and self._co_chu_trung(ung_vien):
                dem[ung_vien] = dem.get(ung_vien, 0) + 1

        nguong = max(5, int(len(ket_qua_frame) * 0.2))
        cum_bo = {cum for cum, so_lan in dem.items() if so_lan >= nguong}
        if not cum_bo:
            return ket_qua_frame

        self._ghi_log(log, f"OCR: tu bo cum lap cuoi dong: {', '.join(sorted(cum_bo))}")
        ket_qua: list[tuple[float, str]] = []
        for thoi_diem, text in ket_qua_frame:
            moi = self._bo_watermark_cuoi_text(text, cum_bo)
            if moi:
                ket_qua.append((thoi_diem, self._lam_sach_text(moi)))
        return ket_qua

    def _bo_watermark_cuoi_text(self, text: str, cum_bo: set[str]) -> str:
        parts = text.split()
        if not parts:
            return ""

        while parts and self._la_token_watermark(parts[-1], cum_bo):
            parts.pop()
        return " ".join(parts).strip()

    def _la_token_watermark(self, token: str, cum_bo: set[str]) -> bool:
        token = token.strip()
        if not token or len(token) > 10:
            return False
        for cum in cum_bo:
            if token == cum or token in cum or cum in token:
                return True
            if SequenceMatcher(None, token, cum).ratio() >= 0.55:
                return True
            if "动漫" in token and "动漫" in cum:
                return True
        return False

    def _them_segment(self, segments: list[SubtitleSegment], start: float, end: float, text: str) -> None:
        text = self._lam_sach_text(text)
        if not text or end <= start:
            return
        if segments and self._giong_nhau(segments[-1].original_zh, text) and start - segments[-1].end <= 0.8:
            segments[-1].end = end
            return
        segments.append(SubtitleSegment(index=len(segments) + 1, start=start, end=end, original_zh=text, status="ocr"))

    def _lam_sach_text(self, text: str) -> str:
        text = re.sub(r"\s+", " ", text).strip()
        text = re.sub(r"[|_~`]+", "", text)
        return text.strip()

    def _co_chu_trung(self, text: str) -> bool:
        return bool(re.search(r"[\u4e00-\u9fff]", text))

    def _giong_nhau(self, a: str, b: str) -> bool:
        a = re.sub(r"\s+", "", a)
        b = re.sub(r"\s+", "", b)
        if not a or not b:
            return False
        if a in b or b in a:
            return True
        return SequenceMatcher(None, a, b).ratio() >= 0.82

    def _ghi_log(self, log: LogCallback, noi_dung: str) -> None:
        if log:
            log(noi_dung)


class RapidOcrAdapter:
    """Chuyen ket qua RapidOCR ve dang text cho pipeline hien co."""

    engine_name = "rapidocr-directml"

    def __init__(self, ocr, providers: list[str]) -> None:
        self.ocr = ocr
        self.providers = providers

    def doc_frame(self, frame: Path, lam_sach_text, co_chu_trung) -> str:
        try:
            ket_qua, _elapsed = self.ocr(str(frame), use_det=True, use_cls=False, use_rec=True)
        except Exception:
            return ""

        cac_dong: list[str] = []
        for dong in ket_qua or []:
            if not isinstance(dong, (list, tuple)) or len(dong) < 2:
                continue
            text = str(dong[1]).strip()
            score = 1.0
            if len(dong) > 2:
                try:
                    score = float(dong[2])
                except (TypeError, ValueError):
                    score = 1.0
            if score >= 0.45 and co_chu_trung(text):
                cac_dong.append(text)
        return lam_sach_text(" ".join(cac_dong))
