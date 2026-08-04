"""Provider dịch local/offline bằng model dịch Trung - Việt thật."""

from __future__ import annotations

from pathlib import Path

from core.models import SubtitleSegment
from core.translation.base import TranslationConfig
from core.translation.glossary import ap_dung_glossary_vao_ban_dich


class LocalProviderError(RuntimeError):
    """Lỗi cấu hình hoặc thiếu thư viện cho dịch local."""


class LocalFallbackProvider:
    """Dịch local bằng Transformers, không dùng bản mô phỏng."""

    provider_name = "local"
    default_model = "Helsinki-NLP/opus-mt-zh-vi"
    _loaded_model_name: str | None = None
    _tokenizer = None
    _model = None

    def translate_batch(
        self,
        segments: list[SubtitleSegment],
        config: TranslationConfig,
        glossary: dict[str, str],
    ) -> dict[int, str]:
        tokenizer, model = self._load_model(config.model)
        ket_qua: dict[int, str] = {}

        for doan in segments:
            van_ban_nguon = self._ap_dung_glossary_vao_nguon(doan.original_zh, glossary)
            ban_dich = self._translate_text(van_ban_nguon, tokenizer, model)
            ket_qua[doan.index] = ap_dung_glossary_vao_ban_dich(ban_dich, glossary)

        return ket_qua

    def _load_model(self, model_name: str):
        ten_model = model_name.strip()
        if not ten_model or ten_model == "offline-demo":
            ten_model = self.default_model

        if self._loaded_model_name == ten_model and self._tokenizer is not None and self._model is not None:
            return self._tokenizer, self._model

        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as loi:
            raise LocalProviderError(
                "Chưa có thư viện dịch local thật. Hãy cài: "
                "python -m pip install transformers sentencepiece torch"
            ) from loi

        try:
            cache_dir = Path("temp") / "huggingface"
            cache_dir.mkdir(parents=True, exist_ok=True)
            tokenizer = AutoTokenizer.from_pretrained(ten_model, cache_dir=str(cache_dir))
            model = AutoModelForSeq2SeqLM.from_pretrained(ten_model, cache_dir=str(cache_dir))
        except Exception as loi:
            raise LocalProviderError(
                f"Không tải được model dịch local '{ten_model}'. "
                "Hãy kiểm tra internet/cache model hoặc đổi sang provider api."
            ) from loi

        self.__class__._loaded_model_name = ten_model
        self.__class__._tokenizer = tokenizer
        self.__class__._model = model
        return tokenizer, model

    def _translate_text(self, text: str, tokenizer, model) -> str:
        inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
        outputs = model.generate(**inputs, max_new_tokens=256, num_beams=4)
        return tokenizer.decode(outputs[0], skip_special_tokens=True).strip()

    def _ap_dung_glossary_vao_nguon(self, text: str, glossary: dict[str, str]) -> str:
        ket_qua = text
        for tieng_trung, tieng_viet in glossary.items():
            ket_qua = ket_qua.replace(tieng_trung, tieng_viet)
        return ket_qua
