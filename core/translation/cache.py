"""Cache bản dịch theo nội dung, provider, model, prompt và glossary."""

from __future__ import annotations

import hashlib
import json
import threading
from pathlib import Path


class TranslationCache:
    """Cache JSON đơn giản, chạy tốt trên Windows."""

    def __init__(self, cache_path: Path | None = None) -> None:
        self.cache_path = cache_path or Path("temp") / "translation_cache.json"
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self._du_lieu = self._doc_cache()
        self._lock = threading.Lock()

    def get(self, key: str) -> str | None:
        with self._lock:
            return self._du_lieu.get(key)

    def set(self, key: str, value: str) -> None:
        with self._lock:
            self._du_lieu[key] = value
            self.cache_path.write_text(json.dumps(self._du_lieu, ensure_ascii=False, indent=2), encoding="utf-8")

    def build_key(
        self,
        original_text: str,
        provider: str,
        model: str,
        prompt_version: str,
        glossary_version: str,
    ) -> str:
        noi_dung = "\n".join([original_text, provider, model, prompt_version, glossary_version])
        return hashlib.sha256(noi_dung.encode("utf-8")).hexdigest()

    def _doc_cache(self) -> dict[str, str]:
        if not self.cache_path.exists():
            return {}

        try:
            return json.loads(self.cache_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
