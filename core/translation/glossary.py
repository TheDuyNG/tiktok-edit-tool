"""Glossary dùng thống nhất toàn video."""

from __future__ import annotations

import hashlib


def doc_glossary(noi_dung: str) -> dict[str, str]:
    """Đọc glossary dạng mỗi dòng: tiếng Trung = tiếng Việt."""

    glossary: dict[str, str] = {}
    for dong in noi_dung.splitlines():
        dong = dong.strip()
        if not dong or dong.startswith("#"):
            continue

        if "=" in dong:
            trai, phai = dong.split("=", 1)
        elif ":" in dong:
            trai, phai = dong.split(":", 1)
        else:
            continue

        khoa = trai.strip()
        gia_tri = phai.strip()
        if khoa and gia_tri:
            glossary[khoa] = gia_tri

    return glossary


def glossary_version(noi_dung: str) -> str:
    """Tạo version ổn định để đưa vào cache."""

    return hashlib.sha256(noi_dung.strip().encode("utf-8")).hexdigest()[:16]


def ap_dung_glossary_vao_ban_dich(ban_dich: str, glossary: dict[str, str]) -> str:
    """Thay các thuật ngữ còn sót bằng bản Việt hóa trong glossary."""

    ket_qua = ban_dich
    for tieng_trung, tieng_viet in glossary.items():
        ket_qua = ket_qua.replace(tieng_trung, tieng_viet)
    return ket_qua
