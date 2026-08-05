"""Dịch trực tiếp tiếng Trung sang tiếng Việt theo ngữ cảnh."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace

from core.models import SubtitleSegment
from core.translation.api_provider import OpenAICompatibleProvider
from core.translation.base import TranslationConfig, TranslationProvider, TranslationResult
from core.translation.cache import TranslationCache
from core.translation.context_batcher import tao_batch_theo_ngu_canh
from core.translation.gemini_provider import GeminiProvider
from core.translation.glossary import doc_glossary, glossary_version
from core.translation.local_provider import LocalFallbackProvider
from core.translation.validator import kiem_tra_ket_qua_batch


class Translator:
    """Bộ dịch Trung-Việt có ngữ cảnh, cache và validator."""

    def __init__(self, cache: TranslationCache | None = None) -> None:
        self.cache = cache or TranslationCache()
        self.providers: dict[str, TranslationProvider] = {
            "api": OpenAICompatibleProvider(),
            "gemini": GeminiProvider(),
            "local": LocalFallbackProvider(),
        }

    def translate(
        self,
        cac_doan: list[SubtitleSegment],
        config: TranslationConfig | None = None,
    ) -> TranslationResult:
        """Dịch danh sách segment, giữ nguyên ID và không gộp/bỏ segment."""

        config = config or TranslationConfig()
        provider = self._lay_provider(config.provider)
        glossary = doc_glossary(config.glossary_text)
        glossary_ver = glossary_version(config.glossary_text)
        cac_batch = list(tao_batch_theo_ngu_canh(cac_doan, config.batch_size))
        api_keys = self._tach_api_keys(config.api_key)
        bat_dau = time.perf_counter()

        if len(api_keys) > 1 and config.provider in {"gemini", "api"}:
            return self._translate_song_song(cac_batch, config, provider, glossary, glossary_ver, bat_dau, api_keys)

        ket_qua, cache_hits, cache_misses = self._translate_tuan_tu(
            cac_batch,
            config,
            provider,
            glossary,
            glossary_ver,
        )
        return TranslationResult(
            segments=ket_qua,
            provider=config.provider,
            model=config.model,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            elapsed_seconds=time.perf_counter() - bat_dau,
        )

    def _translate_tuan_tu(
        self,
        cac_batch: list[list[SubtitleSegment]],
        config: TranslationConfig,
        provider: TranslationProvider,
        glossary: dict[str, str],
        glossary_ver: str,
    ) -> tuple[list[SubtitleSegment], int, int]:
        ket_qua: list[SubtitleSegment] = []
        cache_hits = 0
        cache_misses = 0

        for batch in cac_batch:
            batch_da_dich, hits, misses = self._dich_mot_batch(batch, config, provider, glossary, glossary_ver)
            ket_qua.extend(batch_da_dich)
            cache_hits += hits
            cache_misses += misses

        return ket_qua, cache_hits, cache_misses

    def _translate_song_song(
        self,
        cac_batch: list[list[SubtitleSegment]],
        config: TranslationConfig,
        provider: TranslationProvider,
        glossary: dict[str, str],
        glossary_ver: str,
        bat_dau: float,
        api_keys: list[str],
    ) -> TranslationResult:
        ket_qua_theo_batch: list[list[SubtitleSegment] | None] = [None] * len(cac_batch)
        cache_hits = 0
        cache_misses = 0
        max_workers = min(len(api_keys), max(1, len(cac_batch)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for vi_tri, batch in enumerate(cac_batch):
                api_key = api_keys[vi_tri % len(api_keys)]
                config_batch = replace(config, api_key=api_key)
                future = executor.submit(self._dich_mot_batch, batch, config_batch, provider, glossary, glossary_ver)
                futures[future] = vi_tri

            for future in as_completed(futures):
                vi_tri = futures[future]
                batch_da_dich, hits, misses = future.result()
                ket_qua_theo_batch[vi_tri] = batch_da_dich
                cache_hits += hits
                cache_misses += misses

        ket_qua: list[SubtitleSegment] = []
        for batch_da_dich in ket_qua_theo_batch:
            if batch_da_dich:
                ket_qua.extend(batch_da_dich)

        return TranslationResult(
            segments=ket_qua,
            provider=config.provider,
            model=config.model,
            cache_hits=cache_hits,
            cache_misses=cache_misses,
            elapsed_seconds=time.perf_counter() - bat_dau,
        )

    def _dich_mot_batch(
        self,
        batch: list[SubtitleSegment],
        config: TranslationConfig,
        provider: TranslationProvider,
        glossary: dict[str, str],
        glossary_ver: str,
    ) -> tuple[list[SubtitleSegment], int, int]:
        ban_dich_batch: dict[int, str] = {}
        can_dich: list[SubtitleSegment] = []
        cache_hits = 0
        cache_misses = 0

        for doan in batch:
            key = self.cache.build_key(
                doan.original_zh,
                config.provider,
                config.model,
                config.prompt_version,
                glossary_ver,
            )
            cached = self.cache.get(key)
            if cached:
                cache_hits += 1
                ban_dich_batch[doan.index] = cached
            else:
                cache_misses += 1
                can_dich.append(doan)

        if can_dich:
            ban_dich_moi = self._goi_provider_co_chia_nho(can_dich, config, provider, glossary)
            kiem_tra_ket_qua_batch(can_dich, ban_dich_moi)
            ban_dich_batch.update(ban_dich_moi)

            for doan in can_dich:
                key = self.cache.build_key(
                    doan.original_zh,
                    config.provider,
                    config.model,
                    config.prompt_version,
                    glossary_ver,
                )
                self.cache.set(key, ban_dich_moi[doan.index])

        ban_dich_theo_thu_tu = {doan.index: ban_dich_batch[doan.index] for doan in batch}
        kiem_tra_ket_qua_batch(batch, ban_dich_theo_thu_tu)
        batch_da_dich = [replace(doan, translated_vi=ban_dich_batch[doan.index], status="translated") for doan in batch]
        return batch_da_dich, cache_hits, cache_misses

    def _goi_provider_co_chia_nho(
        self,
        segments: list[SubtitleSegment],
        config: TranslationConfig,
        provider: TranslationProvider,
        glossary: dict[str, str],
    ) -> dict[int, str]:
        try:
            return provider.translate_batch(segments, config, glossary)
        except Exception:
            if len(segments) <= 1:
                raise

            giua = len(segments) // 2
            nua_dau = self._goi_provider_co_chia_nho(segments[:giua], config, provider, glossary)
            nua_sau = self._goi_provider_co_chia_nho(segments[giua:], config, provider, glossary)
            return {**nua_dau, **nua_sau}

    def _lay_provider(self, provider_name: str) -> TranslationProvider:
        if provider_name not in self.providers:
            raise ValueError("Provider chỉ hỗ trợ api, gemini hoặc local.")
        return self.providers[provider_name]

    def _tach_api_keys(self, api_key_text: str) -> list[str]:
        return [key.strip() for key in api_key_text.split(",") if key.strip()]
