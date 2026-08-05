"""Validator cho kết quả dịch theo ID segment."""

from __future__ import annotations

from core.models import SubtitleSegment


class TranslationValidationError(ValueError):
    """Kết quả dịch không đạt yêu cầu."""


def ty_le_chu_trung(noi_dung: str) -> float:
    """Tính tỷ lệ ký tự Trung trong bản dịch."""

    ky_tu = [ky for ky in noi_dung if not ky.isspace()]
    if not ky_tu:
        return 1.0

    so_chu_trung = sum(1 for ky in ky_tu if "\u4e00" <= ky <= "\u9fff")
    return so_chu_trung / len(ky_tu)


def kiem_tra_ket_qua_batch(cac_doan: list[SubtitleSegment], ban_dich: dict[int, str]) -> None:
    """Kiểm tra đủ ID, đúng thứ tự, không trùng, không rỗng."""

    id_vao = [doan.index for doan in cac_doan]
    id_ra = list(ban_dich.keys())

    if len(id_ra) != len(set(id_ra)):
        raise TranslationValidationError("Kết quả dịch có ID bị trùng.")
    if len(id_ra) != len(id_vao):
        raise TranslationValidationError("Số segment đầu ra không bằng đầu vào.")
    if id_ra != id_vao:
        raise TranslationValidationError("ID đầu ra thiếu, thừa hoặc sai thứ tự.")

    for doan in cac_doan:
        noi_dung = ban_dich.get(doan.index, "").strip()
        if not noi_dung:
            raise TranslationValidationError(f"SEG_{doan.index:04d} có bản dịch rỗng.")
        if ty_le_chu_trung(noi_dung) > 0.25:
            raise TranslationValidationError(f"SEG_{doan.index:04d} còn quá nhiều chữ Trung.")
