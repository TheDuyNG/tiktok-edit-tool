"""Các mô hình dữ liệu dùng chung trong ứng dụng."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SubtitleSegment:
    """Một đoạn phụ đề song ngữ theo thời gian."""

    index: int
    start: float
    end: float
    original_zh: str = ""
    translated_vi: str = ""
    cleaned_text: str = ""
    status: str = "moi"
    warning: str = ""

    def __post_init__(self) -> None:
        if self.end <= self.start:
            raise ValueError("Thời điểm kết thúc phải lớn hơn thời điểm bắt đầu.")
