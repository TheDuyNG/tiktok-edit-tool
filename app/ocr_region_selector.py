"""Small Tkinter dialog for selecting the OCR subtitle region."""

from __future__ import annotations

import tempfile
import tkinter as tk
import threading
from pathlib import Path
from tkinter import messagebox, ttk

from core.ffmpeg_service import chay_lenh, lay_thoi_luong_video, tim_ffmpeg


class OcrRegionSelector(tk.Toplevel):
    """Show a video frame and return a normalized crop rectangle."""

    def __init__(
        self,
        parent: tk.Misc,
        video_path: Path,
        initial_region: tuple[float, float, float, float],
    ) -> None:
        super().__init__(parent)
        self.title("Chọn vùng OCR phụ đề Trung")
        self.geometry("980x720")
        self.minsize(760, 520)
        self.transient(parent)
        self.grab_set()

        self.video_path = video_path
        self.result: tuple[float, float, float, float] | None = None
        self._drag_start: tuple[int, int] | None = None
        self._rect_id: int | None = None
        self._image: tk.PhotoImage | None = None
        self._image_scale = 1.0
        self._image_offset = (0, 0)
        self._image_size = (1, 1)
        self._natural_size = (1, 1)
        self._region = initial_region
        self._duration = 0.0
        self._playing = False
        self._play_time = 0.0
        self._play_generation = 0
        self._play_after_id: str | None = None
        self._frame_path = Path(tempfile.gettempdir()) / f"srt_maker_ocr_preview_{abs(hash((str(video_path), id(self))))}.png"

        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self, padding=(10, 10, 10, 4))
        toolbar.grid(row=0, column=0, sticky="ew")
        toolbar.columnconfigure(5, weight=1)
        ttk.Label(toolbar, text="Kéo chuột quanh vùng chữ Trung cần quét").grid(row=0, column=0, sticky="w")
        ttk.Button(toolbar, text="Vùng dưới", command=self._dat_vung_duoi).grid(row=0, column=1, padx=(12, 0))
        ttk.Button(toolbar, text="Toàn màn hình", command=self._dat_toan_man_hinh).grid(row=0, column=2, padx=(8, 0))
        self.nut_chay_thu = ttk.Button(toolbar, text="Chạy thử video", command=self._bat_dau_chay_thu)
        self.nut_chay_thu.grid(row=0, column=3, padx=(12, 0))
        self.nut_dung_thu = ttk.Button(toolbar, text="Dừng thử", command=self._dung_chay_thu, state=tk.DISABLED)
        self.nut_dung_thu.grid(row=0, column=4, padx=(8, 0))
        self.nhan_thoi_gian = ttk.Label(toolbar, text="00:00.0 / 00:00.0")
        self.nhan_thoi_gian.grid(row=0, column=5, sticky="e", padx=(12, 0))

        self.canvas = tk.Canvas(self, bg="#111111", highlightthickness=0)
        self.canvas.grid(row=1, column=0, sticky="nsew", padx=10, pady=8)
        self.canvas.bind("<ButtonPress-1>", self._bat_dau_keo)
        self.canvas.bind("<B1-Motion>", self._dang_keo)
        self.canvas.bind("<ButtonRelease-1>", self._ket_thuc_keo)
        self.canvas.bind("<Configure>", lambda _event: self._ve_lai())

        bottom = ttk.Frame(self, padding=(10, 4, 10, 10))
        bottom.grid(row=2, column=0, sticky="ew")
        bottom.columnconfigure(0, weight=1)
        self.status = ttk.Label(bottom, text="")
        self.status.grid(row=0, column=0, sticky="w")
        ttk.Button(bottom, text="Hủy", command=self._huy).grid(row=0, column=1, padx=(8, 0))
        ttk.Button(bottom, text="Dùng vùng này", command=self._chap_nhan).grid(row=0, column=2, padx=(8, 0))

        self.protocol("WM_DELETE_WINDOW", self._huy)
        self._tai_frame_preview()
        self.after(50, self._ve_lai)

    def _tai_frame_preview(self) -> None:
        self._duration = lay_thoi_luong_video(self.video_path)
        seek = min(max(self._duration * 0.1, 3.0), max(self._duration - 1.0, 0.0))
        self._tao_frame_tai_thoi_diem(seek, self._frame_path)
        self._tai_anh(self._frame_path)
        self._cap_nhat_thoi_gian(seek)

    def _tao_frame_tai_thoi_diem(self, seek: float, frame_path: Path) -> None:
        ffmpeg = tim_ffmpeg()
        lenh = [
            ffmpeg,
            "-y",
            "-ss",
            f"{seek:.3f}",
            "-i",
            str(self.video_path),
            "-vf",
            "scale=960:-2",
            "-frames:v",
            "1",
            str(frame_path),
        ]
        ket_qua = chay_lenh(lenh, timeout=60)
        if ket_qua.returncode != 0 or not frame_path.exists():
            raise RuntimeError(f"Không tạo được preview video: {ket_qua.stderr[-500:]}")

    def _tai_anh(self, frame_path: Path) -> None:
        self._image = tk.PhotoImage(file=str(frame_path))
        self._natural_size = (max(1, self._image.width()), max(1, self._image.height()))

    def _bat_dau_chay_thu(self) -> None:
        if self._playing:
            return
        self._playing = True
        self._play_time = 0.0
        self._play_generation += 1
        generation = self._play_generation
        self.nut_chay_thu.configure(state=tk.DISABLED)
        self.nut_dung_thu.configure(state=tk.NORMAL)
        self._nap_frame_chay_thu(generation)

    def _dung_chay_thu(self) -> None:
        self._playing = False
        self._play_generation += 1
        if self._play_after_id is not None:
            self.after_cancel(self._play_after_id)
            self._play_after_id = None
        self.nut_chay_thu.configure(state=tk.NORMAL)
        self.nut_dung_thu.configure(state=tk.DISABLED)

    def _nap_frame_chay_thu(self, generation: int) -> None:
        if not self._playing or generation != self._play_generation:
            return
        if self._play_time >= self._duration:
            self._dung_chay_thu()
            return
        seek = self._play_time
        threading.Thread(
            target=self._nap_frame_chay_thu_nen,
            args=(seek, generation),
            daemon=True,
        ).start()

    def _nap_frame_chay_thu_nen(self, seek: float, generation: int) -> None:
        try:
            self._tao_frame_tai_thoi_diem(seek, self._frame_path)
            loi = ""
        except Exception as exc:
            loi = str(exc)
        try:
            self.after(0, self._hien_frame_chay_thu, seek, generation, loi)
        except tk.TclError:
            pass

    def _hien_frame_chay_thu(self, seek: float, generation: int, loi: str) -> None:
        if not self._playing or generation != self._play_generation:
            return
        if loi:
            self._dung_chay_thu()
            messagebox.showwarning("Preview video", loi, parent=self)
            return
        try:
            self._tai_anh(self._frame_path)
            self._ve_lai()
        except Exception as exc:
            self._dung_chay_thu()
            messagebox.showwarning("Preview video", f"Không hiển thị được frame: {exc}", parent=self)
            return
        self._cap_nhat_thoi_gian(seek)
        self._play_time += 0.25
        self._play_after_id = self.after(40, self._nap_frame_chay_thu, generation)

    def _cap_nhat_thoi_gian(self, current: float) -> None:
        def dinh_dang(giay: float) -> str:
            phut = int(max(0.0, giay) // 60)
            giay_le = max(0.0, giay) - phut * 60
            return f"{phut:02d}:{giay_le:04.1f}"

        self.nhan_thoi_gian.configure(text=f"{dinh_dang(current)} / {dinh_dang(self._duration)}")

    def _ve_lai(self) -> None:
        if self._image is None:
            return
        self.canvas.delete("all")
        cw = max(1, self.canvas.winfo_width())
        ch = max(1, self.canvas.winfo_height())
        iw, ih = self._natural_size
        display_w = iw
        display_h = ih
        offset_x = max(0, (cw - display_w) // 2)
        offset_y = max(0, (ch - display_h) // 2)
        self._image_scale = 1.0
        self._image_offset = (offset_x, offset_y)
        self._image_size = (display_w, display_h)

        # Tk PhotoImage cannot be resized smoothly without extra packages, so keep
        # native pixels and fit the dialog around it when possible.
        self.canvas.create_image(offset_x, offset_y, image=self._image, anchor="nw")
        self._ve_rect_tu_region()

    def _ve_rect_tu_region(self) -> None:
        x1, y1, x2, y2 = self._region_to_canvas(self._region)
        self._rect_id = self.canvas.create_rectangle(x1, y1, x2, y2, outline="#00e676", width=3)
        self._cap_nhat_status()

    def _region_to_canvas(self, region: tuple[float, float, float, float]) -> tuple[int, int, int, int]:
        left, top, right, bottom = region
        ox, oy = self._image_offset
        dw, dh = self._image_size
        return (
            int(ox + left * dw),
            int(oy + top * dh),
            int(ox + right * dw),
            int(oy + bottom * dh),
        )

    def _canvas_to_region(self, x1: int, y1: int, x2: int, y2: int) -> tuple[float, float, float, float]:
        ox, oy = self._image_offset
        dw, dh = self._image_size
        left = (min(x1, x2) - ox) / dw
        right = (max(x1, x2) - ox) / dw
        top = (min(y1, y2) - oy) / dh
        bottom = (max(y1, y2) - oy) / dh
        return (
            max(0.0, min(1.0, left)),
            max(0.0, min(1.0, top)),
            max(0.0, min(1.0, right)),
            max(0.0, min(1.0, bottom)),
        )

    def _bat_dau_keo(self, event: tk.Event) -> None:
        self._drag_start = (int(event.x), int(event.y))
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
            self._rect_id = None

    def _dang_keo(self, event: tk.Event) -> None:
        if self._drag_start is None:
            return
        x1, y1 = self._drag_start
        if self._rect_id is not None:
            self.canvas.delete(self._rect_id)
        self._rect_id = self.canvas.create_rectangle(x1, y1, int(event.x), int(event.y), outline="#00e676", width=3)

    def _ket_thuc_keo(self, event: tk.Event) -> None:
        if self._drag_start is None:
            return
        x1, y1 = self._drag_start
        self._drag_start = None
        region = self._canvas_to_region(x1, y1, int(event.x), int(event.y))
        left, top, right, bottom = region
        if right - left < 0.03 or bottom - top < 0.03:
            messagebox.showinfo("Vùng OCR", "Vùng chọn quá nhỏ, hãy kéo rộng quanh dòng phụ đề.")
            self._ve_lai()
            return
        self._region = region
        self._ve_lai()

    def _dat_vung_duoi(self) -> None:
        self._region = (0.0, 0.72, 1.0, 1.0)
        self._ve_lai()

    def _dat_toan_man_hinh(self) -> None:
        self._region = (0.0, 0.0, 1.0, 1.0)
        self._ve_lai()

    def _chap_nhan(self) -> None:
        self._dung_chay_thu()
        left, top, right, bottom = self._region
        if right <= left or bottom <= top:
            messagebox.showwarning("Vùng OCR", "Vùng OCR chưa hợp lệ.")
            return
        self.result = self._region
        self.destroy()

    def _huy(self) -> None:
        self._dung_chay_thu()
        self.result = None
        self.destroy()

    def _cap_nhat_status(self) -> None:
        left, top, right, bottom = self._region
        self.status.configure(
            text=f"Vùng OCR: trái {left:.3f}, trên {top:.3f}, phải {right:.3f}, dưới {bottom:.3f}"
        )


def chon_vung_ocr(
    parent: tk.Misc,
    video_path: Path,
    initial_region: tuple[float, float, float, float],
) -> tuple[float, float, float, float] | None:
    dialog = OcrRegionSelector(parent, video_path, initial_region)
    parent.wait_window(dialog)
    return dialog.result
