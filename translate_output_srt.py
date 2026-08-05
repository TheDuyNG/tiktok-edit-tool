from __future__ import annotations

import re
import json
from pathlib import Path

from core.models import SubtitleSegment
from core.srt_writer import ghi_srt
from core.translation.base import TranslationConfig
from core.translator import Translator


OUTPUT_DIR = Path(__file__).resolve().parent / "output"
TIME_RE = re.compile(
    r"(?P<start>\d{2}:\d{2}:\d{2},\d{3})\s+-->\s+(?P<end>\d{2}:\d{2}:\d{2},\d{3})"
)


def parse_time(value: str) -> float:
    hours, minutes, rest = value.split(":")
    seconds, millis = rest.split(",")
    return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(millis) / 1000


def parse_srt(path: Path) -> list[SubtitleSegment]:
    blocks = re.split(r"\r?\n\r?\n", path.read_text(encoding="utf-8").strip())
    segments: list[SubtitleSegment] = []
    for block in blocks:
        lines = block.splitlines()
        if len(lines) < 3:
            continue
        match = TIME_RE.search(lines[1])
        if not match:
            continue
        text = "\n".join(line.strip() for line in lines[2:] if line.strip())
        segments.append(
            SubtitleSegment(
                index=int(lines[0].strip()),
                start=parse_time(match.group("start")),
                end=parse_time(match.group("end")),
                original_zh=text,
            )
        )
    return segments


def write_srt_like_source(source: Path, translated: list[SubtitleSegment], destination: Path) -> None:
    source_blocks = re.split(r"\r?\n\r?\n", source.read_text(encoding="utf-8").strip())
    by_index = {segment.index: segment.translated_vi.strip() for segment in translated}
    output_blocks: list[str] = []
    for block in source_blocks:
        lines = block.splitlines()
        if len(lines) < 2:
            continue
        try:
            index = int(lines[0].strip())
        except ValueError:
            continue
        output_blocks.append("\n".join([lines[0], lines[1], by_index.get(index, "")]))
    destination.write_text("\n\n".join(output_blocks) + "\n", encoding="utf-8")


DESCRIPTIONS = {
    "kinhdi2": (
        "Một tin nhắn ẩn danh xuất hiện trong nhóm lớp: trước 23 giờ phải nằm lên giường ngủ, "
        "nếu không sẽ chết. Tưởng chỉ là trò đùa, nhưng khi đèn tắt, cả ký túc xá bắt đầu nghe thấy "
        "những tiếng kêu cứu lạnh sống lưng.\n\n"
        "#truyenma #kinhdi #reviewphim #phimkinhdi #chuyendem #kytucxa #luatlekinhdi #tamlinh #subtitleviet #tiktoktruyen"
    ),
    "kinhdi3": (
        "Chỉ hỏi một câu rất bình thường trong thang máy: “Anh lên tầng mấy?”, cô gái lại khiến mọi người "
        "hoảng loạn như vừa thấy thứ không nên thấy. Càng tìm câu trả lời, cô càng phát hiện tòa nhà này "
        "không còn thuộc về người sống.\n\n"
        "#truyenma #kinhdi #thangmay #amduong #reviewphim #phimngan #tamlinh #plotwist #subtitleviet #tiktoktruyen"
    ),
    "kinhdi4": (
        "Đêm mưa trong ký túc xá cũ, tiếng gõ cửa vang lên giữa lúc mất điện. Không ai dám mở, nhưng có thứ gì đó "
        "vẫn len vào qua khe cửa, bám lấy người yếu vía nhất phòng.\n\n"
        "#truyenma #kinhdi #kytucxa #demmua #goicua #tamlinh #reviewphim #phimkinhdi #subtitleviet #tiktoktruyen"
    ),
}


def make_description(stem: str, translated_preview: str) -> str:
    key = stem.replace("_zh", "")
    if key in DESCRIPTIONS:
        return DESCRIPTIONS[key]
    return (
        "Một câu chuyện kinh dị ngắn với những dấu hiệu bất thường càng xem càng lạnh gáy. "
        "Đằng sau sự im lặng là một bí mật không ai muốn nhắc lại.\n\n"
        "#truyenma #kinhdi #reviewphim #phimkinhdi #tamlinh #chuyendem #plotwist #subtitleviet #tiktoktruyen"
    )


def main() -> None:
    settings = json.loads((Path(__file__).resolve().parent / "settings.json").read_text(encoding="utf-8"))
    translator = Translator()
    api_keys = [key.strip() for key in settings.get("translation_api_key", "").split(",") if key.strip()]
    api_key = api_keys[2] if len(api_keys) > 2 else (api_keys[-1] if api_keys else "")
    config = TranslationConfig(
        provider=settings.get("translation_provider", "gemini"),
        model=settings.get("translation_model", "gemini-3.5-flash"),
        api_key=api_key,
        batch_size=12,
        max_retries=4,
        quality_mode=(
            "Dịch thủ công kiểu biên dịch phụ đề Trung-Việt: sát nghĩa, tự nhiên, "
            "giữ giọng kể chuyện kinh dị/rùng rợn, không thêm tình tiết, không lược ý, "
            "câu ngắn gọn để hợp phụ đề TikTok."
        ),
    )
    sources = sorted(OUTPUT_DIR.glob("*_zh.srt"), key=lambda path: path.stat().st_size)
    for source in sources:
        destination = source.with_name(source.name.replace("_zh.srt", "_vi.srt"))
        desc_path = source.with_name(source.name.replace("_zh.srt", "_tiktok.txt"))
        if destination.exists() and desc_path.exists():
            print(f"Skip {source.name}: da co file dich", flush=True)
            continue
        print(f"Start {source.name}", flush=True)
        segments = parse_srt(source)
        result = translator.translate(segments, config)
        write_srt_like_source(source, result.segments, destination)
        preview = " ".join(segment.translated_vi for segment in result.segments[:25])
        desc_path.write_text(make_description(source.stem, preview), encoding="utf-8")
        print(f"Done {source.name}: {len(result.segments)} segments -> {destination.name}", flush=True)


if __name__ == "__main__":
    main()
