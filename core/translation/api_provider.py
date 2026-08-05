"""Provider API chất lượng cao, dùng khóa từ môi trường hoặc .env."""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from core.models import SubtitleSegment
from core.translation.base import TranslationConfig
from core.translation.context_batcher import dinh_dang_batch_gui_model, phan_tich_ket_qua_model


class ApiProviderError(RuntimeError):
    """Lỗi khi gọi API dịch."""


class OpenAICompatibleProvider:
    """Provider API chat-completions tương thích OpenAI."""

    provider_name = "api"

    def translate_batch(
        self,
        segments: list[SubtitleSegment],
        config: TranslationConfig,
        glossary: dict[str, str],
    ) -> dict[int, str]:
        api_key = config.api_key.strip() or _doc_api_key("SRT_MAKER_API_KEY")
        if not api_key:
            raise ApiProviderError("Chưa có API key. Hãy nhập trong giao diện hoặc đặt SRT_MAKER_API_KEY/.env.")

        prompt = _tao_prompt(segments, glossary, config.quality_mode)
        payload = {
            "model": config.model,
            "messages": [
                {"role": "system", "content": _system_prompt()},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }
        endpoint = os.environ.get("SRT_MAKER_API_BASE", "https://api.openai.com/v1/chat/completions")
        noi_dung = self._goi_api(endpoint, api_key, payload, config.max_retries)
        return phan_tich_ket_qua_model(noi_dung)

    def _goi_api(self, endpoint: str, api_key: str, payload: dict, max_retries: int) -> str:
        loi_cuoi: Exception | None = None
        for lan_thu in range(max_retries + 1):
            try:
                request = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json",
                    },
                    method="POST",
                )
                with urllib.request.urlopen(request, timeout=90) as response:
                    du_lieu = json.loads(response.read().decode("utf-8"))
                return du_lieu["choices"][0]["message"]["content"]
            except (urllib.error.URLError, urllib.error.HTTPError, KeyError, IndexError, json.JSONDecodeError) as loi:
                loi_cuoi = loi
                if lan_thu >= max_retries:
                    break
                time.sleep(1.5 * (lan_thu + 1))

        raise ApiProviderError(f"Gọi API dịch thất bại sau {max_retries + 1} lần: {loi_cuoi}")


def _system_prompt() -> str:
    return (
        "Bạn là hệ thống dịch phụ đề từ tiếng Trung sang tiếng Việt. "
        "Dịch trực tiếp Trung-Việt, không qua tiếng Anh. "
        "Giữ nguyên ID segment, không gộp, không bỏ, không giải thích, không thêm nội dung ngoài bản gốc. "
        "Giữ nhất quán tên người, địa danh, sản phẩm, thuật ngữ và cách xưng hô."
    )


def _tao_prompt(segments: list[SubtitleSegment], glossary: dict[str, str], quality_mode: str) -> str:
    glossary_text = "\n".join(f"- {k} = {v}" for k, v in glossary.items()) or "- Không có"
    return (
        f"Chế độ dịch: {quality_mode}\n"
        f"Glossary toàn video:\n{glossary_text}\n\n"
        "Dịch các segment sau sang tiếng Việt theo đúng định dạng:\n"
        "[SEG_0001] bản dịch tiếng Việt\n\n"
        f"{dinh_dang_batch_gui_model(segments)}"
    )


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
