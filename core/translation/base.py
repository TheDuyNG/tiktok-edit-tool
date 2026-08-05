"""Kiểu dữ liệu nền cho module dịch."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from core.models import SubtitleSegment


@dataclass(frozen=True)
class TranslationConfig:
    """Cấu hình dịch Trung sang Việt."""

    provider: str = "gemini"
    model: str = "gemini-3.5-flash"
    quality_mode: str = "balanced"
    glossary_text: str = ""
    prompt_version: str = "zh_vi_context_v4_gemini"
    batch_size: int = 50
    max_retries: int = 2
    api_key: str = ""


@dataclass(frozen=True)
class TranslationResult:
    """Kết quả dịch một lượt."""

    segments: list[SubtitleSegment]
    provider: str
    model: str
    cache_hits: int
    cache_misses: int
    elapsed_seconds: float


class TranslationProvider(Protocol):
    """Giao diện chung cho các backend dịch."""

    provider_name: str

    def translate_batch(
        self,
        segments: list[SubtitleSegment],
        config: TranslationConfig,
        glossary: dict[str, str],
    ) -> dict[int, str]:
        """Dịch một batch và trả về mapping index -> tiếng Việt."""
