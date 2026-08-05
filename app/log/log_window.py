from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPlainTextEdit
# from ui.widgets.log_display_widget import LogDisplayWidget

class LogWindow(QWidget):
    def __init__(self):
        super().__init__()
        self._setup_ui() #setup UI

        #receive log error + system log
        # log_bus.system_log.connect(self.log_display.log)
        # log_bus.error_log.connect(self.log_display.log)

    def _setup_ui(self):
        # --- Main layout ---
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)

        # --- Log display ---
        # self.log_display = LogDisplayWidget()
        self.main_layout.addWidget(QPlainTextEdit())

