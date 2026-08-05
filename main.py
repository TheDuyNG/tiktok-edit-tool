"""Điểm khởi chạy ứng dụng SRT Maker."""

import os
import sys
from pathlib import Path


def _kiem_tra_phien_ban_python() -> None:
    """Kiểm tra phiên bản Python, yêu cầu 3.12+."""
    if sys.version_info.major != 3 or sys.version_info.minor < 12:
        print("Lỗi: SRT Maker yêu cầu Python 3.12 trở lên để hoạt động.")
        print(f"Phiên bản của bạn là: {sys.version.split()[0]}")
        print("Vui lòng tạo một môi trường ảo (virtual environment) với Python 3.12.")
        sys.exit(1)


def _them_cuda_site_neu_co() -> None:
    """Uu tien PyTorch CUDA rieng neu da cai vao LocalAppData."""

    if os.name != "nt":
        return

    local_app_data = os.environ.get("LOCALAPPDATA")
    if not local_app_data:
        return

    cuda_site = Path(local_app_data) / "SRT_MAKER" / "cuda_site"
    if cuda_site.exists():
        sys.path.insert(0, str(cuda_site))


_them_cuda_site_neu_co()


from app.ui import chay_ung_dung


if __name__ == "__main__":
    _kiem_tra_phien_ban_python()
    chay_ung_dung()
