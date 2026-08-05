import os
import sys
from pathlib import Path
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from app.main_window import MainWindow

from app.helper.helper import python_version_check, _them_cuda_site_neu_co


if __name__ == "__main__":
    """TikTok Edit Tool / SRT Maker."""
    python_version_check()

    #mp.freeze_support() # help bundle .exe (RuntimeError: freeze_support() missing)
    #mp.set_start_method('spawn', force=True)

    #Init instance
    app = QApplication(sys.argv)
    # app.setWindowIcon(QIcon("assets/keepers_owl.ico"))
    main_window =MainWindow()
    main_window.show()
    sys.exit(app.exec_())
