import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from PyQt5.QtWidgets import QMainWindow, QTabWidget

from app.log.log_window import LogWindow
from app.srt.srt_window import SrtWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TIKTOK EDIT TOOL")
        self.resize(1180, 820)
        
        #create tab widget
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        #init pages
        # self.settings_page = SettingsPage(self.config)
        # self.help_page = HelpPage()
        self.srt_window = SrtWindow()
        self.log_window = LogWindow()
        # self.view_inference_page = ViewInferencePage(self.process_manager)

        #add tabs
        self.tabs.addTab(self.srt_window, "SRT Maker")
        self.tabs.addTab(self.log_window, "Logs")
        # self.tabs.addTab(self.help_page, "Help")

