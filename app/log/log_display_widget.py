#widget display log
from PyQt5.QtWidgets import QTextEdit
from PyQt5.QtCore import QDateTime

class LogDisplayWidget(QTextEdit):
    """#widget display log"""
    
    def __init__(self):
        super().__init__()
        self.setReadOnly(True)
    
    def log(self, message: str):
        """Thêm log với timestamp"""
        timestamp = QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm:ss')
        self.append(f"[{timestamp}] {message}")