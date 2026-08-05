"""Small standalone CUDA diagnostic for the AUTOTTS Python 3.12 environment."""

from __future__ import annotations

import subprocess
import sys


probe = (
    "import torch; "
    "print('torch=' + torch.__version__, flush=True); "
    "print('cuda_build=' + str(torch.version.cuda), flush=True); "
    "print('available=' + str(torch.cuda.is_available()), flush=True); "
    "print('device=' + (torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'), flush=True); "
    "x=torch.randn((1024,1024), device='cuda'); "
    "y=x@x; torch.cuda.synchronize(); "
    "print('gpu_matmul_ok=' + str(float(y[0,0])), flush=True)"
)

result = subprocess.run(
    [sys.executable, "-X", "faulthandler", "-c", probe],
    text=True,
    capture_output=True,
)
print(result.stdout, end="")
print(result.stderr, end="", file=sys.stderr)
print(f"child_exit_code={result.returncode}")
raise SystemExit(0 if result.returncode == 0 else 1)
