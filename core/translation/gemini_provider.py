"""Provider Gemini để dịch trực tiếp Trung sang Việt."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from core.models import SubtitleSegment
from core.translation.base import TranslationConfig
from core.translation.context_batcher import dinh_dang_batch_gui_model, phan_tich_ket_qua_model


class GeminiProviderError(RuntimeError):
    """Lỗi khi gọi Gemini API."""


class GeminiProvider:
    """Dịch bằng Gemini API, giữ nguyên ID segment."""

    provider_name = "gemini"

    def translate_batch(
        self,
        segments: list[SubtitleSegment],
        config: TranslationConfig,
        glossary: dict[str, str],
    ) -> dict[int, str]:
        api_key = config.api_key.strip() or _doc_api_key("GEMINI_API_KEY") or _doc_api_key("SRT_MAKER_GEMINI_API_KEY")
        if not api_key:
            raise GeminiProviderError("Chưa có Gemini API key. Hãy nhập API key hoặc đặt GEMINI_API_KEY trong .env.")

        model = config.model.strip() or "gemini-3.5-flash"
        prompt = _tao_prompt(segments, glossary, config.quality_mode)
        text = self._goi_gemini(model, api_key, prompt, config.max_retries)
        return phan_tich_ket_qua_model(text)

    def _goi_gemini(self, model: str, api_key: str, prompt: str, max_retries: int) -> str:
        model_path = urllib.parse.quote(model, safe="")
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_path}:generateContent?key={api_key}"
        payload = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 8192},
        }

        loi_cuoi: Exception | None = None
        for lan_thu in range(max_retries + 1):
            try:
                request = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=120) as response:
                    data = json.loads(response.read().decode("utf-8"))
                return _lay_text_tu_gemini_response(data)
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError) as loi:
                loi_cuoi = loi
                if lan_thu >= max_retries:
                    break
                time.sleep(1.5 * (lan_thu + 1))

        raise GeminiProviderError(f"Gọi Gemini thất bại sau {max_retries + 1} lần: {loi_cuoi}")


def _tao_prompt(segments: list[SubtitleSegment], glossary: dict[str, str], quality_mode: str) -> str:
    glossary_text = "\n".join(f"- {k} = {v}" for k, v in glossary.items()) or "- Không có"
    return (
        "Bạn là hệ thống dịch phụ đề từ tiếng Trung sang tiếng Việt.\n"
        "Dịch trực tiếp Trung-Việt, tuyệt đối không dịch vòng qua tiếng Anh.\n"
        "Dịch theo ngữ cảnh nhiều segment, giữ xưng hô và tên riêng nhất quán.\n"
        "Không gộp segment, không bỏ segment, không thêm giải thích, không thêm nội dung ngoài bản gốc.\n"
        "Chỉ trả về đúng định dạng [SEG_0001] bản dịch tiếng Việt.\n\n"
        f"Chế độ: {quality_mode}\n"
        f"Glossary toàn video:\n{glossary_text}\n\n"
        f"{dinh_dang_batch_gui_model(segments)}"
    )


def _lay_text_tu_gemini_response(data: dict) -> str:
    parts = data["candidates"][0]["content"]["parts"]
    return "\n".join(part.get("text", "") for part in parts).strip()


def _doc_api_key(ten_bien: str) -> str:
    gia_tri = os.environ.get(ten_bien, "").strip()
    if gia_tri:
        return gia_tri

    env_path = Path(".env")
    if not env_path.exists():
        return ""

    for dong in env_path.read_text(encoding="utf-8").splitlines():
        if "=" not in dong or dong.strip().startswith("#"):
            continue
        khoa, gia_tri = dong.split("=", 1)
        if khoa.strip() == ten_bien:
            return gia_tri.strip().strip('"').strip("'")
    return ""
