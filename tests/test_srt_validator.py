from core.models import SubtitleSegment
from core.srt_validator import chuan_hoa_segments_cho_srt


def test_bo_segment_lap_lien_tiep_rat_sat_nhau():
    cac_doan = [
        SubtitleSegment(index=1, start=0.0, end=2.0, original_zh="你好", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=2, start=2.2, end=3.0, original_zh="你好", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=3, start=5.0, end=6.0, original_zh="你好", translated_vi="", cleaned_text="", status="", warning=""),
    ]

    ket_qua = chuan_hoa_segments_cho_srt(cac_doan, "original_zh")

    assert len(ket_qua) == 2
    assert [doan.index for doan in ket_qua] == [1, 2]
    assert ket_qua[0].start == 0.0
    assert ket_qua[1].start == 5.0


def test_giu_lai_cau_lap_khi_cach_xa_nhau():
    cac_doan = [
        SubtitleSegment(index=1, start=0.0, end=1.0, original_zh="谢谢", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=2, start=3.0, end=4.0, original_zh="谢谢", translated_vi="", cleaned_text="", status="", warning=""),
    ]

    ket_qua = chuan_hoa_segments_cho_srt(cac_doan, "original_zh")

    assert len(ket_qua) == 2


def test_bo_cau_lap_bat_thuong_trong_thoi_gian_ngan():
    cac_doan = [
        SubtitleSegment(index=1, start=0.0, end=1.0, original_zh="她的身体也很尊重塞拉", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=2, start=3.0, end=4.0, original_zh="中间有一句别的", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=3, start=8.0, end=9.0, original_zh="她的身体也很尊重塞拉", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=4, start=16.0, end=17.0, original_zh="她的身体也很尊重塞拉", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=5, start=24.0, end=25.0, original_zh="她的身体也很尊重塞拉", translated_vi="", cleaned_text="", status="", warning=""),
        SubtitleSegment(index=6, start=32.0, end=33.0, original_zh="她的身体也很尊重塞拉", translated_vi="", cleaned_text="", status="", warning=""),
    ]

    ket_qua = chuan_hoa_segments_cho_srt(cac_doan, "original_zh")

    assert [doan.original_zh for doan in ket_qua] == ["她的身体也很尊重塞拉", "中间有一句别的"]
