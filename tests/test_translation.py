"""Kiểm tra module dịch Trung sang Việt theo ngữ cảnh."""

from __future__ import annotations

from pathlib import Path
from threading import Lock

from core.models import SubtitleSegment
from core.translation.base import TranslationConfig
from core.translation.cache import TranslationCache
from core.translation.context_batcher import dinh_dang_batch_gui_model, phan_tich_ket_qua_model
from core.translation.validator import kiem_tra_ket_qua_batch
from core.translator import Translator


class FakeLocalProvider:
    provider_name = "local"

    def translate_batch(self, segments, config, glossary):
        return {
            doan.index: f"Bản dịch tiếng Việt {doan.index} Chi Chi Bắc Kinh"
            for doan in segments
        }


class FakeGeminiProvider:
    provider_name = "gemini"

    def __init__(self) -> None:
        self.api_keys: list[str] = []
        self._lock = Lock()

    def translate_batch(self, segments, config, glossary):
        with self._lock:
            self.api_keys.append(config.api_key)
        return {doan.index: f"Bản dịch tiếng Việt {doan.index}" for doan in segments}


class FakeGeminiProviderGioiHan:
    provider_name = "gemini"

    def translate_batch(self, segments, config, glossary):
        if len(segments) > 2:
            raise RuntimeError("Dữ liệu gửi lên quá lớn")
        return {doan.index: f"Bản dịch tiếng Việt {doan.index}" for doan in segments}


def _segment(index: int, text: str) -> SubtitleSegment:
    return SubtitleSegment(index=index, start=float(index), end=float(index) + 0.8, original_zh=text)


def test_dinh_dang_gui_va_doc_model() -> None:
    cac_doan = [_segment(1, "哥哥,你去哪儿?"), _segment(2, "我去北京。")]
    noi_dung_gui = dinh_dang_batch_gui_model(cac_doan)
    assert "[SEG_0001] 哥哥,你去哪儿?" in noi_dung_gui

    ket_qua = phan_tich_ket_qua_model("[SEG_0001] Anh đi đâu?\n[SEG_0002] Tôi đi Bắc Kinh.")
    assert ket_qua == {1: "Anh đi đâu?", 2: "Tôi đi Bắc Kinh."}
    kiem_tra_ket_qua_batch(cac_doan, ket_qua)


def test_dich_local_du_cac_nhom_tinh_huong(tmp_path: Path) -> None:
    cac_doan = [
        _segment(1, "哥哥,你为什么不理我?"),
        _segment(2, "她说芝芝今天很开心。"),
        _segment(3, "墨云姐姐在北京等我们。"),
        _segment(4, "这件事真是一箭双雕。"),
        _segment(5, "产品重量是2公斤,续航8小时。"),
        _segment(6, "这款产品的屏幕很亮,但是电池一般。"),
        _segment(7, "这部纪录片讲述上海的发展。"),
        _segment(8, "如果明天你还..."),
    ]
    config = TranslationConfig(
        provider="local",
        model="offline-demo",
        glossary_text="芝芝 = Chi Chi\n墨云 = Mặc Vân\n北京 = Bắc Kinh\n上海 = Thượng Hải",
        batch_size=4,
    )

    cache = TranslationCache(tmp_path / "translation_cache.json")
    translator = Translator(cache=cache)
    translator.providers["local"] = FakeLocalProvider()
    ket_qua = translator.translate(cac_doan, config)

    assert len(ket_qua.segments) == len(cac_doan)
    assert [doan.index for doan in ket_qua.segments] == list(range(1, 9))
    assert all(doan.translated_vi.strip() for doan in ket_qua.segments)
    assert any("Chi Chi" in doan.translated_vi for doan in ket_qua.segments)
    assert any("Bắc Kinh" in doan.translated_vi for doan in ket_qua.segments)
    assert ket_qua.cache_misses == len(cac_doan)


def test_dich_gemini_chia_nhieu_api_key_va_giu_thu_tu(tmp_path: Path) -> None:
    cac_doan = [_segment(index, f"句子 {index}") for index in range(1, 7)]
    config = TranslationConfig(
        provider="gemini",
        model="gemini-3.5-flash",
        api_key="key_1, key_2, key_3",
        batch_size=2,
    )

    provider = FakeGeminiProvider()
    translator = Translator(cache=TranslationCache(tmp_path / "translation_cache.json"))
    translator.providers["gemini"] = provider
    ket_qua = translator.translate(cac_doan, config)

    assert [doan.index for doan in ket_qua.segments] == [1, 2, 3, 4, 5, 6]
    assert [doan.translated_vi for doan in ket_qua.segments] == [
        "Bản dịch tiếng Việt 1",
        "Bản dịch tiếng Việt 2",
        "Bản dịch tiếng Việt 3",
        "Bản dịch tiếng Việt 4",
        "Bản dịch tiếng Việt 5",
        "Bản dịch tiếng Việt 6",
    ]
    assert sorted(provider.api_keys) == ["key_1", "key_2", "key_3"]


def test_dich_gemini_tu_chia_nho_khi_batch_qua_lon(tmp_path: Path) -> None:
    cac_doan = [_segment(index, f"句子 {index}") for index in range(1, 7)]
    config = TranslationConfig(
        provider="gemini",
        model="gemini-3.5-flash",
        api_key="key_1",
        batch_size=6,
    )

    translator = Translator(cache=TranslationCache(tmp_path / "translation_cache.json"))
    translator.providers["gemini"] = FakeGeminiProviderGioiHan()
    ket_qua = translator.translate(cac_doan, config)

    assert [doan.index for doan in ket_qua.segments] == [1, 2, 3, 4, 5, 6]
    assert all(doan.translated_vi.startswith("Bản dịch tiếng Việt") for doan in ket_qua.segments)
