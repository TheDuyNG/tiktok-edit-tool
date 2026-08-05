from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from core.ffmpeg_service import lay_thoi_luong_video
from core.ocr_subtitle_transcriber import OcrSubtitleTranscriber
from core.srt_writer import ghi_srt_tieng_trung
from core.transcriber import TranscriberConfig


def _find_video() -> Path:
    video_dir = Path.home() / "Downloads" / "video"
    for path in video_dir.iterdir():
        if path.suffix.lower() == ".mp4" and "Robot Mary" in path.name:
            return path
    raise FileNotFoundError("Khong tim thay video Robot Mary trong Downloads/video")


def _analyze(segments, video_duration: float) -> dict[str, object]:
    ordered = sorted(segments, key=lambda item: (float(item.start), float(item.end)))
    overlaps = []
    gaps = []
    bad_timing = []
    for current in ordered:
        if float(current.end) <= float(current.start):
            bad_timing.append(current.index)
    for before, after in zip(ordered, ordered[1:]):
        if float(after.start) < float(before.end) - 0.001:
            overlaps.append((before.index, after.index, float(before.end) - float(after.start)))
        gap = float(after.start) - float(before.end)
        if gap > 2.0:
            gaps.append((before.index, after.index, gap))

    duplicate_adjacent = []
    for before, after in zip(ordered, ordered[1:]):
        a = re.sub(r"\s+", "", before.original_zh)
        b = re.sub(r"\s+", "", after.original_zh)
        if a and a == b:
            duplicate_adjacent.append((before.index, after.index, before.original_zh))

    last_end = max((float(item.end) for item in ordered), default=0.0)
    first_start = min((float(item.start) for item in ordered), default=0.0)
    return {
        "segments": len(ordered),
        "video_duration": round(video_duration, 3),
        "first_start": round(first_start, 3),
        "last_end": round(last_end, 3),
        "timeline_coverage": round(last_end / video_duration, 4) if video_duration else 0,
        "bad_timing": len(bad_timing),
        "overlaps": len(overlaps),
        "gaps_gt_2s": len(gaps),
        "max_gap": round(max((gap for *_pair, gap in gaps), default=0.0), 3),
        "duplicate_adjacent": len(duplicate_adjacent),
        "first_text": ordered[0].original_zh if ordered else "",
        "last_text": ordered[-1].original_zh if ordered else "",
        "largest_gaps": [
            {"before": before, "after": after, "gap": round(gap, 3)}
            for before, after, gap in sorted(gaps, key=lambda item: item[2], reverse=True)[:10]
        ],
    }


def main() -> None:
    video = _find_video()
    output = Path.cwd() / os.environ.get("OCR_VERIFY_OUTPUT", "ocr_run_verify_gpu")
    output.mkdir(exist_ok=True)

    logs: list[str] = []

    def log(message: str) -> None:
        logs.append(message)
        print(message, flush=True)

    config = TranscriberConfig(
        recognition_engine="ocr_subtitle",
        ocr_fps=1.0,
        ocr_crop_left=0.0,
        ocr_crop_top=0.72,
        ocr_crop_right=1.0,
        ocr_crop_bottom=1.0,
        ocr_use_gpu=True,
    )
    transcriber = OcrSubtitleTranscriber()
    result = transcriber.transcribe(video, output, config, log)
    duration = lay_thoi_luong_video(video)
    srt_path, clean_segments = ghi_srt_tieng_trung(result.segments, video, output, duration)
    stats = _analyze(clean_segments, duration)
    stats.update(
        {
            "video": str(video),
            "json": str(result.json_path),
            "srt": str(srt_path),
            "device": result.device_used,
            "compute": result.compute_type,
            "elapsed_seconds": round(result.elapsed_seconds, 3),
            "log_tail": logs[-12:],
        }
    )
    stats_path = output / "ocr_verify_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding="utf-8")
    print("VERIFY_STATS", stats_path, flush=True)
    print(json.dumps(stats, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
