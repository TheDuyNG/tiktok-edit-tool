from pathlib import Path

from core.sensevoice_transcriber import SenseVoiceTranscriber
from core.transcriber import FasterWhisperTranscriber


def test_explicit_cuda_does_not_include_cpu_fallback() -> None:
    transcriber = FasterWhisperTranscriber()

    assert all(device == "cuda" for device, _compute_type in transcriber._chon_thiet_bi("cuda"))
    assert ("cpu", "int8") in transcriber._chon_thiet_bi("auto")


def test_sensevoice_finds_local_modelscope_snapshots(tmp_path: Path) -> None:
    model_snapshot = tmp_path / "models" / "iic--SenseVoiceSmall" / "snapshots" / "master"
    vad_snapshot = tmp_path / "models" / "iic--speech_fsmn_vad_zh-cn-16k-common-pytorch" / "snapshots" / "master"
    for snapshot in (model_snapshot, vad_snapshot):
        snapshot.mkdir(parents=True)
        (snapshot / "config.yaml").write_text("model: test", encoding="utf-8")
        (snapshot / "model.pt").write_bytes(b"test")

    transcriber = SenseVoiceTranscriber()

    assert transcriber._tim_snapshot_model_local("iic/SenseVoiceSmall", tmp_path) == model_snapshot
    assert transcriber._tim_snapshot_vad_local(tmp_path) == vad_snapshot
