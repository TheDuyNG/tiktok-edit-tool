import importlib.util, os, subprocess, sys
base = r"C:\Users\DELL Vostro 15-3500\Documents\ai studio"
mod_path = os.path.join(base, "AUTOTTS", "TTS_v2_5_UI_Pro.py")
tmp_dir = os.path.join(base, "AUTOTTS", "_render_test")
os.makedirs(tmp_dir, exist_ok=True)
input_video = os.path.join(tmp_dir, "input.mp4")
output_video = os.path.join(tmp_dir, "effects_out.mp4")
if os.path.exists(output_video):
    os.remove(output_video)
cmd = [
    "ffmpeg", "-y",
    "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24:duration=1",
    "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
    "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-c:a", "aac", "-shortest", input_video,
]
subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
spec = importlib.util.spec_from_file_location("autotts_test_mod", mod_path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
logs = []
def log(msg):
    logs.append(str(msg))
    print(str(msg))

effects = {
    "flip_h": True,
    "flip_v": False,
    "line_mode": "Kẻ dọc",
    "line_strength": "Nhẹ",
    "blur_strength": 35,
    "export_ratio": "Bản Gốc",
    "output_quality": "4K / 2160p",
    "blur_regions": [(86, 52, 179, 106)],
    "logo_path": None,
    "logo_pos": None,
    "review_mode": False,
}
result = mod.render_video_effects_only(
    video_path=input_video,
    output_video_path=output_video,
    use_gpu=False,
    fast_render=True,
    video_speed=1.0,
    editor_effects=effects,
    progress_callback=lambda c,t,p: None,
    log_callback=log,
)
print("RESULT", result)
print("OUTPUT_EXISTS", os.path.exists(output_video), os.path.getsize(output_video) if os.path.exists(output_video) else 0)
