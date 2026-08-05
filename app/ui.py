"""Giao diện Tkinter cho SRT Maker."""

from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable

from app.settings import AppSettings, luu_cau_hinh, tai_cau_hinh
from app.ocr_region_selector import chon_vung_ocr
from app.worker import PipelineConfig, PipelineResult, SrtMakerWorker
from core.ffmpeg_service import lay_thoi_luong_video
from core.transcriber import TranscriptionResult
from core.translation.base import TranslationResult


class SrtMakerApp(tk.Tk):
    """Cửa sổ chính của ứng dụng."""

    def __init__(self) -> None:
        super().__init__()
        self.title("SRT Maker - Trung sang Việt")
        self.geometry("1280x900")
        self.minsize(1080, 760)

        cau_hinh = tai_cau_hinh()
        self.cau_hinh = cau_hinh
        self.worker = SrtMakerWorker()
        self.hang_doi_ui: queue.Queue[tuple[str, object]] = queue.Queue()
        self.pipeline_stop_event = threading.Event()
        self.hang_doi_video: list[dict[str, object]] = []
        self.ma_hang_doi_tiep_theo = 1
        self.ma_item_hang_doi_dang_chon: int | None = None
        self.dang_chay_hang_doi = False
        self.dung_sau_file_hien_tai = False
        self.stop_event_hien_tai: threading.Event | None = None
        self.ma_item_dang_chay: int | None = None

        self.duong_dan_video = tk.StringVar()
        self.thu_muc_dau_ra = tk.StringVar(value=str(Path(cau_hinh.thu_muc_output).resolve()))
        self.duong_dan_wav = tk.StringVar(value="Chưa tạo WAV")
        self.duong_dan_srt_zh = tk.StringVar(value="Chưa xuất SRT tiếng Trung")
        self.duong_dan_srt_vi = tk.StringVar(value="Chưa xuất SRT tiếng Trung")
        self.recognition_engine = tk.StringVar(value=cau_hinh.recognition_engine)
        self.recognition_mode = tk.StringVar(value="ocr" if cau_hinh.recognition_engine == "ocr_subtitle" else "audio")
        self.model_size = tk.StringVar(value=cau_hinh.model_size)
        self.device = tk.StringVar(value=cau_hinh.device)
        self.language = tk.StringVar(value=cau_hinh.language)
        self.vad_filter = tk.BooleanVar(value=cau_hinh.vad_filter)
        self.difficult_audio_mode = tk.BooleanVar(value=cau_hinh.difficult_audio_mode)
        self.full_dialogue_mode = tk.BooleanVar(value=cau_hinh.full_dialogue_mode)
        self.aggressive_gap_fill = tk.BooleanVar(value=cau_hinh.aggressive_gap_fill)
        self.ocr_fps = tk.StringVar(value=str(cau_hinh.ocr_fps))
        self.ocr_crop_left = tk.StringVar(value=str(cau_hinh.ocr_crop_left))
        self.ocr_crop_top = tk.StringVar(value=str(cau_hinh.ocr_crop_top))
        self.ocr_crop_right = tk.StringVar(value=str(cau_hinh.ocr_crop_right))
        self.ocr_crop_bottom = tk.StringVar(value=str(cau_hinh.ocr_crop_bottom))
        self.ocr_use_gpu = tk.BooleanVar(value=cau_hinh.ocr_use_gpu)
        self.translation_provider = tk.StringVar(value=cau_hinh.translation_provider)
        self.translation_model = tk.StringVar(value=cau_hinh.translation_model)
        self.translation_quality = tk.StringVar(value=cau_hinh.translation_quality)
        self.translation_api_key = tk.StringVar(value=cau_hinh.translation_api_key)
        self.translation_api_key_moi = tk.StringVar()
        self.api_key_visible = tk.BooleanVar(value=False)
        self.keep_wav = tk.BooleanVar(value=cau_hinh.keep_wav)
        self.shutdown_when_done = tk.BooleanVar(value=cau_hinh.shutdown_when_done)
        self.ten_buoc_hien_tai = tk.StringVar(value="Chưa chạy")

        self._tao_giao_dien()
        self._dong_bo_giao_dien_nhan_dang()
        self.after(100, self._doc_hang_doi_ui)

    def _tao_giao_dien(self) -> None:
        khung_chinh = ttk.Frame(self, padding=18)
        khung_chinh.pack(fill=tk.BOTH, expand=True)
        khung_chinh.columnconfigure(0, weight=1)
        khung_chinh.rowconfigure(5, weight=3)
        khung_chinh.rowconfigure(7, weight=2)
        khung_chinh.rowconfigure(8, weight=2)

        ttk.Label(
            khung_chinh,
            text="SRT Maker - tạo phụ đề Trung / Việt",
            font=("Segoe UI", 18, "bold"),
        ).grid(row=0, column=0, sticky="w", pady=(0, 12))

        self._tao_thanh_chay_chinh(khung_chinh)
        self._tao_vung_chon_file(khung_chinh, 2, "Nơi lưu SRT tiếng Trung", self.thu_muc_dau_ra, self._chon_thu_muc_dau_ra)
        self._tao_vung_srt(khung_chinh)
        self._tao_vung_cau_hinh_nhan_dang(khung_chinh)
        self._tao_vung_hang_doi(khung_chinh)
        self._tao_tien_trinh(khung_chinh)
        self._tao_bang_xem_truoc(khung_chinh)
        self._tao_vung_log(khung_chinh)

        self._ghi_log("Ứng dụng đã sẵn sàng. Bấm Bắt đầu để tạo SRT.")
        self.after(500, self._ghi_log_moi_truong_nen)

    def _tao_thanh_chay_chinh(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Chạy pipeline")
        khung.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        khung.columnconfigure(5, weight=1)

        self.nut_bat_dau = ttk.Button(khung, text="Bắt đầu", command=self._bat_dau_pipeline)
        self.nut_bat_dau.grid(row=0, column=0, padx=10, pady=10)

        self.nut_dung = ttk.Button(khung, text="Dừng", command=self._dung_pipeline, state=tk.DISABLED)
        self.nut_dung.grid(row=0, column=1, padx=(0, 10), pady=10)

        ttk.Checkbutton(khung, text="Giữ WAV", variable=self.keep_wav).grid(row=0, column=2, padx=(0, 10), pady=10)
        ttk.Checkbutton(khung, text="Tắt máy khi xong hết hàng chờ", variable=self.shutdown_when_done).grid(
            row=0,
            column=3,
            padx=(0, 10),
            pady=10,
        )
        ttk.Button(khung, text="Mở thư mục kết quả", command=self._mo_thu_muc_ket_qua).grid(
            row=0,
            column=4,
            padx=(0, 10),
            pady=10,
        )
        ttk.Button(khung, text="Lưu cấu hình", command=self._luu_cau_hinh_hien_tai).grid(
            row=0,
            column=5,
            padx=(0, 10),
            pady=10,
        )
        ttk.Button(khung, text="Thoát", command=self.destroy).grid(row=0, column=6, padx=(0, 10), pady=10)

    def _tao_vung_chon_file(
        self,
        cha: ttk.Frame,
        dong: int,
        nhan: str,
        bien: tk.StringVar,
        lenh_chon: Callable[[], None],
    ) -> None:
        khung = ttk.LabelFrame(cha, text=nhan)
        khung.grid(row=dong, column=0, sticky="ew", pady=(0, 8))
        khung.columnconfigure(0, weight=1)

        ttk.Entry(khung, textvariable=bien).grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        ttk.Button(khung, text="Chọn nơi lưu", command=lenh_chon).grid(
            row=0,
            column=1,
            padx=(0, 10),
            pady=10,
        )

    def _tao_vung_wav(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="File WAV đã tách")
        khung.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        khung.columnconfigure(0, weight=1)
        ttk.Entry(khung, textvariable=self.duong_dan_wav, state="readonly").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=10,
        )

    def _tao_vung_srt(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Kết quả cuối cùng - SRT tiếng Trung")
        khung.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        khung.columnconfigure(0, weight=1)
        ttk.Entry(khung, textvariable=self.duong_dan_srt_vi, state="readonly").grid(
            row=0,
            column=0,
            sticky="ew",
            padx=10,
            pady=10,
        )

    def _tao_vung_cau_hinh_nhan_dang(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Cấu hình nhận dạng")
        khung.grid(row=4, column=0, sticky="ew", pady=(0, 8))
        khung.columnconfigure(0, weight=1)
        khung.columnconfigure(1, weight=1)

        self.nhan_che_do_nhan_dang = ttk.Label(
            khung,
            text="",
            font=("Segoe UI", 10, "bold"),
            anchor="center",
        )
        self.nhan_che_do_nhan_dang.grid(row=0, column=0, columnspan=2, sticky="ew", padx=10, pady=(10, 6))

        self.khung_audio_mode = ttk.LabelFrame(khung, text="1. Whisper / Hybrid - nhận dạng từ âm thanh")
        self.khung_audio_mode.grid(row=1, column=0, sticky="nsew", padx=(10, 6), pady=(0, 10))
        self.khung_audio_mode.columnconfigure(1, weight=1)
        self.khung_audio_mode.columnconfigure(3, weight=1)

        ttk.Radiobutton(
            self.khung_audio_mode,
            text="DÙNG ÂM THANH",
            variable=self.recognition_mode,
            value="audio",
            command=self._doi_che_do_nhan_dang,
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 4))
        ttk.Label(
            self.khung_audio_mode,
            text="Tách WAV rồi nhận dạng lời nói bằng Whisper/SenseVoice/Hybrid.",
            wraplength=500,
            justify="left",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))

        self.audio_mode_widgets: list[tk.Widget] = []

        ttk.Label(self.khung_audio_mode, text="Engine").grid(row=2, column=0, sticky="w", padx=(10, 6), pady=6)
        self.o_recognition_engine = ttk.Combobox(
            self.khung_audio_mode,
            textvariable=self.recognition_engine,
            values=("whisper", "sensevoice", "hybrid"),
            state="readonly",
        )
        self.o_recognition_engine.grid(row=2, column=1, sticky="ew", padx=(0, 12), pady=6)

        ttk.Label(self.khung_audio_mode, text="Model").grid(row=2, column=2, sticky="w", padx=(0, 6), pady=6)
        self.o_model_size = ttk.Combobox(
            self.khung_audio_mode,
            textvariable=self.model_size,
            values=("small", "medium", "large-v3", "sensevoice-small"),
            state="readonly",
        )
        self.o_model_size.grid(row=2, column=3, sticky="ew", padx=(0, 10), pady=6)

        ttk.Label(self.khung_audio_mode, text="Thiết bị").grid(row=3, column=0, sticky="w", padx=(10, 6), pady=6)
        self.o_device = ttk.Combobox(
            self.khung_audio_mode,
            textvariable=self.device,
            values=("auto", "cuda", "cpu"),
            state="readonly",
        )
        self.o_device.grid(row=3, column=1, sticky="ew", padx=(0, 12), pady=6)

        ttk.Label(self.khung_audio_mode, text="Ngôn ngữ").grid(row=3, column=2, sticky="w", padx=(0, 6), pady=6)
        self.o_language = ttk.Combobox(
            self.khung_audio_mode,
            textvariable=self.language,
            values=("zh", "auto"),
            state="readonly",
        )
        self.o_language.grid(row=3, column=3, sticky="ew", padx=(0, 10), pady=6)

        self.o_vad_filter = ttk.Checkbutton(self.khung_audio_mode, text="Bật VAD", variable=self.vad_filter)
        self.o_vad_filter.grid(row=4, column=0, sticky="w", padx=10, pady=(6, 10))
        self.o_difficult_audio_mode = ttk.Checkbutton(
            self.khung_audio_mode,
            text="Âm thanh khó / nhiều nhạc nền",
            variable=self.difficult_audio_mode,
        )
        self.o_difficult_audio_mode.grid(row=4, column=1, columnspan=2, sticky="w", padx=(0, 10), pady=(6, 10))
        self.o_full_dialogue_mode = ttk.Checkbutton(
            self.khung_audio_mode,
            text="Nhận dạng toàn bộ hội thoại",
            variable=self.full_dialogue_mode,
        )
        self.o_full_dialogue_mode.grid(row=5, column=0, columnspan=2, sticky="w", padx=10, pady=(0, 10))
        self.o_aggressive_gap_fill = ttk.Checkbutton(
            self.khung_audio_mode,
            text="Ghép hội thoại tối đa",
            variable=self.aggressive_gap_fill,
        )
        self.o_aggressive_gap_fill.grid(row=5, column=2, columnspan=2, sticky="w", padx=(0, 10), pady=(0, 10))
        self.audio_mode_widgets.extend(
            [
                self.o_recognition_engine,
                self.o_model_size,
                self.o_device,
                self.o_language,
                self.o_vad_filter,
                self.o_difficult_audio_mode,
                self.o_full_dialogue_mode,
                self.o_aggressive_gap_fill,
            ]
        )

        self.khung_ocr_mode = ttk.LabelFrame(khung, text="2. OCR - đọc phụ đề đã có trên hình video")
        self.khung_ocr_mode.grid(row=1, column=1, sticky="nsew", padx=(6, 10), pady=(0, 10))
        self.khung_ocr_mode.columnconfigure(1, weight=1)
        self.khung_ocr_mode.columnconfigure(3, weight=1)

        ttk.Radiobutton(
            self.khung_ocr_mode,
            text="DÙNG OCR VIDEO",
            variable=self.recognition_mode,
            value="ocr",
            command=self._doi_che_do_nhan_dang,
        ).grid(row=0, column=0, columnspan=4, sticky="w", padx=10, pady=(10, 4))
        ttk.Label(
            self.khung_ocr_mode,
            text="Đọc chữ Trung trong vùng crop trên khung hình video.",
            wraplength=500,
            justify="left",
            foreground="#555555",
        ).grid(row=1, column=0, columnspan=4, sticky="ew", padx=10, pady=(0, 10))

        self.ocr_mode_widgets: list[tk.Widget] = []

        ttk.Label(self.khung_ocr_mode, text="OCR fps").grid(row=2, column=0, sticky="w", padx=(10, 6), pady=6)
        self.o_ocr_fps = ttk.Entry(self.khung_ocr_mode, textvariable=self.ocr_fps, width=8)
        self.o_ocr_fps.grid(row=2, column=1, sticky="w", padx=(0, 12), pady=6)
        self.o_ocr_use_gpu = ttk.Checkbutton(self.khung_ocr_mode, text="OCR dùng GPU", variable=self.ocr_use_gpu)
        self.o_ocr_use_gpu.grid(row=2, column=2, columnspan=2, sticky="w", padx=(0, 10), pady=6)

        ttk.Label(self.khung_ocr_mode, text="Crop trên").grid(row=3, column=0, sticky="w", padx=(10, 6), pady=6)
        self.o_ocr_crop_top = ttk.Entry(self.khung_ocr_mode, textvariable=self.ocr_crop_top, width=8)
        self.o_ocr_crop_top.grid(row=3, column=1, sticky="w", padx=(0, 12), pady=6)
        ttk.Label(self.khung_ocr_mode, text="dưới").grid(row=3, column=2, sticky="w", padx=(0, 6), pady=6)
        self.o_ocr_crop_bottom = ttk.Entry(self.khung_ocr_mode, textvariable=self.ocr_crop_bottom, width=8)
        self.o_ocr_crop_bottom.grid(row=3, column=3, sticky="w", padx=(0, 10), pady=6)

        ttk.Label(self.khung_ocr_mode, text="Crop trái").grid(row=4, column=0, sticky="w", padx=(10, 6), pady=6)
        self.o_ocr_crop_left = ttk.Entry(self.khung_ocr_mode, textvariable=self.ocr_crop_left, width=8)
        self.o_ocr_crop_left.grid(row=4, column=1, sticky="w", padx=(0, 12), pady=6)
        ttk.Label(self.khung_ocr_mode, text="phải").grid(row=4, column=2, sticky="w", padx=(0, 6), pady=6)
        self.o_ocr_crop_right = ttk.Entry(self.khung_ocr_mode, textvariable=self.ocr_crop_right, width=8)
        self.o_ocr_crop_right.grid(row=4, column=3, sticky="w", padx=(0, 10), pady=6)

        self.nut_chon_vung_ocr = ttk.Button(self.khung_ocr_mode, text="Chọn vùng OCR trên video", command=self._chon_vung_ocr)
        self.nut_chon_vung_ocr.grid(row=5, column=0, columnspan=4, sticky="ew", padx=10, pady=(8, 10))
        self.ocr_mode_widgets.extend(
            [
                self.o_ocr_fps,
                self.o_ocr_use_gpu,
                self.o_ocr_crop_top,
                self.o_ocr_crop_bottom,
                self.o_ocr_crop_left,
                self.o_ocr_crop_right,
                self.nut_chon_vung_ocr,
            ]
        )

    def _tao_vung_cau_hinh_dich(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Cấu hình dịch Trung sang Việt")
        khung.grid(row=5, column=0, sticky="ew", pady=(0, 8))
        for cot in (1, 3, 5):
            khung.columnconfigure(cot, weight=1)

        ttk.Label(khung, text="Provider").grid(row=0, column=0, sticky="w", padx=(10, 6), pady=(10, 4))
        ttk.Combobox(khung, textvariable=self.translation_provider, values=("gemini", "api", "local"), state="readonly").grid(
            row=0,
            column=1,
            sticky="ew",
            padx=(0, 12),
            pady=(10, 4),
        )
        ttk.Label(khung, text="Model").grid(row=0, column=2, sticky="w", padx=(0, 6), pady=(10, 4))
        ttk.Entry(khung, textvariable=self.translation_model).grid(row=0, column=3, sticky="ew", padx=(0, 12), pady=(10, 4))
        ttk.Label(khung, text="Chế độ").grid(row=0, column=4, sticky="w", padx=(0, 6), pady=(10, 4))
        ttk.Combobox(
            khung,
            textvariable=self.translation_quality,
            values=("high_quality", "balanced", "fast"),
            state="readonly",
        ).grid(row=0, column=5, sticky="ew", padx=(0, 10), pady=(10, 4))

        ttk.Label(khung, text="API key, cách nhau bằng ,").grid(row=1, column=0, sticky="w", padx=(10, 6), pady=(4, 10))
        self.o_api_key = ttk.Entry(khung, textvariable=self.translation_api_key, show="*")
        self.o_api_key.grid(
            row=1,
            column=1,
            sticky="ew",
            padx=(0, 6),
            pady=(4, 10),
        )
        self.nut_xem_api_key = ttk.Button(khung, text="Xem", command=self._doi_hien_api_key, width=7)
        self.nut_xem_api_key.grid(row=1, column=2, sticky="ew", padx=(0, 12), pady=(4, 10))

        ttk.Label(khung, text="Thêm API key").grid(row=2, column=0, sticky="w", padx=(10, 6), pady=(0, 10))
        ttk.Entry(khung, textvariable=self.translation_api_key_moi, show="*").grid(
            row=2,
            column=1,
            sticky="ew",
            padx=(0, 6),
            pady=(0, 10),
        )
        ttk.Button(khung, text="Thêm", command=self._them_api_key).grid(
            row=2,
            column=2,
            sticky="ew",
            padx=(0, 12),
            pady=(0, 10),
        )
        ttk.Label(khung, text="Glossary").grid(row=1, column=3, sticky="w", padx=(0, 6), pady=(4, 10))
        self.o_glossary = tk.Text(khung, height=3, wrap="word")
        self.o_glossary.grid(row=1, column=4, rowspan=2, columnspan=2, sticky="ew", padx=(0, 10), pady=(4, 10))
        self.o_glossary.insert("1.0", tai_cau_hinh().glossary_text)

    def _tao_vung_hang_doi(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Hàng đợi video")
        khung.grid(row=5, column=0, sticky="nsew", pady=(0, 8))
        khung.rowconfigure(0, weight=1)
        khung.columnconfigure(0, weight=1)

        cot = ("ten_video", "thoi_luong", "model", "ocr_trang_thai", "trang_thai", "tien_trinh", "ket_qua", "loi")
        self.bang_hang_doi = ttk.Treeview(khung, columns=cot, show="headings", height=5)
        tieu_de = {
            "ten_video": "Tên video",
            "thoi_luong": "Thời lượng",
            "model": "Model",
            "ocr_trang_thai": "Trạng thái OCR",
            "trang_thai": "Trạng thái",
            "tien_trinh": "Tiến trình",
            "ket_qua": "Kết quả",
            "loi": "Lỗi",
        }
        do_rong = {
            "ten_video": 230,
            "thoi_luong": 80,
            "model": 90,
            "ocr_trang_thai": 140,
            "trang_thai": 110,
            "tien_trinh": 80,
            "ket_qua": 220,
            "loi": 220,
        }
        for ma_cot in cot:
            self.bang_hang_doi.heading(ma_cot, text=tieu_de[ma_cot])
            self.bang_hang_doi.column(ma_cot, width=do_rong[ma_cot], anchor="w")
        self.bang_hang_doi.grid(row=0, column=0, sticky="nsew", padx=10, pady=(10, 6))
        self.bang_hang_doi.bind("<<TreeviewSelect>>", self._chon_dong_hang_doi)
        cuon_doc = ttk.Scrollbar(khung, orient="vertical", command=self.bang_hang_doi.yview)
        cuon_doc.grid(row=0, column=1, sticky="ns", pady=(10, 6))
        cuon_ngang = ttk.Scrollbar(khung, orient="horizontal", command=self.bang_hang_doi.xview)
        cuon_ngang.grid(row=2, column=0, sticky="ew", padx=10)
        self.bang_hang_doi.configure(yscrollcommand=cuon_doc.set, xscrollcommand=cuon_ngang.set)

        khung_nut = ttk.Frame(khung)
        khung_nut.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        khung_nut.columnconfigure(1, weight=1)
        self.nhan_so_video_hang_doi = ttk.Label(khung_nut, text="Tong video: 0")
        self.nhan_so_video_hang_doi.grid(row=0, column=0, padx=(0, 12))
        self.nhan_tom_tat_trang_thai_video = ttk.Label(khung_nut, text="Chưa có video trong hàng chờ")
        self.nhan_tom_tat_trang_thai_video.grid(row=0, column=1, padx=(0, 12), sticky="w")
        self.nhan_video_hang_doi_dang_chon = ttk.Label(khung_nut, text="Chưa chọn video")
        self.nhan_video_hang_doi_dang_chon.grid(row=0, column=2, padx=(0, 12), sticky="w")
        self.nut_xem_video_hang_doi = ttk.Button(
            khung_nut,
            text="Preview / chạy thử video",
            command=self._xem_preview_video_hang_doi,
        )
        self.nut_xem_video_hang_doi.grid(row=0, column=3, padx=(0, 8))
        self.nut_chon_vung_ocr_hang_doi = ttk.Button(
            khung_nut,
            text="Chọn vùng OCR cho video",
            command=self._chon_vung_ocr_cho_video_hang_doi,
        )
        self.nut_chon_vung_ocr_hang_doi.grid(row=0, column=4, padx=(0, 8))
        self.nut_chon_nhieu_video = ttk.Button(khung_nut, text="Thêm video vào hàng đợi", command=self._chon_nhieu_video)
        self.nut_chon_nhieu_video.grid(row=0, column=5, padx=(0, 8))
        self.nut_xoa_chua_chay = ttk.Button(khung_nut, text="Xóa video đã chọn", command=self._xoa_video_chua_chay)
        self.nut_xoa_chua_chay.grid(row=0, column=6, padx=(0, 8))
        self.nut_thu_lai_loi = ttk.Button(khung_nut, text="Thử lại video lỗi", command=self._thu_lai_video_loi)
        self.nut_thu_lai_loi.grid(row=0, column=7, padx=(0, 8))
        self.nut_dung_sau_file = ttk.Button(
            khung_nut,
            text="Dừng sau file hiện tại",
            command=self._dung_sau_file,
            state=tk.DISABLED,
        )
        self.nut_dung_sau_file.grid(row=0, column=8, padx=(0, 8))
        self.nut_dung_ngay = ttk.Button(
            khung_nut,
            text="Dừng ngay an toàn",
            command=self._dung_ngay_an_toan,
            state=tk.DISABLED,
        )
        self.nut_dung_ngay.grid(row=0, column=9, padx=(0, 8))

    def _tao_thanh_nut_phu(self, cha: ttk.Frame) -> None:
        khung = ttk.Frame(cha)
        khung.grid(row=9, column=0, sticky="ew", pady=(0, 8))

        self.nut_kiem_tra = ttk.Button(khung, text="Kiểm tra FFmpeg", command=self._kiem_tra_ffmpeg)
        self.nut_kiem_tra.grid(row=0, column=0, padx=(0, 8))
        self.nut_tach_audio = ttk.Button(khung, text="Tách âm thanh", command=self._tach_audio)
        self.nut_tach_audio.grid(row=0, column=1, padx=(0, 8))
        self.nut_nhan_dang = ttk.Button(khung, text="Nhận dạng tiếng Trung", command=self._nhan_dang)
        self.nut_nhan_dang.grid(row=0, column=2, padx=(0, 8))
        self.nut_xuat_srt_zh = ttk.Button(khung, text="Xuất SRT tiếng Trung", command=self._xuat_srt_tieng_trung)
        self.nut_xuat_srt_zh.grid(row=0, column=3, padx=(0, 8))
        self.nut_dich_thu = ttk.Button(khung, text="Dịch thử", command=self._dich_thu)
        self.nut_dich_thu.grid(row=0, column=4, padx=(0, 8))
        self.nut_xuat_srt_vi = ttk.Button(khung, text="Xuất SRT tiếng Việt", command=self._xuat_srt_tieng_viet)
        self.nut_xuat_srt_vi.grid(row=0, column=5, padx=(0, 8))

    def _tao_tien_trinh(self, cha: ttk.Frame) -> None:
        khung = ttk.Frame(cha)
        khung.grid(row=6, column=0, sticky="ew", pady=(0, 10))
        khung.columnconfigure(1, weight=1)

        ttk.Label(khung, textvariable=self.ten_buoc_hien_tai, width=28).grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.tien_trinh = ttk.Progressbar(khung, mode="determinate", maximum=100)
        self.tien_trinh.grid(row=0, column=1, sticky="ew")

    def _tao_bang_xem_truoc(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Kiểm tra mẫu 10 câu đầu tiếng Trung")
        khung.grid(row=7, column=0, sticky="nsew", pady=(0, 10))
        khung.rowconfigure(0, weight=1)
        khung.columnconfigure(0, weight=1)

        self.o_preview_srt = tk.Text(khung, height=5, wrap="word", state="disabled")
        self.o_preview_srt.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        khung_dich = ttk.LabelFrame(cha, text="Đối chiếu Trung - Việt")
        khung_dich.grid_remove()
        khung_dich.rowconfigure(0, weight=1)
        khung_dich.columnconfigure(0, weight=1)

        cot = ("index", "original_zh", "translated_vi")
        self.bang_dich = ttk.Treeview(khung_dich, columns=cot, show="headings", height=5)
        self.bang_dich.heading("index", text="#")
        self.bang_dich.heading("original_zh", text="Tiếng Trung")
        self.bang_dich.heading("translated_vi", text="Tiếng Việt")
        self.bang_dich.column("index", width=50, anchor="center", stretch=False)
        self.bang_dich.column("original_zh", width=430, anchor="w")
        self.bang_dich.column("translated_vi", width=430, anchor="w")
        self.bang_dich.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.bang_preview = self.bang_dich

    def _tao_vung_log(self, cha: ttk.Frame) -> None:
        khung = ttk.LabelFrame(cha, text="Log")
        khung.grid(row=8, column=0, sticky="nsew")
        khung.rowconfigure(0, weight=1)
        khung.columnconfigure(0, weight=1)

        self.o_log = tk.Text(khung, height=8, wrap="none", state="disabled")
        self.o_log.grid(row=0, column=0, sticky="nsew")
        cuon_doc = ttk.Scrollbar(khung, orient="vertical", command=self.o_log.yview)
        cuon_doc.grid(row=0, column=1, sticky="ns")
        cuon_ngang = ttk.Scrollbar(khung, orient="horizontal", command=self.o_log.xview)
        cuon_ngang.grid(row=1, column=0, sticky="ew")
        self.o_log.configure(yscrollcommand=cuon_doc.set, xscrollcommand=cuon_ngang.set)

    def _chon_video(self) -> None:
        duong_dan = filedialog.askopenfilename(
            title="Chọn video tiếng Trung",
            filetypes=[("Video", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("Tất cả file", "*.*")],
        )
        if duong_dan:
            self.duong_dan_video.set(duong_dan)
            self.ma_item_hang_doi_dang_chon = None
            self._ghi_log(f"Đã chọn video: {duong_dan}")

    def _chon_nhieu_video(self) -> None:
        duong_dan_video = filedialog.askopenfilenames(
            title="Chọn nhiều video tiếng Trung",
            filetypes=[("Video", "*.mp4 *.mkv *.avi *.mov *.wmv"), ("Tất cả file", "*.*")],
        )
        da_them = 0
        for duong_dan in duong_dan_video:
            if self._them_video_vao_hang_doi(duong_dan):
                da_them += 1
        if duong_dan_video:
            self.duong_dan_video.set(duong_dan_video[0])
            self._lam_moi_bang_hang_doi()
            if self.bang_hang_doi.get_children() and not self.bang_hang_doi.selection():
                self.bang_hang_doi.selection_set(self.bang_hang_doi.get_children()[0])
            self._ghi_log(f"Da them {da_them}/{len(duong_dan_video)} video vao hang doi.")
            self._ghi_log(f"Đã thêm {len(duong_dan_video)} video vào hàng đợi.")

    def _them_video_vao_hang_doi(self, duong_dan: str) -> bool:
        video = Path(duong_dan)
        if any(Path(str(item["path"])) == video for item in self.hang_doi_video):
            self._ghi_log(f"Video đã có trong hàng đợi: {video.name}")
            return False
        try:
            thoi_luong = f"{lay_thoi_luong_video(video):.2f}s"
        except Exception:
            thoi_luong = "Chưa rõ"
        item = {
            "id": self.ma_hang_doi_tiep_theo,
            "path": str(video),
            "ten_video": video.name,
            "thoi_luong": thoi_luong,
            "model": self.model_size.get(),
            "ocr_region": self._vung_ocr_hien_tai(),
            "ocr_region_custom": False,
            "ocr_status": "Chưa chọn OCR",
            "trang_thai": "Chờ",
            "tien_trinh": "0%",
            "ket_qua": "",
            "loi": "",
            "tree_id": "",
        }
        self.ma_hang_doi_tiep_theo += 1
        self.hang_doi_video.append(item)
        self._lam_moi_bang_hang_doi()
        self._ghi_log(f"Da them vao hang doi: {video.name}")
        return True
        self._ghi_log(f"Đã thêm vào hàng đợi: {video.name}")

    def _gia_tri_dong_hang_doi(self, item: dict[str, object]) -> tuple[object, ...]:
        trang_thai_ocr = str(item.get("ocr_status") or ("Đã chọn OCR" if item.get("ocr_region_custom") else "Chưa chọn OCR"))
        return (
            item["ten_video"],
            item["thoi_luong"],
            item["model"],
            trang_thai_ocr,
            item["trang_thai"],
            item["tien_trinh"],
            item["ket_qua"],
            item["loi"],
        )

    def _cap_nhat_dong_hang_doi(self, item: dict[str, object]) -> None:
        tree_id = str(item.get("tree_id", ""))
        if tree_id and self.bang_hang_doi.exists(tree_id):
            self.bang_hang_doi.item(tree_id, values=self._gia_tri_dong_hang_doi(item))
        else:
            self._lam_moi_bang_hang_doi()
        self._cap_nhat_tom_tat_hang_doi()

    def _dat_trang_thai_ocr_item(self, item: dict[str, object], trang_thai: str) -> None:
        item["ocr_status"] = trang_thai
        self._cap_nhat_dong_hang_doi(item)

    def _lam_moi_bang_hang_doi(self) -> None:
        ma_dang_chon = self.ma_item_hang_doi_dang_chon
        for tree_id in self.bang_hang_doi.get_children():
            self.bang_hang_doi.delete(tree_id)
        for item in self.hang_doi_video:
            tree_id = self.bang_hang_doi.insert("", "end", values=self._gia_tri_dong_hang_doi(item))
            item["tree_id"] = tree_id
        if ma_dang_chon is not None:
            item_dang_chon = self._tim_item_hang_doi(ma_dang_chon)
            if item_dang_chon is not None:
                self.bang_hang_doi.selection_set(str(item_dang_chon["tree_id"]))
        if hasattr(self, "nhan_so_video_hang_doi"):
            self.nhan_so_video_hang_doi.configure(text=f"Tong video: {len(self.hang_doi_video)}")
        self.bang_hang_doi.update_idletasks()
        self._cap_nhat_tom_tat_hang_doi()

    def _cap_nhat_tom_tat_hang_doi(self) -> None:
        if not hasattr(self, "nhan_tom_tat_trang_thai_video"):
            return
        tong = len(self.hang_doi_video)
        da_chon = sum(1 for item in self.hang_doi_video if item.get("ocr_status") in {"Đã chọn OCR", "Đã chạy OCR"})
        dang_chay = sum(1 for item in self.hang_doi_video if item.get("trang_thai") not in {"Chờ", "Hoàn thành", "Lỗi", "Đã dừng"})
        self.nhan_tom_tat_trang_thai_video.configure(
            text=f"Đã cấu hình OCR: {da_chon} | Đang xử lý: {dang_chay}"
            if tong
            else "Chưa có video trong hàng chờ"
        )

    def _vung_ocr_hien_tai(self) -> tuple[float, float, float, float]:
        return (
            self._doc_float(self.ocr_crop_left.get(), 0.0),
            self._doc_float(self.ocr_crop_top.get(), 0.75),
            self._doc_float(self.ocr_crop_right.get(), 1.0),
            self._doc_float(self.ocr_crop_bottom.get(), 1.0),
        )

    def _chon_dong_hang_doi(self, _event: tk.Event | None = None) -> None:
        selections = self.bang_hang_doi.selection()
        if not selections:
            return
        tree_id = selections[0]
        item = next(
            (candidate for candidate in self.hang_doi_video if str(candidate.get("tree_id", "")) == tree_id),
            None,
        )
        if item is None:
            return
        self.ma_item_hang_doi_dang_chon = int(item["id"])
        self.duong_dan_video.set(str(item["path"]))
        region = item.get("ocr_region", self._vung_ocr_hien_tai())
        if not isinstance(region, tuple) or len(region) != 4:
            region = self._vung_ocr_hien_tai()
        self._dat_vung_ocr_giao_dien(region)
        self.nhan_video_hang_doi_dang_chon.configure(
            text=f"Đang chọn: {item['ten_video']} | {item.get('ocr_status', 'Chưa chọn OCR')}"
        )
        self._ghi_log(f"Đã chọn video trong hàng đợi: {item['ten_video']}")

    def _dat_vung_ocr_giao_dien(self, region: tuple[float, float, float, float]) -> None:
        left, top, right, bottom = region
        self.ocr_crop_left.set(f"{float(left):.4f}")
        self.ocr_crop_top.set(f"{float(top):.4f}")
        self.ocr_crop_right.set(f"{float(right):.4f}")
        self.ocr_crop_bottom.set(f"{float(bottom):.4f}")

    def _tim_item_hang_doi(self, ma_item: int) -> dict[str, object] | None:
        for item in self.hang_doi_video:
            if item["id"] == ma_item:
                return item
        return None

    def _item_hang_doi_dang_chon(self) -> dict[str, object] | None:
        if self.ma_item_hang_doi_dang_chon is not None:
            item = self._tim_item_hang_doi(self.ma_item_hang_doi_dang_chon)
            if item is not None:
                return item
        selections = self.bang_hang_doi.selection()
        if selections:
            tree_id = selections[0]
            return next(
                (
                    item
                    for item in self.hang_doi_video
                    if str(item.get("tree_id", "")) == tree_id
                ),
                None,
            )
        return None

    def _xoa_video_chua_chay(self) -> None:
        cac_tree_id = set(self.bang_hang_doi.selection())
        if not cac_tree_id:
            messagebox.showinfo("Hàng đợi", "Hãy chọn video cần xóa trong bảng.")
            return
        giu_lai: list[dict[str, object]] = []
        da_xoa = 0
        for item in self.hang_doi_video:
            duoc_chon = item["tree_id"] in cac_tree_id
            if duoc_chon:
                if self.dang_chay_hang_doi and int(item["id"]) == self.ma_item_dang_chay and self.stop_event_hien_tai is not None:
                    self.stop_event_hien_tai.set()
                    item["trang_thai"] = "Đã dừng"
                    item["loi"] = "Đã xóa khi đang chạy."
                self.bang_hang_doi.delete(str(item["tree_id"]))
                da_xoa += 1
            else:
                giu_lai.append(item)
        self.hang_doi_video = giu_lai
        if self.ma_item_hang_doi_dang_chon is not None and self._tim_item_hang_doi(self.ma_item_hang_doi_dang_chon) is None:
            self.ma_item_hang_doi_dang_chon = None
            self.nhan_video_hang_doi_dang_chon.configure(text="Chưa chọn video")
        self._lam_moi_bang_hang_doi()
        self._ghi_log(f"Đã xóa {da_xoa} video khỏi hàng đợi.")

    def _thu_lai_video_loi(self) -> None:
        dem = 0
        for item in self.hang_doi_video:
            if item["trang_thai"] in {"Lỗi", "Đã dừng"}:
                item["trang_thai"] = "Chờ"
                item["tien_trinh"] = "0%"
                item["loi"] = ""
                self._cap_nhat_dong_hang_doi(item)
                dem += 1
        self._ghi_log(f"Đã đưa {dem} video lỗi/dừng về trạng thái chờ.")

    def _dung_sau_file(self) -> None:
        self.dung_sau_file_hien_tai = True
        self._ghi_log("Đã bật dừng sau file hiện tại. Video đang chạy sẽ hoàn tất rồi hàng đợi dừng lại.")

    def _dung_ngay_an_toan(self) -> None:
        self.dung_sau_file_hien_tai = True
        if self.stop_event_hien_tai is not None:
            self.stop_event_hien_tai.set()
        self.pipeline_stop_event.set()
        self._ghi_log("Đã yêu cầu dừng ngay an toàn. App sẽ dừng ở điểm an toàn gần nhất.")

    def _chon_thu_muc_dau_ra(self) -> None:
        thu_muc_hien_tai = Path(self.thu_muc_dau_ra.get()).expanduser()
        initialdir = str(thu_muc_hien_tai if thu_muc_hien_tai.exists() else Path.cwd())
        duong_dan = filedialog.askdirectory(title="Chọn nơi lưu SRT tiếng Trung", initialdir=initialdir)
        if duong_dan:
            self.thu_muc_dau_ra.set(duong_dan)
            self._luu_cau_hinh_hien_tai()
            self._ghi_log(f"Đã chọn nơi lưu SRT: {duong_dan}")

    def _lay_video_cho_ocr(self) -> Path | None:
        item = self._item_hang_doi_dang_chon()
        duong_dan = str(item["path"]) if item is not None else self.duong_dan_video.get().strip()
        if not duong_dan and self.hang_doi_video:
            duong_dan = str(self.hang_doi_video[0]["path"])
            self.duong_dan_video.set(duong_dan)
        if not duong_dan:
            messagebox.showinfo("OCR", "Hãy chọn hoặc thêm video trước khi chọn vùng OCR.")
            return None
        video = Path(duong_dan)
        if not video.exists():
            messagebox.showwarning("OCR", "Video đã chọn không tồn tại.")
            return None
        return video

    def _mo_preview_ocr_cho_video_hang_doi(self, luu_vung: bool) -> bool:
        item = self._item_hang_doi_dang_chon()
        if item is None:
            messagebox.showinfo("Hàng đợi", "Hãy chọn một video trong bảng trước.")
            return False
        video = Path(str(item["path"]))
        if not video.exists():
            messagebox.showwarning("Hàng đợi", "Video đã chọn không tồn tại.")
            return False
        region = item.get("ocr_region", self._vung_ocr_hien_tai())
        if not isinstance(region, tuple) or len(region) != 4:
            region = self._vung_ocr_hien_tai()
        trang_thai_truoc = str(item.get("ocr_status") or ("Đã chọn OCR" if item.get("ocr_region_custom") else "Chưa chọn OCR"))
        self._dat_trang_thai_ocr_item(item, "Đang chỉnh OCR")
        self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | Đang chỉnh OCR")
        try:
            region_moi = chon_vung_ocr(self, video, region)
        except Exception as loi:
            self._dat_trang_thai_ocr_item(item, trang_thai_truoc)
            self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | {trang_thai_truoc}")
            messagebox.showwarning("Preview OCR", f"Không mở được preview video: {loi}")
            self._ghi_log(f"Lỗi preview OCR cho {video.name}: {loi}")
            return False
        if region_moi is None:
            self._dat_trang_thai_ocr_item(item, trang_thai_truoc)
            self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | {trang_thai_truoc}")
            return False
        self.duong_dan_video.set(str(video))
        self._dat_vung_ocr_giao_dien(region_moi)
        if luu_vung:
            item["ocr_region"] = region_moi
            item["ocr_region_custom"] = True
            item["ocr_status"] = "Đã chọn OCR"
            self._cap_nhat_dong_hang_doi(item)
            self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | Đã chọn OCR")
            self._luu_cau_hinh_hien_tai()
            self._ghi_log(f"Đã lưu vùng OCR riêng cho {video.name}.")
        return True

    def _xem_preview_video_hang_doi(self) -> None:
        self._mo_preview_ocr_cho_video_hang_doi(luu_vung=True)

    def _chon_vung_ocr_cho_video_hang_doi(self) -> None:
        self._mo_preview_ocr_cho_video_hang_doi(luu_vung=True)

    def _chon_vung_ocr(self) -> bool:
        video = self._lay_video_cho_ocr()
        if video is None:
            return False
        item = self._item_hang_doi_dang_chon()
        trang_thai_truoc = ""
        if item is not None and Path(str(item["path"])).resolve() == video.resolve():
            trang_thai_truoc = str(item.get("ocr_status") or ("Đã chọn OCR" if item.get("ocr_region_custom") else "Chưa chọn OCR"))
            self._dat_trang_thai_ocr_item(item, "Đang chỉnh OCR")
            self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | Đang chỉnh OCR")
        try:
            region = chon_vung_ocr(
                self,
                video,
                (
                    self._doc_float(self.ocr_crop_left.get(), 0.0),
                    self._doc_float(self.ocr_crop_top.get(), 0.75),
                    self._doc_float(self.ocr_crop_right.get(), 1.0),
                    self._doc_float(self.ocr_crop_bottom.get(), 1.0),
                ),
            )
        except Exception as loi:
            if item is not None and trang_thai_truoc:
                self._dat_trang_thai_ocr_item(item, trang_thai_truoc)
                self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | {trang_thai_truoc}")
            messagebox.showwarning("OCR", f"Không mở được preview video: {loi}")
            self._ghi_log(f"Lỗi preview OCR: {loi}")
            return False
        if region is None:
            if item is not None and trang_thai_truoc:
                self._dat_trang_thai_ocr_item(item, trang_thai_truoc)
                self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | {trang_thai_truoc}")
            return False
        self._dat_vung_ocr_giao_dien(region)
        if item is not None and Path(str(item["path"])).resolve() == video.resolve():
            item["ocr_region"] = region
            item["ocr_region_custom"] = True
            item["ocr_status"] = "Đã chọn OCR"
            self._cap_nhat_dong_hang_doi(item)
            self.nhan_video_hang_doi_dang_chon.configure(text=f"Đang chọn: {item['ten_video']} | Đã chọn OCR")
        left, top, right, bottom = region
        self._luu_cau_hinh_hien_tai()
        self._ghi_log(f"Đã chọn vùng OCR: trái={left:.3f}, trên={top:.3f}, phải={right:.3f}, dưới={bottom:.3f}")
        return True

    def _chon_vung_ocr_neu_can(self) -> bool:
        left = self._doc_float(self.ocr_crop_left.get(), 0.0)
        top = self._doc_float(self.ocr_crop_top.get(), 0.75)
        right = self._doc_float(self.ocr_crop_right.get(), 1.0)
        bottom = self._doc_float(self.ocr_crop_bottom.get(), 1.0)
        if right <= left or bottom <= top:
            return self._chon_vung_ocr()
        return True

    def _kiem_tra_ffmpeg(self) -> None:
        self._chay_nen("Đang kiểm tra FFmpeg...", self.worker.kiem_tra_ffmpeg_va_video, self.duong_dan_video.get())

    def _tach_audio(self) -> None:
        self._chay_nen("Đang tách âm thanh...", self.worker.tach_audio, self.duong_dan_video.get())

    def _nhan_dang(self) -> None:
        if self._engine_hien_tai() == "ocr_subtitle":
            if not self._chon_vung_ocr_neu_can():
                return
            self._chay_nen(
                "Đang OCR phụ đề tiếng Trung trên video...",
                self.worker.nhan_dang_ocr_tieng_trung,
                self.duong_dan_video.get(),
                self.thu_muc_dau_ra.get(),
                self._doc_float(self.ocr_fps.get(), 3.0),
                self._doc_float(self.ocr_crop_left.get(), 0.0),
                self._doc_float(self.ocr_crop_top.get(), 0.75),
                self._doc_float(self.ocr_crop_right.get(), 1.0),
                self._doc_float(self.ocr_crop_bottom.get(), 1.0),
                self.ocr_use_gpu.get(),
                self._ghi_log_tu_thread,
            )
            return

        self._chay_nen(
            "Đang nhận dạng tiếng Trung...",
            self.worker.nhan_dang_tieng_trung,
            self.duong_dan_wav.get(),
            self.recognition_engine.get(),
            self.model_size.get(),
            self.device.get(),
            self.language.get(),
            self.vad_filter.get(),
            self.full_dialogue_mode.get(),
            self.aggressive_gap_fill.get(),
            self._ghi_log_tu_thread,
        )

    def _xuat_srt_tieng_trung(self) -> None:
        self._chay_nen(
            "Đang xuất SRT tiếng Trung...",
            self.worker.xuat_srt_tieng_trung,
            self.duong_dan_video.get(),
            self.duong_dan_wav.get(),
            self.thu_muc_dau_ra.get(),
        )

    def _dich_thu(self) -> None:
        self._chay_nen(
            "Đang dịch thử tiếng Việt...",
            self.worker.dich_thu,
            self.duong_dan_wav.get(),
            self.translation_provider.get(),
            self.translation_model.get(),
            self.translation_api_key.get(),
            self.translation_quality.get(),
            self.o_glossary.get("1.0", tk.END),
        )

    def _xuat_srt_tieng_viet(self) -> None:
        self._chay_nen(
            "Đang xuất SRT tiếng Việt...",
            self.worker.xuat_srt_tieng_viet,
            self.duong_dan_video.get(),
            self.duong_dan_wav.get(),
            self.thu_muc_dau_ra.get(),
        )

    def _doi_hien_api_key(self) -> None:
        dang_hien = not self.api_key_visible.get()
        self.api_key_visible.set(dang_hien)
        self.o_api_key.configure(show="" if dang_hien else "*")
        self.nut_xem_api_key.configure(text="Ẩn" if dang_hien else "Xem")

    def _them_api_key(self) -> None:
        api_moi = self.translation_api_key_moi.get().strip().strip(",")
        if not api_moi:
            messagebox.showwarning("Cần kiểm tra lại", "Vui lòng nhập API key cần thêm.")
            return

        api_cu = self.translation_api_key.get().strip()
        if api_cu:
            api_cu = api_cu.rstrip(" ,")
            self.translation_api_key.set(f"{api_cu}, {api_moi}")
        else:
            self.translation_api_key.set(api_moi)

        self.translation_api_key_moi.set("")
        self._ghi_log("Đã thêm API key vào danh sách. Các key được ngăn cách bằng dấu phẩy.")

    def _bat_dau_pipeline(self) -> None:
        if self._engine_hien_tai() == "ocr_subtitle" and not self._chon_vung_ocr_neu_can():
            return
        self._bat_dau_hang_doi()

    def _doi_che_do_nhan_dang(self) -> None:
        if self.recognition_mode.get() == "ocr":
            if self.recognition_engine.get() not in {"whisper", "sensevoice", "hybrid"}:
                self.recognition_engine.set("hybrid")
            self._ghi_log("Đã chọn chế độ OCR: đọc phụ đề tiếng Trung có sẵn trên video.")
            self._chon_vung_ocr_neu_can()
        else:
            if self.recognition_engine.get() not in {"whisper", "sensevoice", "hybrid"}:
                self.recognition_engine.set("hybrid")
            self._ghi_log("Đã chọn chế độ âm thanh: dùng Whisper/Hybrid để nhận dạng lời nói.")
        self._dong_bo_giao_dien_nhan_dang()

    def _dong_bo_giao_dien_nhan_dang(self) -> None:
        audio_engines = {"whisper", "sensevoice", "hybrid"}
        if self.recognition_engine.get() == "ocr_subtitle":
            self.recognition_mode.set("ocr")
            self.recognition_engine.set("hybrid")
        elif self.recognition_mode.get() == "ocr":
            if self.recognition_engine.get() not in audio_engines:
                self.recognition_engine.set("hybrid")
        else:
            self.recognition_mode.set("audio")
            if self.recognition_engine.get() not in audio_engines:
                self.recognition_engine.set("hybrid")

        che_do_ocr = self.recognition_mode.get() == "ocr"
        if hasattr(self, "nhan_che_do_nhan_dang"):
            self.nhan_che_do_nhan_dang.configure(
                text=(
                    "CHẾ ĐỘ ĐANG CHẠY: OCR PHỤ ĐỀ TRÊN VIDEO"
                    if che_do_ocr
                    else "CHẾ ĐỘ ĐANG CHẠY: WHISPER / HYBRID THEO ÂM THANH"
                )
            )
        if hasattr(self, "khung_audio_mode"):
            self.khung_audio_mode.configure(
                text=(
                    "1. Whisper / Hybrid - nhận dạng từ âm thanh"
                    if che_do_ocr
                    else "✓ 1. Whisper / Hybrid - ĐANG DÙNG"
                )
            )
        if hasattr(self, "khung_ocr_mode"):
            self.khung_ocr_mode.configure(
                text=(
                    "✓ 2. OCR - ĐANG DÙNG"
                    if che_do_ocr
                    else "2. OCR - đọc phụ đề đã có trên hình video"
                )
            )
        self._dat_trang_thai_nhom_nhan_dang(
            getattr(self, "audio_mode_widgets", []),
            not che_do_ocr,
        )
        self._dat_trang_thai_nhom_nhan_dang(
            getattr(self, "ocr_mode_widgets", []),
            che_do_ocr,
        )
        dang_chay = self.dang_chay_hang_doi
        for ten_nut in ("nut_xem_video_hang_doi", "nut_chon_vung_ocr_hang_doi"):
            nut = getattr(self, ten_nut, None)
            if nut is not None:
                nut.configure(state=tk.NORMAL if che_do_ocr and not dang_chay else tk.DISABLED)

    def _dat_trang_thai_nhom_nhan_dang(self, widgets: list[tk.Widget], bat: bool) -> None:
        for widget in widgets:
            try:
                if isinstance(widget, ttk.Combobox):
                    widget.configure(state="readonly" if bat else tk.DISABLED)
                else:
                    widget.configure(state=tk.NORMAL if bat else tk.DISABLED)
            except tk.TclError:
                pass

    def _engine_hien_tai(self) -> str:
        if self.recognition_mode.get() == "ocr":
            return "ocr_subtitle"
        engine = self.recognition_engine.get()
        return "hybrid" if engine == "ocr_subtitle" else engine

    def _tao_pipeline_config(self) -> PipelineConfig:
        return PipelineConfig(
            model_size=self.model_size.get(),
            recognition_engine=self._engine_hien_tai(),
            device=self.device.get(),
            language=self.language.get(),
            vad_filter=self.vad_filter.get(),
            difficult_audio_mode=self.difficult_audio_mode.get(),
            full_dialogue_mode=self.full_dialogue_mode.get(),
            aggressive_gap_fill=self.aggressive_gap_fill.get(),
            ocr_fps=self._doc_float(self.ocr_fps.get(), 3.0),
            ocr_crop_left=self._doc_float(self.ocr_crop_left.get(), 0.0),
            ocr_crop_top=self._doc_float(self.ocr_crop_top.get(), 0.75),
            ocr_crop_right=self._doc_float(self.ocr_crop_right.get(), 1.0),
            ocr_crop_bottom=self._doc_float(self.ocr_crop_bottom.get(), 1.0),
            ocr_use_gpu=self.ocr_use_gpu.get(),
            provider="none",
            translation_model="",
            api_key="",
            quality_mode="",
            glossary_text="",
            keep_wav=self.keep_wav.get(),
        )

    def _bat_dau_hang_doi(self) -> None:
        if self.dang_chay_hang_doi:
            return
        try:
            Path(self.thu_muc_dau_ra.get()).mkdir(parents=True, exist_ok=True)
        except OSError as loi:
            messagebox.showwarning("Cần kiểm tra lại", f"Không tạo được nơi lưu SRT: {loi}")
            return
        cac_video_cho = [item for item in self.hang_doi_video if item["trang_thai"] == "Chờ"]
        if not cac_video_cho:
            messagebox.showinfo("Hàng đợi", "Không có video nào đang chờ xử lý.")
            return
        self.dang_chay_hang_doi = True
        self.dung_sau_file_hien_tai = False
        self.pipeline_stop_event.clear()
        self._dat_dang_xu_ly(True)
        self.nut_dung_sau_file.configure(state=tk.NORMAL)
        self.nut_dung_ngay.configure(state=tk.NORMAL)
        self._ghi_log_moi_truong_nen()
        self._ghi_log(f"Bắt đầu xử lý hàng đợi {len(cac_video_cho)} video.")
        config_hang_doi = self._tao_pipeline_config()
        thu_muc_output = self.thu_muc_dau_ra.get()

        def viec_nen() -> None:
            self._chay_hang_doi_nen(cac_video_cho, config_hang_doi, thu_muc_output)

        threading.Thread(target=viec_nen, daemon=True).start()

    def _chay_hang_doi_nen(
        self,
        cac_video_cho: list[dict[str, object]],
        config: PipelineConfig,
        thu_muc_output: str,
    ) -> None:
        tong = len(cac_video_cho)
        da_xong = 0
        for item in cac_video_cho:
            if self._tim_item_hang_doi(int(item["id"])) is None:
                da_xong += 1
                self.hang_doi_ui.put(("progress", (f"Hàng đợi {da_xong}/{tong}", int(da_xong / tong * 100))))
                continue
            if self.dung_sau_file_hien_tai or self.pipeline_stop_event.is_set():
                item["trang_thai"] = "Đã dừng"
                item["loi"] = "Dừng trước khi chạy."
                self.hang_doi_ui.put(("queue_update", item.copy()))
                continue

            ma_item = int(item["id"])
            ten_video = str(item["ten_video"])
            stop_event = threading.Event()
            self.stop_event_hien_tai = stop_event
            self.ma_item_dang_chay = ma_item
            item["trang_thai"] = "Tách âm thanh"
            item["tien_trinh"] = "0%"
            item["loi"] = ""
            if config.recognition_engine == "ocr_subtitle":
                item["ocr_status"] = "Đang chạy OCR"
            self.hang_doi_ui.put(("queue_update", item.copy()))

            def log_callback(noi_dung: str, ten: str = ten_video) -> None:
                self.hang_doi_ui.put(("log", f"[{ten}] {noi_dung}"))

            def progress_callback(ten_buoc: str, phan_tram: int, ma: int = ma_item) -> None:
                trang_thai = self._trang_thai_tu_buoc(ten_buoc)
                tong_the = int(((da_xong + max(0, min(100, phan_tram)) / 100) / tong) * 100)
                self.hang_doi_ui.put(("queue_progress", (ma, trang_thai, phan_tram, tong_the, ten_buoc)))

            try:
                config_item = config
                if config.recognition_engine == "ocr_subtitle":
                    region = item.get(
                        "ocr_region",
                        (
                            config.ocr_crop_left,
                            config.ocr_crop_top,
                            config.ocr_crop_right,
                            config.ocr_crop_bottom,
                        ),
                    )
                    if isinstance(region, (tuple, list)) and len(region) == 4:
                        config_item = replace(
                            config,
                            ocr_crop_left=float(region[0]),
                            ocr_crop_top=float(region[1]),
                            ocr_crop_right=float(region[2]),
                            ocr_crop_bottom=float(region[3]),
                        )
                ket_qua = self.worker.chay_pipeline(
                    str(item["path"]),
                    thu_muc_output,
                    config_item,
                    log_callback,
                    progress_callback,
                    stop_event,
                )
                item["trang_thai"] = "Hoàn thành"
                item["tien_trinh"] = "100%"
                item["ket_qua"] = str(ket_qua.zh_srt_path)
                item["loi"] = "; ".join(ket_qua.warnings or [])
                if config.recognition_engine == "ocr_subtitle":
                    item["ocr_status"] = "Đã chạy OCR"
                self.hang_doi_ui.put(("queue_update", item.copy()))
                self.hang_doi_ui.put(("queue_result", ket_qua))
            except Exception as loi:
                item["trang_thai"] = "Đã dừng" if stop_event.is_set() else "Lỗi"
                item["loi"] = str(loi)
                if config.recognition_engine == "ocr_subtitle":
                    item["ocr_status"] = "OCR lỗi"
                self.hang_doi_ui.put(("queue_update", item.copy()))
                log_callback(f"Lỗi: {loi}")
            finally:
                da_xong += 1
                self.hang_doi_ui.put(("progress", (f"Hàng đợi {da_xong}/{tong}", int(da_xong / tong * 100))))
                self.stop_event_hien_tai = None
                self.ma_item_dang_chay = None

            if self.dung_sau_file_hien_tai:
                break

        self.hang_doi_ui.put(("queue_done", None))

    def _trang_thai_tu_buoc(self, ten_buoc: str) -> str:
        if "Tách" in ten_buoc or "WAV" in ten_buoc:
            return "Tách âm thanh"
        if "Nhận dạng" in ten_buoc:
            return "Nhận dạng"
        if "Dịch" in ten_buoc or "bản dịch" in ten_buoc:
            return "Dịch"
        if "SRT" in ten_buoc or "Tối ưu" in ten_buoc:
            return "Xuất SRT"
        if "Hoàn thành" in ten_buoc:
            return "Hoàn thành"
        return "Tách âm thanh"

    def _dung_pipeline(self) -> None:
        if self.dang_chay_hang_doi:
            self._dung_ngay_an_toan()
            return
        self.pipeline_stop_event.set()
        self._ghi_log("Đã yêu cầu dừng. Ứng dụng sẽ dừng sau khi bước hiện tại kết thúc an toàn.")

    def _cap_nhat_tien_trinh_tu_thread(self, ten_buoc: str, phan_tram: int) -> None:
        self.hang_doi_ui.put(("progress", (ten_buoc, phan_tram)))

    def _mo_thu_muc_ket_qua(self) -> None:
        thu_muc = Path(self.thu_muc_dau_ra.get()).expanduser().resolve()
        if thu_muc.exists():
            os.startfile(str(thu_muc))
        else:
            messagebox.showwarning("Cần kiểm tra lại", "Thư mục đầu ra chưa tồn tại.")

    def _luu_cau_hinh_hien_tai(self) -> None:
        luu_cau_hinh(
            AppSettings(
                thu_muc_output=self.thu_muc_dau_ra.get(),
                recognition_engine=self._engine_hien_tai(),
                model_size=self.model_size.get(),
                device=self.device.get(),
                language=self.language.get(),
                vad_filter=self.vad_filter.get(),
                difficult_audio_mode=self.difficult_audio_mode.get(),
                full_dialogue_mode=self.full_dialogue_mode.get(),
                aggressive_gap_fill=self.aggressive_gap_fill.get(),
                ocr_fps=self._doc_float(self.ocr_fps.get(), 3.0),
                ocr_crop_left=self._doc_float(self.ocr_crop_left.get(), 0.0),
                ocr_crop_top=self._doc_float(self.ocr_crop_top.get(), 0.75),
                ocr_crop_right=self._doc_float(self.ocr_crop_right.get(), 1.0),
                ocr_crop_bottom=self._doc_float(self.ocr_crop_bottom.get(), 1.0),
                ocr_use_gpu=self.ocr_use_gpu.get(),
                translation_provider=self.translation_provider.get(),
                translation_model=self.translation_model.get(),
                translation_quality=self.translation_quality.get(),
                translation_api_key=self.translation_api_key.get(),
                glossary_text=self.o_glossary.get("1.0", tk.END).strip() if hasattr(self, "o_glossary") else "",
                keep_wav=self.keep_wav.get(),
                shutdown_when_done=self.shutdown_when_done.get(),
            )
        )
        self._ghi_log("Đã lưu cấu hình. Lần sau mở app sẽ dùng lại các lựa chọn này.")

    def _doc_float(self, gia_tri: str, mac_dinh: float) -> float:
        try:
            return float(str(gia_tri).strip().replace(",", "."))
        except ValueError:
            return mac_dinh

    def _chay_nen(self, thong_bao: str, ham: Callable[..., object], *tham_so: object) -> None:
        self._dat_dang_xu_ly(True)
        self._ghi_log(thong_bao)

        def viec_nen() -> None:
            try:
                ket_qua = ham(*tham_so)
                self.hang_doi_ui.put(("thanh_cong", ket_qua))
            except Exception as loi:
                self.hang_doi_ui.put(("loi", str(loi)))

        threading.Thread(target=viec_nen, daemon=True).start()

    def _ghi_log_tu_thread(self, noi_dung: str) -> None:
        self.hang_doi_ui.put(("log", noi_dung))

    def _doc_hang_doi_ui(self) -> None:
        try:
            while True:
                loai, du_lieu = self.hang_doi_ui.get_nowait()
                self._xu_ly_ket_qua_nen(loai, du_lieu)
        except queue.Empty:
            pass
        self.after(100, self._doc_hang_doi_ui)

    def _xu_ly_ket_qua_nen(self, loai: str, du_lieu: object) -> None:
        if loai == "log":
            self._ghi_log(str(du_lieu))
            return
        if loai == "progress":
            ten_buoc, phan_tram = du_lieu
            self.ten_buoc_hien_tai.set(str(ten_buoc))
            self.tien_trinh.configure(value=int(phan_tram))
            return
        if loai == "queue_progress":
            ma_item, trang_thai, phan_tram, tong_the, ten_buoc = du_lieu
            item = self._tim_item_hang_doi(int(ma_item))
            if item is not None:
                item["trang_thai"] = str(trang_thai)
                item["tien_trinh"] = f"{int(phan_tram)}%"
                self._cap_nhat_dong_hang_doi(item)
            self.ten_buoc_hien_tai.set(str(ten_buoc))
            self.tien_trinh.configure(value=int(tong_the))
            return
        if loai == "queue_update":
            du_lieu_item = du_lieu
            item = self._tim_item_hang_doi(int(du_lieu_item["id"]))
            if item is not None:
                item.update(du_lieu_item)
                self._cap_nhat_dong_hang_doi(item)
            return
        if loai == "queue_result":
            if isinstance(du_lieu, PipelineResult):
                self._hien_thi_ket_qua_pipeline(du_lieu)
            return
        if loai == "queue_done":
            self._ket_thuc_hang_doi()
            return

        self._dat_dang_xu_ly(False)
        if loai == "loi":
            thong_bao = str(du_lieu)
            messagebox.showwarning("Cần kiểm tra lại", thong_bao)
            self._ghi_log(f"Lỗi: {thong_bao}")
            return
        if isinstance(du_lieu, TranscriptionResult):
            self._hien_thi_ket_qua_nhan_dang(du_lieu)
            return
        if isinstance(du_lieu, TranslationResult):
            self._hien_thi_ket_qua_dich(du_lieu)
            return
        if isinstance(du_lieu, PipelineResult):
            self._hien_thi_ket_qua_pipeline(du_lieu)
            return
        if isinstance(du_lieu, dict) and "srt_path" in du_lieu:
            self._hien_thi_ket_qua_srt(du_lieu)
            return
        if isinstance(du_lieu, dict) and "srt_vi_path" in du_lieu:
            self._hien_thi_ket_qua_srt_vi(du_lieu)
            return
        if isinstance(du_lieu, tuple):
            wav, cac_dong = du_lieu
            self.duong_dan_wav.set(str(wav))
            for dong in cac_dong:
                self._ghi_log(str(dong))

    def _hien_thi_ket_qua_nhan_dang(self, ket_qua: TranscriptionResult) -> None:
        self._ghi_log(f"Nhận dạng xong: {len(ket_qua.segments)} segment.")
        self._ghi_log(f"JSON UTF-8: {ket_qua.json_path}")

    def _hien_thi_ket_qua_srt(self, ket_qua: dict) -> None:
        self.duong_dan_srt_zh.set(str(ket_qua["srt_path"]))
        self._hien_thi_preview(str(ket_qua["preview"]))
        self._ghi_log(f"Đã xuất SRT tiếng Trung: {ket_qua['srt_path']}")

    def _hien_thi_ket_qua_srt_vi(self, ket_qua: dict) -> None:
        self.duong_dan_srt_vi.set(str(ket_qua["srt_vi_path"]))
        self._hien_thi_preview(str(ket_qua["preview"]))
        self._ghi_log(f"Đã xuất SRT tiếng Việt: {ket_qua['srt_vi_path']}")

    def _hien_thi_ket_qua_dich(self, ket_qua: TranslationResult) -> None:
        self._ghi_log(f"Dịch thử xong: {len(ket_qua.segments)} segment.")
        for item in self.bang_dich.get_children():
            self.bang_dich.delete(item)
        for segment in ket_qua.segments[:10]:
            self.bang_dich.insert("", "end", values=(segment.index, segment.original_zh, segment.translated_vi))

    def _hien_thi_ket_qua_pipeline(self, ket_qua: PipelineResult) -> None:
        self.duong_dan_wav.set(str(ket_qua.wav_path))
        duong_dan_srt = Path(ket_qua.zh_srt_path).resolve()
        self.duong_dan_srt_zh.set(str(duong_dan_srt))
        self.duong_dan_srt_vi.set(str(duong_dan_srt))
        self.ten_buoc_hien_tai.set("Hoàn thành")
        self.tien_trinh.configure(value=100)
        self._hien_thi_preview(ket_qua.preview_zh)
        self._ghi_log(f"Pipeline hoàn tất. SRT Trung: {duong_dan_srt}")
        for ten_buoc, so_giay in ket_qua.step_times.items():
            self._ghi_log(f"Thời gian - {ten_buoc}: {so_giay:.2f} giây")

    def _ket_thuc_hang_doi(self) -> None:
        self.dang_chay_hang_doi = False
        self.dung_sau_file_hien_tai = False
        self.stop_event_hien_tai = None
        self._dat_dang_xu_ly(False)
        self.nut_dung_sau_file.configure(state=tk.DISABLED)
        self.nut_dung_ngay.configure(state=tk.DISABLED)
        self.ten_buoc_hien_tai.set("Hàng đợi đã xong")
        self._ghi_log("Hàng đợi đã kết thúc.")
        if self.shutdown_when_done.get():
            self._ghi_log("Đã bật tùy chọn tắt máy. Máy tính sẽ tắt sau 60 giây.")
            try:
                subprocess.Popen(["shutdown", "/s", "/t", "60"], shell=False)
            except Exception as loi:
                self._ghi_log(f"Không gọi được lệnh tắt máy: {loi}")

    def _hien_thi_preview(self, noi_dung: str) -> None:
        self.o_preview_srt.configure(state="normal")
        self.o_preview_srt.delete("1.0", tk.END)
        self.o_preview_srt.insert(tk.END, noi_dung)
        self.o_preview_srt.configure(state="disabled")

    def _dat_dang_xu_ly(self, dang_chay: bool) -> None:
        trang_thai = tk.DISABLED if dang_chay else tk.NORMAL
        for ten_nut in (
            "nut_kiem_tra",
            "nut_tach_audio",
            "nut_nhan_dang",
            "nut_xuat_srt_zh",
            "nut_dich_thu",
            "nut_xuat_srt_vi",
            "nut_bat_dau",
            "nut_chon_nhieu_video",
            "nut_thu_lai_loi",
            "nut_chon_vung_ocr",
            "nut_xem_video_hang_doi",
            "nut_chon_vung_ocr_hang_doi",
        ):
            nut = getattr(self, ten_nut, None)
            if nut is not None:
                nut.configure(state=trang_thai)
        self.nut_dung.configure(state=tk.NORMAL if dang_chay else tk.DISABLED)
        if hasattr(self, "nut_dung_sau_file"):
            self.nut_dung_sau_file.configure(state=tk.NORMAL if self.dang_chay_hang_doi else tk.DISABLED)
            self.nut_dung_ngay.configure(state=tk.NORMAL if self.dang_chay_hang_doi else tk.DISABLED)
        if hasattr(self, "nut_xoa_chua_chay"):
            self.nut_xoa_chua_chay.configure(state=tk.NORMAL)
        if dang_chay:
            self.tien_trinh.configure(value=0)
        else:
            self._dong_bo_giao_dien_nhan_dang()

    def _ghi_log(self, noi_dung: str) -> None:
        thoi_gian = datetime.now().strftime("%H:%M:%S")
        self.o_log.configure(state="normal")
        self.o_log.insert(tk.END, f"[{thoi_gian}] {noi_dung}\n")
        self.o_log.see(tk.END)
        self.o_log.configure(state="disabled")

    def _ghi_log_moi_truong(self) -> None:
        try:
            for dong in self.worker.lay_thong_tin_moi_truong():
                self._ghi_log(dong)
        except Exception as loi:
            self._ghi_log(f"Khong kiem tra duoc moi truong Python: {loi}")

    def _ghi_log_moi_truong_nen(self) -> None:
        def viec_nen() -> None:
            try:
                for dong in self.worker.lay_thong_tin_moi_truong():
                    self.hang_doi_ui.put(("log", dong))
            except Exception as loi:
                self.hang_doi_ui.put(("log", f"Khong kiem tra duoc moi truong Python: {loi}"))

        threading.Thread(target=viec_nen, daemon=True).start()


def chay_ung_dung() -> None:
    """Khởi chạy vòng lặp giao diện."""

    ung_dung = SrtMakerApp()
    ung_dung.mainloop()
