"""Ghi và kiểm tra file SRT UTF-8."""

from __future__ import annotations

import json
from pathlib import Path

import pysrt

from core.models import SubtitleSegment
from core.srt_validator import chuan_hoa_segments_cho_srt
from core.subtitle_formatter import co_chu_trung, co_dau_tieng_viet, lam_sach_noi_dung_srt, lam_sach_tieng_viet_cho_tts


class SrtWriteError(RuntimeError):
    """Lỗi khi ghi hoặc đọc lại SRT."""


def dinh_dang_moc_thoi_gian(giay: float) -> str:
    """Chuyển số giây sang định dạng HH:MM:SS,mmm của SRT."""

    if giay < 0:
        raise SrtWriteError("Timestamp không được âm.")

    tong_mili_giay = int(round(giay * 1000))
    gio, phan_du = divmod(tong_mili_giay, 3_600_000)
    phut, phan_du = divmod(phan_du, 60_000)
    giay_nguyen, mili_giay = divmod(phan_du, 1000)
    return f"{gio:02}:{phut:02}:{giay_nguyen:02},{mili_giay:03}"


def doc_segments_tu_json(duong_dan_json: Path) -> list[SubtitleSegment]:
    """Đọc danh sách SubtitleSegment từ JSON nhận dạng UTF-8."""

    du_lieu = json.loads(duong_dan_json.read_text(encoding="utf-8"))
    cac_doan = du_lieu.get("segments", [])
    ket_qua: list[SubtitleSegment] = []

    for muc in cac_doan:
        ket_qua.append(
            SubtitleSegment(
                index=int(muc["index"]),
                start=float(muc["start"]),
                end=float(muc["end"]),
                original_zh=str(muc.get("original_zh", "")),
                translated_vi=str(muc.get("translated_vi", "")),
                cleaned_text=str(muc.get("cleaned_text", "")),
                status=str(muc.get("status", "")),
                warning=str(muc.get("warning", "")),
            )
        )

    return ket_qua


def tao_ten_srt_mac_dinh(duong_dan_video: Path, ngon_ngu: str = "zh") -> str:
    """Tạo tên file SRT mặc định theo tên video."""

    ten_goc = duong_dan_video.stem if duong_dan_video and duong_dan_video.stem else "subtitle"
    return f"{ten_goc}_{ngon_ngu}.srt"


def ghi_srt(
    cac_doan: list[SubtitleSegment],
    duong_dan_file: Path,
    truong_noi_dung: str,
    thoi_luong_video: float | None = None,
) -> list[SubtitleSegment]:
    """Ghi file SRT, đọc lại bằng pysrt và trả về segment đã chuẩn hóa."""

    if duong_dan_file.suffix.lower() != ".srt":
        duong_dan_file = duong_dan_file.with_suffix(".srt")

    cac_doan_sach = chuan_hoa_segments_cho_srt(cac_doan, truong_noi_dung, thoi_luong_video)
    cac_khoi: list[str] = []

    for vi_tri, doan in enumerate(cac_doan_sach, start=1):
        noi_dung = lam_sach_noi_dung_srt(str(getattr(doan, truong_noi_dung)))
        cac_khoi.append(
            "\n".join(
                [
                    str(vi_tri),
                    f"{dinh_dang_moc_thoi_gian(doan.start)} --> {dinh_dang_moc_thoi_gian(doan.end)}",
                    noi_dung,
                ]
            )
        )

    duong_dan_file.parent.mkdir(parents=True, exist_ok=True)
    duong_dan_file.write_text("\n\n".join(cac_khoi) + "\n", encoding="utf-8")
    kiem_tra_srt_bang_pysrt(duong_dan_file, cac_doan_sach, truong_noi_dung)
    return cac_doan_sach


def ghi_srt_tieng_trung(
    cac_doan: list[SubtitleSegment],
    duong_dan_video: Path,
    thu_muc_dau_ra: Path,
    thoi_luong_video: float | None = None,
) -> tuple[Path, list[SubtitleSegment]]:
    """Ghi file SRT tiếng Trung với tên mặc định <ten_video>_zh.srt."""

    duong_dan_file = tao_duong_dan_khong_trung(thu_muc_dau_ra / tao_ten_srt_mac_dinh(duong_dan_video, "zh"))
    cac_doan_sach = ghi_srt(cac_doan, duong_dan_file, "original_zh", thoi_luong_video)
    return duong_dan_file, cac_doan_sach


def ghi_srt_tieng_viet(
    cac_doan: list[SubtitleSegment],
    duong_dan_video: Path,
    thu_muc_dau_ra: Path,
    thoi_luong_video: float | None = None,
) -> tuple[Path, Path, list[SubtitleSegment]]:
    """Ghi file <ten_video>_vi.srt và JSON trung gian tối ưu cho TTS."""

    duong_dan_file = tao_duong_dan_khong_trung(thu_muc_dau_ra / tao_ten_srt_mac_dinh(duong_dan_video, "vi"))
    cac_doan_toi_uu = toi_uu_segments_tieng_viet(cac_doan, thoi_luong_video)
    cac_doan_sach = ghi_srt(cac_doan_toi_uu, duong_dan_file, "cleaned_text", thoi_luong_video)
    _kiem_tra_srt_tieng_viet(duong_dan_file, cac_doan_sach)

    json_path = tao_duong_dan_khong_trung(duong_dan_file.with_suffix(".json"))
    _luu_json_trung_gian_tieng_viet(json_path, cac_doan_sach)
    return duong_dan_file, json_path, cac_doan_sach


def tao_duong_dan_khong_trung(duong_dan: Path) -> Path:
    """Thêm số thứ tự nếu file đã tồn tại để không ghi đè kết quả cũ."""

    if not duong_dan.exists():
        return duong_dan

    for so_thu_tu in range(1, 10_000):
        ung_vien = duong_dan.with_name(f"{duong_dan.stem}_{so_thu_tu}{duong_dan.suffix}")
        if not ung_vien.exists():
            return ung_vien

    raise SrtWriteError("Không tìm được tên file chưa tồn tại.")


def toi_uu_segments_tieng_viet(
    cac_doan: list[SubtitleSegment],
    thoi_luong_video: float | None = None,
) -> list[SubtitleSegment]:
    """Làm sạch, gộp block quá ngắn khi an toàn và ghi cảnh báo cần xem xét."""

    da_sap_xep = sorted(cac_doan, key=lambda doan: (doan.start, doan.end))
    tam: list[SubtitleSegment] = []

    for doan in da_sap_xep:
        cleaned = lam_sach_tieng_viet_cho_tts(doan.translated_vi or doan.cleaned_text)
        if not cleaned:
            continue

        warning = doan.warning or ""
        status = "ok"
        if co_chu_trung(cleaned):
            warning = _them_canh_bao(warning, "Bản tiếng Việt còn ký tự Trung.")
            status = "warning"

        if thoi_luong_video is not None and doan.end > thoi_luong_video and doan.end - thoi_luong_video <= 0.08:
            end = thoi_luong_video
        else:
            end = doan.end

        tam.append(
            SubtitleSegment(
                index=len(tam) + 1,
                start=doan.start,
                end=end,
                original_zh=doan.original_zh,
                translated_vi=doan.translated_vi,
                cleaned_text=cleaned,
                status=status,
                warning=warning,
            )
        )

    ket_qua: list[SubtitleSegment] = []
    vi_tri = 0
    while vi_tri < len(tam):
        hien_tai = tam[vi_tri]
        thoi_luong = hien_tai.end - hien_tai.start
        if thoi_luong < 0.8 and vi_tri + 1 < len(tam):
            tiep = tam[vi_tri + 1]
            khoang_cach = tiep.start - hien_tai.end
            van_ban_gop = f"{hien_tai.cleaned_text} {tiep.cleaned_text}".strip()
            thoi_luong_gop = tiep.end - hien_tai.start
            if 0 <= khoang_cach <= 0.35 and thoi_luong_gop <= 6.0 and len(van_ban_gop) <= 120:
                ket_qua.append(
                    SubtitleSegment(
                        index=len(ket_qua) + 1,
                        start=hien_tai.start,
                        end=tiep.end,
                        original_zh=f"{hien_tai.original_zh} {tiep.original_zh}".strip(),
                        translated_vi=f"{hien_tai.translated_vi} {tiep.translated_vi}".strip(),
                        cleaned_text=van_ban_gop,
                        status="ok",
                        warning=_them_canh_bao(hien_tai.warning or tiep.warning, "Đã gộp segment quá ngắn để dễ đọc TTS."),
                    )
                )
                vi_tri += 2
                continue

            hien_tai = _cap_nhat_canh_bao(hien_tai, "Segment dưới 800 ms, chưa gộp vì không an toàn.")

        if thoi_luong > 8.0:
            hien_tai = _cap_nhat_canh_bao(hien_tai, "Segment trên 8 giây, cần xem xét chia thủ công.")
        elif thoi_luong < 1.2:
            hien_tai = _cap_nhat_canh_bao(hien_tai, "Thời lượng dưới mức khuyến nghị 1,2 giây.")

        if len(hien_tai.cleaned_text) > max(80, int((hien_tai.end - hien_tai.start) * 22)):
            hien_tai = _cap_nhat_canh_bao(hien_tai, "Câu có thể quá dài so với thời lượng đọc.")

        ket_qua.append(hien_tai)
        vi_tri += 1

    return [
        SubtitleSegment(
            index=index,
            start=doan.start,
            end=doan.end,
            original_zh=doan.original_zh,
            translated_vi=doan.translated_vi,
            cleaned_text=doan.cleaned_text,
            status=doan.status,
            warning=doan.warning,
        )
        for index, doan in enumerate(ket_qua, start=1)
    ]


def kiem_tra_srt_bang_pysrt(
    duong_dan_file: Path,
    cac_doan_goc: list[SubtitleSegment],
    truong_noi_dung: str,
) -> None:
    """Mở lại bằng pysrt và so sánh số lượng, thời gian, nội dung."""

    try:
        cac_muc = pysrt.open(str(duong_dan_file), encoding="utf-8")
    except Exception as loi:
        raise SrtWriteError(f"Không đọc lại được SRT bằng pysrt: {loi}") from loi

    if len(cac_muc) != len(cac_doan_goc):
        raise SrtWriteError("Số lượng segment đọc lại bằng pysrt không khớp.")

    for muc, doan in zip(cac_muc, cac_doan_goc):
        start_ms = _pysrt_sang_mili_giay(muc.start)
        end_ms = _pysrt_sang_mili_giay(muc.end)
        if start_ms != int(round(doan.start * 1000)) or end_ms != int(round(doan.end * 1000)):
            raise SrtWriteError(f"Timestamp đọc lại không khớp ở segment {doan.index}.")

        noi_dung = lam_sach_noi_dung_srt(str(getattr(doan, truong_noi_dung)))
        if muc.text.strip() != noi_dung:
            raise SrtWriteError(f"Nội dung đọc lại không khớp ở segment {doan.index}.")


def _kiem_tra_srt_tieng_viet(duong_dan_file: Path, cac_doan: list[SubtitleSegment]) -> None:
    """Kiểm tra riêng cho SRT tiếng Việt sau khi đọc lại bằng pysrt."""

    cac_muc = pysrt.open(str(duong_dan_file), encoding="utf-8")
    if len(cac_muc) != len(cac_doan):
        raise SrtWriteError("Số block tiếng Việt đọc lại không khớp.")

    co_dau = False
    for vi_tri, muc in enumerate(cac_muc):
        text = muc.text.strip()
        if not text:
            raise SrtWriteError(f"Block {vi_tri + 1} bị rỗng.")
        if co_chu_trung(text):
            raise SrtWriteError(f"Block {vi_tri + 1} còn chứa chữ Trung.")
        if co_dau_tieng_viet(text):
            co_dau = True
        if vi_tri and muc.start < cac_muc[vi_tri - 1].end:
            raise SrtWriteError(f"Block {vi_tri + 1} bị chồng lấn.")

    if not co_dau:
        raise SrtWriteError("Không phát hiện dấu tiếng Việt trong file SRT.")


def _luu_json_trung_gian_tieng_viet(json_path: Path, cac_doan: list[SubtitleSegment]) -> None:
    du_lieu = {
        "segments": [
            {
                "index": doan.index,
                "start": doan.start,
                "end": doan.end,
                "original_zh": doan.original_zh,
                "translated_vi": doan.translated_vi,
                "cleaned_text": doan.cleaned_text,
                "warning": doan.warning,
                "validation_status": doan.status or "ok",
            }
            for doan in cac_doan
        ]
    }
    json_path.write_text(json.dumps(du_lieu, ensure_ascii=False, indent=2), encoding="utf-8")


def tao_preview_srt(cac_doan: list[SubtitleSegment], truong_noi_dung: str = "original_zh", so_luong: int = 10) -> str:
    """Tạo chuỗi preview các block SRT đầu tiên."""

    cac_khoi: list[str] = []
    for doan in cac_doan[:so_luong]:
        cac_khoi.append(
            "\n".join(
                [
                    str(doan.index),
                    f"{dinh_dang_moc_thoi_gian(doan.start)} --> {dinh_dang_moc_thoi_gian(doan.end)}",
                    lam_sach_noi_dung_srt(str(getattr(doan, truong_noi_dung))),
                ]
            )
        )
    return "\n\n".join(cac_khoi)


def _pysrt_sang_mili_giay(thoi_gian: pysrt.SubRipTime) -> int:
    return (
        thoi_gian.hours * 3_600_000
        + thoi_gian.minutes * 60_000
        + thoi_gian.seconds * 1000
        + thoi_gian.milliseconds
    )


def _them_canh_bao(cu: str, moi: str) -> str:
    if not cu:
        return moi
    if moi in cu:
        return cu
    return f"{cu} {moi}"


def _cap_nhat_canh_bao(doan: SubtitleSegment, canh_bao: str) -> SubtitleSegment:
    return SubtitleSegment(
        index=doan.index,
        start=doan.start,
        end=doan.end,
        original_zh=doan.original_zh,
        translated_vi=doan.translated_vi,
        cleaned_text=doan.cleaned_text,
        status="warning",
        warning=_them_canh_bao(doan.warning, canh_bao),
    )
