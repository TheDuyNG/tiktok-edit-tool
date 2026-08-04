from pathlib import Path
from subprocess import CompletedProcess

from PIL import Image

from core.ocr_subtitle_transcriber import OcrSubtitleTranscriber
from core.transcriber import TranscriberConfig


def test_ocr_frame_extraction_uses_selected_region(tmp_path, monkeypatch):
    commands = []

    def fake_chay_lenh(command, timeout=60):
        commands.append(command)
        return CompletedProcess(command, 0, "", "")

    monkeypatch.setattr("core.ocr_subtitle_transcriber.tim_ffmpeg", lambda: "ffmpeg")
    monkeypatch.setattr("core.ocr_subtitle_transcriber.chay_lenh", fake_chay_lenh)

    transcriber = OcrSubtitleTranscriber()
    config = TranscriberConfig(
        recognition_engine="ocr_subtitle",
        ocr_fps=2.0,
        ocr_crop_left=0.25,
        ocr_crop_top=0.50,
        ocr_crop_right=0.75,
        ocr_crop_bottom=0.75,
    )

    transcriber._trich_frame(Path("video.mp4"), tmp_path, 2.0, config)

    assert commands
    command = commands[0]
    assert command[command.index("-vf") + 1] == "fps=2.0,crop=iw*0.5:ih*0.25:iw*0.25:ih*0.5"


def test_ocr_removes_repeated_trailing_watermark():
    transcriber = OcrSubtitleTranscriber()
    frames = [
        (0.0, "第一句台词 拾叁动漫"),
        (1.0, "第二句台词 拾叁动漫"),
        (2.0, "第三句台词 拾叁动漫"),
        (3.0, "第四句台词 拾叁动漫"),
        (4.0, "第五句台词 拾叁动漫"),
        (5.0, "第六句台词 拾叁动漫"),
        (6.0, "第七句台词 拾叁动漫"),
        (7.0, "第八句台词 洽叁动漫"),
    ]

    cleaned = transcriber._bo_cum_lap_cuoi_dong(frames)

    assert cleaned[0][1] == "第一句台词"
    assert cleaned[-1][1] == "第八句台词"
    assert all("动漫" not in text for _time, text in cleaned)


def test_smart_frame_reader_uses_image_cache(tmp_path, monkeypatch):
    transcriber = OcrSubtitleTranscriber()
    frame_a = tmp_path / "a.png"
    frame_b = tmp_path / "b.png"
    frame_c = tmp_path / "c.png"
    Image.new("RGB", (120, 40), "black").save(frame_a)
    Image.new("RGB", (120, 40), "black").save(frame_b)
    Image.new("RGB", (120, 40), "white").save(frame_c)

    calls = []

    def fake_doc_frame(_ocr, frame):
        calls.append(frame)
        return "字幕"

    monkeypatch.setattr(transcriber, "_doc_frame", fake_doc_frame)

    frames, stats = transcriber._doc_cac_frame_thong_minh(None, [frame_a, frame_b, frame_c], 1.0)

    assert len(frames) == 3
    assert len(calls) == 2
    assert stats["cache_hits"] == 1


def test_image_similarity_is_conservative():
    transcriber = OcrSubtitleTranscriber()

    assert transcriber._anh_gan_giong(bytes([10] * 20), bytes([10] * 20))
    assert not transcriber._anh_gan_giong(bytes([0] * 20), bytes([10] * 20))
