"""Định dạng nội dung phụ đề để xuất SRT và dùng cho TTS."""

from __future__ import annotations

import re


MAU_HTML = re.compile(r"<[^>]+>")
MAU_ASS = re.compile(r"\{\\[^}]+\}")
MAU_MARKDOWN = re.compile(r"[*_`#>\[\]]")
MAU_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
MAU_NHAN_AM_THANH = re.compile(
    r"\s*[\[\(（【]\s*(âm nhạc|nhạc|cười|tiếng cười|tiếng động|ồn|applause|music|laughs?)\s*[\]\)）】]\s*",
    re.IGNORECASE,
)


def lam_sach_noi_dung_srt(van_ban: str) -> str:
    """Làm sạch nội dung SRT, ưu tiên một dòng và không giữ mã định dạng."""

    noi_dung = MAU_URL.sub("", van_ban)
    noi_dung = MAU_NHAN_AM_THANH.sub(" ", noi_dung)
    noi_dung = MAU_HTML.sub("", noi_dung)
    noi_dung = MAU_ASS.sub("", noi_dung)
    noi_dung = MAU_MARKDOWN.sub("", noi_dung)
    noi_dung = " ".join(noi_dung.split())
    return noi_dung.strip()


def lam_sach_tieng_viet_cho_tts(van_ban: str) -> str:
    """Làm sạch bản dịch tiếng Việt để đọc tự nhiên hơn bằng TTS."""

    noi_dung = lam_sach_noi_dung_srt(van_ban)
    noi_dung = re.sub(r"\s+([,.!?;:])", r"\1", noi_dung)
    noi_dung = re.sub(r"([,.!?;:]){2,}", r"\1", noi_dung)
    noi_dung = re.sub(r"\b(\d+)\s*kg\b", r"\1 ki-lô-gam", noi_dung, flags=re.IGNORECASE)
    noi_dung = re.sub(r"\b(\d+)\s*km\b", r"\1 ki-lô-mét", noi_dung, flags=re.IGNORECASE)
    noi_dung = re.sub(r"\b(\d+)\s*h\b", r"\1 giờ", noi_dung, flags=re.IGNORECASE)
    return noi_dung.strip()


def co_chu_trung(noi_dung: str) -> bool:
    """Kiểm tra chuỗi còn ký tự Trung hay không."""

    return any("\u4e00" <= ky_tu <= "\u9fff" for ky_tu in noi_dung)


def co_dau_tieng_viet(noi_dung: str) -> bool:
    """Kiểm tra có dấu tiếng Việt trong văn bản."""

    dau = "ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ"
    return any(ky_tu.lower() in dau for ky_tu in noi_dung)


def lam_sach_cho_tts(van_ban: str) -> str:
    """Tương thích với tên hàm cũ."""

    return lam_sach_tieng_viet_cho_tts(van_ban)
