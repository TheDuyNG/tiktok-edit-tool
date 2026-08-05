"""SRT Maker tab for the PyQt5 application."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PyQt5.QtCore import Qt, QUrl, pyqtSignal
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from app.settings import AppSettings, luu_cau_hinh, tai_cau_hinh
from core.ffmpeg_service import lay_thoi_luong_video


class SrtWindow(QWidget):
    """One tab containing the complete SRT creation interface.

    Long-running work is intentionally not performed here. The tab emits
    signals with the selected videos and configuration so a controller can
    connect it to ``SrtMakerWorker`` without coupling worker code to widgets.
    """

    start_requested = pyqtSignal(dict, list)
    stop_requested = pyqtSignal()
    stop_after_current_requested = pyqtSignal()
    retry_failed_requested = pyqtSignal()
    ocr_preview_requested = pyqtSignal(str)
    ocr_region_requested = pyqtSignal(str)
    log_message = pyqtSignal(str)

    VIDEO_FILTER = "Video (*.mp4 *.mkv *.avi *.mov *.wmv);;Tất cả file (*.*)"
    TABLE_HEADERS = (
        "Tên video",
        "Thời lượng",
        "Model",
        "Trạng thái OCR",
        "Trạng thái",
        "Tiến trình",
        "Kết quả",
        "Lỗi",
    )

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.settings = tai_cau_hinh()
        self._running = False

        self._setup_ui()
        self._connect_signals()
        self._sync_recognition_mode()
        self._update_queue_summary()

    def _setup_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(16, 16, 16, 16)
        root_layout.setSpacing(10)

        title = QLabel("SRT Maker - tạo phụ đề tiếng Trung")
        title.setObjectName("srtTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 600;")
        root_layout.addWidget(title)

        root_layout.addWidget(self._create_action_bar())
        root_layout.addWidget(self._create_output_group())
        root_layout.addWidget(self._create_recognition_group())
        root_layout.addWidget(self._create_queue_group(), 1)
        root_layout.addWidget(self._create_progress_group())
        root_layout.addWidget(self._create_preview_group(), 1)

    def _create_action_bar(self) -> QGroupBox:
        group = QGroupBox("Chạy pipeline")
        layout = QGridLayout(group)

        self.start_button = QPushButton("Bắt đầu")
        self.start_button.setEnabled(False)
        self.stop_button = QPushButton("Dừng")
        self.stop_button.setToolTip("Dừng ngay tại điểm an toàn gần nhất")
        self.stop_button.setEnabled(False)
        self.keep_wav_checkbox = QCheckBox("Giữ WAV")
        self.keep_wav_checkbox.setChecked(self.settings.keep_wav)
        self.shutdown_checkbox = QCheckBox("Tắt máy khi xong")
        self.shutdown_checkbox.setToolTip("Tắt máy tính sau khi xử lý hết hàng đợi")
        self.shutdown_checkbox.setChecked(self.settings.shutdown_when_done)
        self.open_output_button = QPushButton("Mở thư mục")
        self.save_settings_button = QPushButton("Lưu cấu hình")

        layout.addWidget(self.start_button, 0, 0)
        layout.addWidget(self.stop_button, 0, 1)
        layout.addWidget(self.keep_wav_checkbox, 0, 2)
        layout.addWidget(self.shutdown_checkbox, 0, 3)
        layout.addWidget(self.open_output_button, 1, 2)
        layout.addWidget(self.save_settings_button, 1, 3)
        layout.setColumnStretch(4, 1)
        return group

    def _create_output_group(self) -> QGroupBox:
        group = QGroupBox("Nơi lưu SRT tiếng Trung")
        layout = QHBoxLayout(group)

        self.output_edit = QLineEdit(str(Path(self.settings.thu_muc_output).resolve()))
        self.output_browse_button = QPushButton("Chọn thư mục")

        layout.addWidget(self.output_edit, 1)
        layout.addWidget(self.output_browse_button)
        return group

    def _create_recognition_group(self) -> QGroupBox:
        group = QGroupBox("Cấu hình nhận dạng")
        layout = QVBoxLayout(group)

        mode_layout = QGridLayout()
        self.audio_mode_radio = QRadioButton("Âm thanh (Whisper / Hybrid)")
        self.ocr_mode_radio = QRadioButton("OCR phụ đề trên video")
        self.mode_status_label = QLabel()
        self.mode_status_label.setStyleSheet("font-weight: 600;")
        mode_layout.addWidget(self.mode_status_label, 0, 0, 1, 2)
        mode_layout.addWidget(self.audio_mode_radio, 1, 0)
        mode_layout.addWidget(self.ocr_mode_radio, 1, 1)
        mode_layout.setColumnStretch(2, 1)
        layout.addLayout(mode_layout)

        self.recognition_stack = QStackedWidget()
        self.recognition_stack.addWidget(self._create_audio_settings_page())
        self.recognition_stack.addWidget(self._create_ocr_settings_page())
        layout.addWidget(self.recognition_stack)

        if self.settings.recognition_engine == "ocr_subtitle":
            self.ocr_mode_radio.setChecked(True)
        else:
            self.audio_mode_radio.setChecked(True)
        return group

    def _create_audio_settings_page(self) -> QWidget:
        page = QFrame()
        layout = QGridLayout(page)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["whisper", "sensevoice", "hybrid"])
        engine = self.settings.recognition_engine
        self.engine_combo.setCurrentText(engine if engine in {"whisper", "sensevoice", "hybrid"} else "hybrid")

        self.model_combo = QComboBox()
        self.model_combo.addItems(["small", "medium", "large-v3", "sensevoice-small"])
        self.model_combo.setCurrentText(self.settings.model_size)

        self.device_combo = QComboBox()
        self.device_combo.addItems(["auto", "cuda", "cpu"])
        self.device_combo.setCurrentText(self.settings.device)

        self.language_combo = QComboBox()
        self.language_combo.addItems(["zh", "auto"])
        self.language_combo.setCurrentText(self.settings.language)

        self.vad_checkbox = QCheckBox("Bật VAD")
        self.vad_checkbox.setChecked(self.settings.vad_filter)
        self.difficult_audio_checkbox = QCheckBox("Âm thanh khó / nhiều nhiễu")
        self.difficult_audio_checkbox.setChecked(self.settings.difficult_audio_mode)
        self.full_dialogue_checkbox = QCheckBox("Nhận dạng toàn bộ hội thoại")
        self.full_dialogue_checkbox.setChecked(self.settings.full_dialogue_mode)
        self.gap_fill_checkbox = QCheckBox("Ghép khoảng trống tối đa")
        self.gap_fill_checkbox.setChecked(self.settings.aggressive_gap_fill)

        layout.addWidget(QLabel("Engine"), 0, 0)
        layout.addWidget(self.engine_combo, 0, 1)
        layout.addWidget(QLabel("Model"), 0, 2)
        layout.addWidget(self.model_combo, 0, 3)
        layout.addWidget(QLabel("Thiết bị"), 1, 0)
        layout.addWidget(self.device_combo, 1, 1)
        layout.addWidget(QLabel("Ngôn ngữ"), 1, 2)
        layout.addWidget(self.language_combo, 1, 3)
        layout.addWidget(self.vad_checkbox, 2, 0)
        layout.addWidget(self.difficult_audio_checkbox, 2, 1)
        layout.addWidget(self.full_dialogue_checkbox, 2, 2)
        layout.addWidget(self.gap_fill_checkbox, 2, 3)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        return page

    def _create_ocr_settings_page(self) -> QWidget:
        page = QFrame()
        layout = QGridLayout(page)

        self.ocr_fps_edit = QLineEdit(str(self.settings.ocr_fps))
        self.ocr_fps_edit.setMaximumWidth(100)
        self.ocr_gpu_checkbox = QCheckBox("Dùng GPU cho OCR")
        self.ocr_gpu_checkbox.setChecked(self.settings.ocr_use_gpu)
        self.crop_left_edit = QLineEdit(str(self.settings.ocr_crop_left))
        self.crop_top_edit = QLineEdit(str(self.settings.ocr_crop_top))
        self.crop_right_edit = QLineEdit(str(self.settings.ocr_crop_right))
        self.crop_bottom_edit = QLineEdit(str(self.settings.ocr_crop_bottom))
        for editor in (
            self.crop_left_edit,
            self.crop_top_edit,
            self.crop_right_edit,
            self.crop_bottom_edit,
        ):
            editor.setMaximumWidth(100)

        layout.addWidget(QLabel("OCR FPS"), 0, 0)
        layout.addWidget(self.ocr_fps_edit, 0, 1)
        layout.addWidget(self.ocr_gpu_checkbox, 0, 2, 1, 2)
        layout.addWidget(QLabel("Crop trái"), 1, 0)
        layout.addWidget(self.crop_left_edit, 1, 1)
        layout.addWidget(QLabel("Crop trên"), 1, 2)
        layout.addWidget(self.crop_top_edit, 1, 3)
        layout.addWidget(QLabel("Crop phải"), 2, 0)
        layout.addWidget(self.crop_right_edit, 2, 1)
        layout.addWidget(QLabel("Crop dưới"), 2, 2)
        layout.addWidget(self.crop_bottom_edit, 2, 3)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(3, 1)
        return page

    def _create_queue_group(self) -> QGroupBox:
        group = QGroupBox("Hàng đợi video")
        layout = QVBoxLayout(group)

        self.queue_table = QTableWidget(0, len(self.TABLE_HEADERS))
        self.queue_table.setHorizontalHeaderLabels(self.TABLE_HEADERS)
        self.queue_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.queue_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.queue_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.queue_table.setAlternatingRowColors(True)
        self.queue_table.verticalHeader().setVisible(False)
        header = self.queue_table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Stretch)
        header.setSectionResizeMode(7, QHeaderView.Stretch)
        layout.addWidget(self.queue_table, 1)

        controls = QGridLayout()
        self.queue_summary_label = QLabel()
        self.ocr_preview_button = QPushButton("Preview")
        self.ocr_region_button = QPushButton("Chọn vùng OCR")
        self.add_videos_button = QPushButton("Thêm video")
        self.remove_videos_button = QPushButton("Xóa đã chọn")
        self.retry_button = QPushButton("Thử lại lỗi")
        self.stop_after_button = QPushButton("Dừng sau file")

        self.ocr_preview_button.setEnabled(False)
        self.ocr_region_button.setEnabled(False)
        self.remove_videos_button.setEnabled(False)
        self.retry_button.setEnabled(False)
        self.stop_after_button.setEnabled(False)

        controls.addWidget(self.queue_summary_label, 0, 0, 2, 1)
        controls.setColumnStretch(1, 1)
        controls.addWidget(self.add_videos_button, 0, 2)
        controls.addWidget(self.remove_videos_button, 0, 3)
        controls.addWidget(self.retry_button, 0, 4)
        controls.addWidget(self.ocr_preview_button, 1, 2)
        controls.addWidget(self.ocr_region_button, 1, 3)
        controls.addWidget(self.stop_after_button, 1, 4)
        layout.addLayout(controls)
        return group

    def _create_progress_group(self) -> QWidget:
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        self.step_label = QLabel("Chưa chạy")
        self.step_label.setMinimumWidth(220)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        layout.addWidget(self.step_label)
        layout.addWidget(self.progress_bar, 1)
        return container

    def _create_preview_group(self) -> QGroupBox:
        group = QGroupBox("Kiểm tra mẫu phụ đề tiếng Trung")
        layout = QVBoxLayout(group)
        self.preview_edit = QPlainTextEdit()
        self.preview_edit.setReadOnly(True)
        self.preview_edit.setPlaceholderText("Kết quả xem trước sẽ xuất hiện tại đây.")
        layout.addWidget(self.preview_edit)
        return group

    def _connect_signals(self) -> None:
        self.audio_mode_radio.toggled.connect(self._sync_recognition_mode)
        self.ocr_mode_radio.toggled.connect(self._sync_recognition_mode)
        self.output_browse_button.clicked.connect(self._choose_output_directory)
        self.open_output_button.clicked.connect(self._open_output_directory)
        self.save_settings_button.clicked.connect(self.save_settings)
        self.add_videos_button.clicked.connect(self._choose_videos)
        self.remove_videos_button.clicked.connect(self.remove_selected_videos)
        self.retry_button.clicked.connect(self.retry_failed_videos)
        self.queue_table.itemSelectionChanged.connect(self._sync_queue_buttons)
        self.start_button.clicked.connect(self._emit_start_requested)
        self.stop_button.clicked.connect(self.stop_requested.emit)
        self.stop_after_button.clicked.connect(self.stop_after_current_requested.emit)
        self.ocr_preview_button.clicked.connect(self._emit_ocr_preview_requested)
        self.ocr_region_button.clicked.connect(self._emit_ocr_region_requested)

    def _sync_recognition_mode(self) -> None:
        is_ocr = self.ocr_mode_radio.isChecked()
        self.recognition_stack.setCurrentIndex(1 if is_ocr else 0)
        self.mode_status_label.setText(
            "Chế độ: OCR phụ đề" if is_ocr else "Chế độ: nhận dạng âm thanh"
        )
        self._sync_queue_buttons()

    def _choose_output_directory(self) -> None:
        current = Path(self.output_edit.text()).expanduser()
        selected = QFileDialog.getExistingDirectory(
            self,
            "Chọn nơi lưu SRT tiếng Trung",
            str(current if current.exists() else Path.cwd()),
        )
        if selected:
            self.output_edit.setText(selected)
            self.log_message.emit(f"Đã chọn nơi lưu SRT: {selected}")

    def _open_output_directory(self) -> None:
        output = Path(self.output_edit.text()).expanduser().resolve()
        try:
            output.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            QMessageBox.warning(self, "Không mở được thư mục", str(error))
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(output)))

    def _choose_videos(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Chọn video tiếng Trung",
            str(Path.cwd()),
            self.VIDEO_FILTER,
        )
        if paths:
            self.add_videos(paths)

    def add_videos(self, paths: list[str]) -> int:
        """Add unique video paths to the queue and return the number added."""

        existing = set(self.queued_video_paths())
        added = 0
        for raw_path in paths:
            video = Path(raw_path).expanduser().resolve()
            path_text = str(video)
            if path_text in existing:
                continue

            try:
                duration = f"{lay_thoi_luong_video(video):.2f}s"
            except Exception:
                duration = "Chưa rõ"

            row = self.queue_table.rowCount()
            self.queue_table.insertRow(row)
            values = (
                video.name,
                duration,
                "OCR" if self.ocr_mode_radio.isChecked() else self.model_combo.currentText(),
                "Chưa chọn OCR",
                "Chờ",
                "0%",
                "",
                "",
            )
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, path_text)
                    item.setToolTip(path_text)
                self.queue_table.setItem(row, column, item)

            existing.add(path_text)
            added += 1
            self.log_message.emit(f"Đã thêm vào hàng đợi: {video.name}")

        self._update_queue_summary()
        if added and self.queue_table.currentRow() < 0:
            self.queue_table.selectRow(0)
        return added

    def remove_selected_videos(self) -> None:
        rows = sorted({index.row() for index in self.queue_table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for row in rows:
            self.queue_table.removeRow(row)
        self.log_message.emit(f"Đã xóa {len(rows)} video khỏi hàng đợi.")
        self._update_queue_summary()

    def retry_failed_videos(self) -> None:
        retried = 0
        for row in range(self.queue_table.rowCount()):
            status_item = self.queue_table.item(row, 4)
            if status_item and status_item.text() in {"Lỗi", "Đã dừng"}:
                status_item.setText("Chờ")
                self.queue_table.item(row, 5).setText("0%")
                self.queue_table.item(row, 7).setText("")
                retried += 1
        if retried:
            self.retry_failed_requested.emit()
        self.log_message.emit(f"Đã đưa {retried} video lỗi/dừng về trạng thái chờ.")
        self._update_queue_summary()

    def queued_video_paths(self) -> list[str]:
        paths: list[str] = []
        for row in range(self.queue_table.rowCount()):
            item = self.queue_table.item(row, 0)
            if item:
                paths.append(str(item.data(Qt.UserRole)))
        return paths

    def selected_video_path(self) -> str | None:
        row = self.queue_table.currentRow()
        if row < 0:
            return None
        item = self.queue_table.item(row, 0)
        return str(item.data(Qt.UserRole)) if item else None

    def current_config(self) -> dict:
        """Return a UI-neutral configuration for the future pipeline controller."""

        is_ocr = self.ocr_mode_radio.isChecked()
        return {
            "output_directory": self.output_edit.text().strip(),
            "recognition_engine": "ocr_subtitle" if is_ocr else self.engine_combo.currentText(),
            "model_size": self.model_combo.currentText(),
            "device": self.device_combo.currentText(),
            "language": self.language_combo.currentText(),
            "vad_filter": self.vad_checkbox.isChecked(),
            "difficult_audio_mode": self.difficult_audio_checkbox.isChecked(),
            "full_dialogue_mode": self.full_dialogue_checkbox.isChecked(),
            "aggressive_gap_fill": self.gap_fill_checkbox.isChecked(),
            "ocr_fps": self._read_float(self.ocr_fps_edit.text(), 3.0),
            "ocr_crop_left": self._read_float(self.crop_left_edit.text(), 0.0),
            "ocr_crop_top": self._read_float(self.crop_top_edit.text(), 0.75),
            "ocr_crop_right": self._read_float(self.crop_right_edit.text(), 1.0),
            "ocr_crop_bottom": self._read_float(self.crop_bottom_edit.text(), 1.0),
            "ocr_use_gpu": self.ocr_gpu_checkbox.isChecked(),
            "keep_wav": self.keep_wav_checkbox.isChecked(),
            "shutdown_when_done": self.shutdown_checkbox.isChecked(),
        }

    def save_settings(self) -> None:
        config = self.current_config()
        updated: AppSettings = replace(
            self.settings,
            thu_muc_output=config["output_directory"],
            recognition_engine=config["recognition_engine"],
            model_size=config["model_size"],
            device=config["device"],
            language=config["language"],
            vad_filter=config["vad_filter"],
            difficult_audio_mode=config["difficult_audio_mode"],
            full_dialogue_mode=config["full_dialogue_mode"],
            aggressive_gap_fill=config["aggressive_gap_fill"],
            ocr_fps=config["ocr_fps"],
            ocr_crop_left=config["ocr_crop_left"],
            ocr_crop_top=config["ocr_crop_top"],
            ocr_crop_right=config["ocr_crop_right"],
            ocr_crop_bottom=config["ocr_crop_bottom"],
            ocr_use_gpu=config["ocr_use_gpu"],
            keep_wav=config["keep_wav"],
            shutdown_when_done=config["shutdown_when_done"],
        )
        try:
            luu_cau_hinh(updated)
        except OSError as error:
            QMessageBox.warning(self, "Không lưu được cấu hình", str(error))
            return
        self.settings = updated
        self.log_message.emit("Đã lưu cấu hình SRT.")

    def set_running(self, running: bool) -> None:
        """Switch the tab between editable and pipeline-running states."""

        self._running = running
        self.start_button.setEnabled(not running and self.queue_table.rowCount() > 0)
        self.stop_button.setEnabled(running)
        self.stop_after_button.setEnabled(running)
        self.add_videos_button.setEnabled(not running)
        self.save_settings_button.setEnabled(not running)
        self.output_browse_button.setEnabled(not running)
        self.audio_mode_radio.setEnabled(not running)
        self.ocr_mode_radio.setEnabled(not running)
        self.recognition_stack.setEnabled(not running)
        self._sync_queue_buttons()

    def set_progress(self, step: str, percent: int) -> None:
        self.step_label.setText(step)
        self.progress_bar.setValue(max(0, min(100, int(percent))))

    def set_preview(self, text: str) -> None:
        self.preview_edit.setPlainText(text)

    def update_video_status(
        self,
        video_path: str,
        *,
        status: str | None = None,
        progress: int | None = None,
        result: str | None = None,
        error: str | None = None,
        ocr_status: str | None = None,
    ) -> bool:
        """Update one queue row using its absolute video path."""

        target = str(Path(video_path).expanduser().resolve())
        for row in range(self.queue_table.rowCount()):
            name_item = self.queue_table.item(row, 0)
            if name_item and str(name_item.data(Qt.UserRole)) == target:
                if ocr_status is not None:
                    self.queue_table.item(row, 3).setText(ocr_status)
                if status is not None:
                    self.queue_table.item(row, 4).setText(status)
                if progress is not None:
                    self.queue_table.item(row, 5).setText(f"{max(0, min(100, int(progress)))}%")
                if result is not None:
                    self.queue_table.item(row, 6).setText(result)
                if error is not None:
                    self.queue_table.item(row, 7).setText(error)
                self._update_queue_summary()
                return True
        return False

    def _emit_start_requested(self) -> None:
        videos = self.queued_video_paths()
        if not videos:
            QMessageBox.information(self, "Hàng đợi", "Hãy thêm ít nhất một video trước khi bắt đầu.")
            return
        self.start_requested.emit(self.current_config(), videos)

    def _emit_ocr_preview_requested(self) -> None:
        path = self.selected_video_path()
        if path:
            self.ocr_preview_requested.emit(path)

    def _emit_ocr_region_requested(self) -> None:
        path = self.selected_video_path()
        if path:
            self.ocr_region_requested.emit(path)

    def _sync_queue_buttons(self) -> None:
        has_selection = self.queue_table.currentRow() >= 0
        is_ocr = self.ocr_mode_radio.isChecked()
        self.remove_videos_button.setEnabled(has_selection and not self._running)
        self.ocr_preview_button.setEnabled(has_selection and is_ocr and not self._running)
        self.ocr_region_button.setEnabled(has_selection and is_ocr and not self._running)

    def _update_queue_summary(self) -> None:
        total = self.queue_table.rowCount()
        waiting = 0
        failed = 0
        for row in range(total):
            status = self.queue_table.item(row, 4)
            if not status:
                continue
            if status.text() == "Chờ":
                waiting += 1
            elif status.text() in {"Lỗi", "Đã dừng"}:
                failed += 1
        self.queue_summary_label.setText(f"Tổng: {total} | Chờ: {waiting} | Lỗi/dừng: {failed}")
        self.start_button.setEnabled(total > 0 and not self._running)
        self.retry_button.setEnabled(failed > 0 and not self._running)
        self._sync_queue_buttons()

    @staticmethod
    def _read_float(value: str, default: float) -> float:
        try:
            return float(value.strip().replace(",", "."))
        except ValueError:
            return default
