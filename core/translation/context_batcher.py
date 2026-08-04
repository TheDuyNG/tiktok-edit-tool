"""Tạo batch dịch có ngữ cảnh nhiều segment."""

from __future__ import annotations

from core.models import SubtitleSegment


def tao_batch_theo_ngu_canh(cac_doan: list[SubtitleSegment], kich_thuoc: int) -> list[list[SubtitleSegment]]:
    """Chia segment thành batch liên tiếp, không gộp và không bỏ segment."""

    if kich_thuoc <= 0:
        kich_thuoc = 8

    return [cac_doan[vi_tri : vi_tri + kich_thuoc] for vi_tri in range(0, len(cac_doan), kich_thuoc)]


def dinh_dang_batch_gui_model(cac_doan: list[SubtitleSegment]) -> str:
    """Định dạng batch theo mẫu [SEG_0001] nội dung tiếng Trung."""

    return "\n".join(f"[SEG_{doan.index:04d}] {doan.original_zh.strip()}" for doan in cac_doan)


def phan_tich_ket_qua_model(noi_dung: str) -> dict[int, str]:
    """Đọc kết quả dạng [SEG_0001] bản dịch tiếng Việt."""

    ket_qua: dict[int, str] = {}
    for dong in noi_dung.splitlines():
        dong = dong.strip()
        if not dong.startswith("[SEG_") or "]" not in dong:
            continue

        nhan, ban_dich = dong.split("]", 1)
        ma_so = nhan.replace("[SEG_", "").strip()
        if not ma_so.isdigit():
            continue

        chi_so = int(ma_so)
        if chi_so in ket_qua:
            raise ValueError(f"ID SEG_{chi_so:04d} bị trùng.")
        ket_qua[chi_so] = ban_dich.strip()

    return ket_qua
