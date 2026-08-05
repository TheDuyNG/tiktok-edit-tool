"""Kiểm tra và chuẩn hóa dữ liệu phụ đề trước khi xuất file SRT."""

from __future__ import annotations

import re
from dataclasses import replace

from core.models import SubtitleSegment
from core.subtitle_formatter import lam_sach_noi_dung_srt


class SrtValidationError(ValueError):
    """Lỗi dữ liệu khiến không thể xuất SRT hợp lệ."""


def chuan_hoa_segments_cho_srt(
    cac_doan: list[SubtitleSegment],
    truong_noi_dung: str = "original_zh",
    thoi_luong_video: float | None = None,
    nguong_chong_lan_nho: float = 0.08,
    nguong_lap_lien_tiep: float = 1.0,
    nguong_lech_duoi_video: float = 2.0,
) -> list[SubtitleSegment]:
    """Sắp xếp, bỏ rỗng, đánh số lại và xử lý chồng lấn nhỏ."""

    ket_qua: list[SubtitleSegment] = []
    cac_doan_sap_xep = _tach_va_lam_sach_segments_dai(
        sorted(cac_doan, key=lambda doan: (doan.start, doan.end)),
        truong_noi_dung,
    )
    cac_cau_lap_bat_thuong = _tim_cau_lap_bat_thuong(cac_doan_sap_xep, truong_noi_dung)
    cac_cau_lap_da_giu: set[str] = set()
    noi_dung_da_xet_truoc = ""
    end_da_xet_truoc: float | None = None

    for doan in cac_doan_sap_xep:
        noi_dung = lam_sach_noi_dung_srt(str(getattr(doan, truong_noi_dung, "")))
        if not noi_dung:
            continue

        start = float(doan.start)
        end = float(doan.end)

        if start < 0 or end < 0:
            raise SrtValidationError(f"Đoạn {doan.index} có timestamp âm.")
        if end <= start:
            raise SrtValidationError(f"Đoạn {doan.index} có thời điểm kết thúc không lớn hơn bắt đầu.")
        if thoi_luong_video is not None and end > thoi_luong_video:
            if end - thoi_luong_video <= nguong_lech_duoi_video and thoi_luong_video > start:
                end = thoi_luong_video
            else:
                raise SrtValidationError(f"Đoạn {doan.index} vượt thời lượng video.")

        if ket_qua and start < ket_qua[-1].end:
            do_lech = ket_qua[-1].end - start
            if do_lech <= nguong_chong_lan_nho and start > ket_qua[-1].start:
                ket_qua[-1] = replace(ket_qua[-1], end=start)
            else:
                raise SrtValidationError(f"Đoạn {doan.index} bị chồng lấn quá lớn.")

        if ket_qua and end <= ket_qua[-1].end:
            raise SrtValidationError(f"Đoạn {doan.index} không đúng thứ tự thời gian.")

        if ket_qua and _xu_ly_lap_bao_ham_lien_tiep(ket_qua, noi_dung, truong_noi_dung, start, nguong_lap_lien_tiep):
            noi_dung_da_xet_truoc = noi_dung
            end_da_xet_truoc = end
            continue

        if _la_noi_dung_lap_vua_xet(noi_dung, noi_dung_da_xet_truoc, start, end_da_xet_truoc, nguong_lap_lien_tiep):
            end_da_xet_truoc = end
            continue

        if noi_dung in cac_cau_lap_bat_thuong and noi_dung in cac_cau_lap_da_giu:
            noi_dung_da_xet_truoc = noi_dung
            end_da_xet_truoc = end
            continue

        if ket_qua and _la_doan_lap_lien_tiep(noi_dung, ket_qua[-1], truong_noi_dung, start, nguong_lap_lien_tiep):
            noi_dung_da_xet_truoc = noi_dung
            end_da_xet_truoc = end
            continue

        noi_dung_da_xet_truoc = noi_dung
        end_da_xet_truoc = end
        if noi_dung in cac_cau_lap_bat_thuong:
            cac_cau_lap_da_giu.add(noi_dung)
        ket_qua.append(
            SubtitleSegment(
                index=len(ket_qua) + 1,
                start=start,
                end=end,
                original_zh=noi_dung if truong_noi_dung == "original_zh" else doan.original_zh,
                translated_vi=noi_dung if truong_noi_dung == "translated_vi" else doan.translated_vi,
                cleaned_text=doan.cleaned_text,
                status=doan.status,
                warning=doan.warning,
            )
        )

    if not ket_qua:
        raise SrtValidationError("Không có segment hợp lệ để xuất SRT.")

    return ket_qua


def _la_doan_lap_lien_tiep(
    noi_dung: str,
    doan_truoc: SubtitleSegment,
    truong_noi_dung: str,
    start: float,
    nguong_lap_lien_tiep: float,
) -> bool:
    """Bá» segment láº·p do nháº­n dáº¡ng náº¿u giá»‘ng há»‡t dÃ²ng trÆ°á»›c vÃ  xuáº¥t hiá»‡n quÃ¡ sÃ¡t."""

    noi_dung_truoc = lam_sach_noi_dung_srt(str(getattr(doan_truoc, truong_noi_dung, "")))
    khoang_cach = start - doan_truoc.end
    return noi_dung == noi_dung_truoc and 0 <= khoang_cach <= nguong_lap_lien_tiep


def _tim_cau_lap_bat_thuong(cac_doan: list[SubtitleSegment], truong_noi_dung: str) -> set[str]:
    """Tìm câu bị lặp dày đặc trong thời gian ngắn, thường là lỗi nhận dạng."""

    moc_theo_noi_dung: dict[str, list[float]] = {}
    for doan in cac_doan:
        noi_dung = lam_sach_noi_dung_srt(str(getattr(doan, truong_noi_dung, "")))
        if len(noi_dung) < 6:
            continue
        moc_theo_noi_dung.setdefault(noi_dung, []).append(float(doan.start))

    ket_qua: set[str] = set()
    for noi_dung, cac_moc in moc_theo_noi_dung.items():
        if len(cac_moc) >= 5 and max(cac_moc) - min(cac_moc) <= 120:
            ket_qua.add(noi_dung)
    return ket_qua


def _la_noi_dung_lap_vua_xet(
    noi_dung: str,
    noi_dung_truoc: str,
    start: float,
    end_truoc: float | None,
    nguong_lap_lien_tiep: float,
) -> bool:
    """Nháº­n diá»‡n chuá»—i láº·p liÃªn tá»¥c ká»ƒ cáº£ khi cÃ¡c segment trÆ°á»›c Ä‘Ã£ bá»‹ bá»."""

    if end_truoc is None:
        return False
    khoang_cach = start - end_truoc
    return noi_dung == noi_dung_truoc and 0 <= khoang_cach <= nguong_lap_lien_tiep


def kiem_tra_cac_doan(cac_doan: list[SubtitleSegment]) -> list[str]:
    """Trả về danh sách cảnh báo về thứ tự và thời lượng phụ đề."""

    canh_bao: list[str] = []
    moc_ket_thuc_truoc = 0.0

    for doan in cac_doan:
        if doan.start < moc_ket_thuc_truoc:
            canh_bao.append(f"Đoạn {doan.index} bị chồng thời gian với đoạn trước.")
        if not doan.original_zh.strip() and not doan.translated_vi.strip():
            canh_bao.append(f"Đoạn {doan.index} chưa có nội dung.")
        moc_ket_thuc_truoc = doan.end

    return canh_bao


def _tach_va_lam_sach_segments_dai(
    cac_doan: list[SubtitleSegment],
    truong_noi_dung: str,
    max_ky_tu: int = 32,
    max_thoi_luong: float = 4.0,
) -> list[SubtitleSegment]:
    """Cat segment qua dai va loai lap sat ranh gioi truoc khi ghi SRT."""

    ket_qua: list[SubtitleSegment] = []
    noi_dung_truoc = ""
    end_truoc: float | None = None

    for doan in cac_doan:
        noi_dung = lam_sach_noi_dung_srt(str(getattr(doan, truong_noi_dung, "")))
        if not noi_dung:
            continue

        start = float(doan.start)
        end = float(doan.end)
        if end <= start:
            ket_qua.append(doan)
            continue

        if end_truoc is not None and 0 <= start - end_truoc <= 1.0:
            noi_dung = _bo_phan_lap_voi_doan_truoc(noi_dung, noi_dung_truoc)
            if not noi_dung:
                end_truoc = end
                continue

        cac_manh = _tach_noi_dung_theo_nhip_doc(noi_dung, max_ky_tu)
        if len(cac_manh) == 1:
            cac_manh = _tach_them_neu_con_dai(cac_manh[0], end - start, max_ky_tu, max_thoi_luong)

        for manh in cac_manh:
            ket_qua.append(_tao_doan_voi_noi_dung(doan, manh, truong_noi_dung, start, end))

        noi_dung_truoc = noi_dung
        end_truoc = end

    return _phan_bo_lai_thoi_gian(ket_qua, truong_noi_dung)


def _tach_them_neu_con_dai(noi_dung: str, thoi_luong: float, max_ky_tu: int, max_thoi_luong: float) -> list[str]:
    if len(noi_dung) <= max_ky_tu:
        return [noi_dung]
    so_manh = max(1, int((len(noi_dung) + max_ky_tu - 1) // max_ky_tu))
    so_manh = max(so_manh, int((thoi_luong + max_thoi_luong - 0.001) // max_thoi_luong))
    if so_manh <= 1:
        return [noi_dung]
    return _cat_deu_theo_ky_tu(noi_dung, so_manh)


def _tach_noi_dung_theo_nhip_doc(noi_dung: str, max_ky_tu: int) -> list[str]:
    cac_manh = [item.strip() for item in re.split(r"(?<=[。！？!?；;])\s*", noi_dung) if item.strip()]
    if len(cac_manh) <= 1:
        cac_manh = [item.strip() for item in re.split(r"(?<=[，、,])\s*", noi_dung) if item.strip()]

    ket_qua: list[str] = []
    for manh in cac_manh or [noi_dung]:
        if len(manh) <= max_ky_tu:
            ket_qua.append(manh)
        else:
            ket_qua.extend(_cat_theo_cum_ngan(manh, max_ky_tu))
    return ket_qua or [noi_dung]


def _cat_theo_cum_ngan(noi_dung: str, max_ky_tu: int) -> list[str]:
    cac_tu = [item for item in re.split(r"(\s+)", noi_dung) if item]
    if len(cac_tu) > 1 and any(item.isspace() for item in cac_tu):
        ket_qua: list[str] = []
        hien_tai = ""
        for item in cac_tu:
            if len((hien_tai + item).strip()) > max_ky_tu and hien_tai.strip():
                ket_qua.append(hien_tai.strip())
                hien_tai = item
            else:
                hien_tai += item
        if hien_tai.strip():
            ket_qua.append(hien_tai.strip())
        return ket_qua

    return [noi_dung[i : i + max_ky_tu] for i in range(0, len(noi_dung), max_ky_tu)]


def _cat_deu_theo_ky_tu(noi_dung: str, so_manh: int) -> list[str]:
    do_dai = max(1, (len(noi_dung) + so_manh - 1) // so_manh)
    return [noi_dung[i : i + do_dai].strip() for i in range(0, len(noi_dung), do_dai) if noi_dung[i : i + do_dai].strip()]


def _tao_doan_voi_noi_dung(
    doan: SubtitleSegment,
    noi_dung: str,
    truong_noi_dung: str,
    start: float,
    end: float,
) -> SubtitleSegment:
    gia_tri = {
        "index": doan.index,
        "start": start,
        "end": end,
        "original_zh": doan.original_zh,
        "translated_vi": doan.translated_vi,
        "cleaned_text": doan.cleaned_text,
        "status": doan.status,
        "warning": doan.warning,
    }
    gia_tri[truong_noi_dung] = noi_dung
    return SubtitleSegment(**gia_tri)


def _phan_bo_lai_thoi_gian(cac_doan: list[SubtitleSegment], truong_noi_dung: str) -> list[SubtitleSegment]:
    ket_qua: list[SubtitleSegment] = []
    nhom: list[SubtitleSegment] = []

    def flush() -> None:
        if not nhom:
            return
        if len(nhom) == 1:
            ket_qua.append(nhom[0])
            nhom.clear()
            return

        start = nhom[0].start
        end = nhom[0].end
        tong = max(1, sum(len(lam_sach_noi_dung_srt(str(getattr(item, truong_noi_dung, "")))) for item in nhom))
        moc = start
        for vi_tri, item in enumerate(nhom):
            if vi_tri == len(nhom) - 1:
                moc_moi = end
            else:
                ty_le = len(lam_sach_noi_dung_srt(str(getattr(item, truong_noi_dung, "")))) / tong
                moc_moi = min(end, moc + (end - start) * ty_le)
            if moc_moi <= moc:
                moc_moi = min(end, moc + 0.05)
            ket_qua.append(replace(item, start=moc, end=moc_moi))
            moc = moc_moi
        nhom.clear()

    for doan in cac_doan:
        if nhom and (doan.start != nhom[0].start or doan.end != nhom[0].end):
            flush()
        nhom.append(doan)
    flush()
    return ket_qua


def _bo_phan_lap_voi_doan_truoc(noi_dung: str, noi_dung_truoc: str) -> str:
    truoc = _rut_gon_noi_dung(noi_dung_truoc)
    hien_tai = _rut_gon_noi_dung(noi_dung)
    if len(truoc) < 6 or not hien_tai:
        return noi_dung
    if truoc == hien_tai:
        return ""
    if truoc in hien_tai and len(hien_tai) >= len(truoc) + 6:
        return noi_dung.replace(noi_dung_truoc, "", 1).strip(" ，,。.!！?？")
    return noi_dung


def _xu_ly_lap_bao_ham_lien_tiep(
    ket_qua: list[SubtitleSegment],
    noi_dung: str,
    truong_noi_dung: str,
    start: float,
    nguong_lap_lien_tiep: float,
) -> bool:
    truoc = ket_qua[-1]
    noi_dung_truoc = lam_sach_noi_dung_srt(str(getattr(truoc, truong_noi_dung, "")))
    khoang_cach = start - truoc.end
    if not (0 <= khoang_cach <= nguong_lap_lien_tiep):
        return False

    rut_gon_truoc = _rut_gon_noi_dung(noi_dung_truoc)
    rut_gon_hien_tai = _rut_gon_noi_dung(noi_dung)
    if len(rut_gon_truoc) < 6 or len(rut_gon_hien_tai) < 6:
        return False
    if rut_gon_hien_tai in rut_gon_truoc:
        return True
    if rut_gon_truoc in rut_gon_hien_tai and len(rut_gon_hien_tai) >= len(rut_gon_truoc) + 6:
        ket_qua.pop()
    return False


def _rut_gon_noi_dung(noi_dung: str) -> str:
    return re.sub(r"\s+|[，。,.!?！？、：:；;\"“”‘’\-—…]", "", noi_dung)
