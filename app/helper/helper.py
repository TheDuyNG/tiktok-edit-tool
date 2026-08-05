import sys, os
from pathlib import Path

def python_version_check() -> None:
    """Check Python version, requires 3.12 or higher."""
    if sys.version_info.major != 3 or sys.version_info.minor < 12:
        print("Error: SRT Maker requires Python 3.12 or higher to run.")
        print(f"Current version: {sys.version.split()[0]}")
        print("Please create a virtual environment with Python 3.12.")
        sys.exit(1)


def _them_cuda_site_neu_co() -> None:
    #need remake this function to check if the user has installed PyTorch CUDA in LocalAppData and add it to sys.path if it exists.
    """Ưu tiên PyTorch CUDA riêng nếu đã cài vào LocalAppData."""
    if os.name != "nt":
        return

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return

    cuda_site = Path(local_app_data) / "SRT_MAKER" / "cuda_site"
    if cuda_site.exists():
        sys.path.insert(0, str(cuda_site))