import os
import json
import time
import cv2
import numpy as np
import logging
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QFormLayout, QLineEdit, QSpinBox, QCheckBox, QSlider, 
    QGroupBox, QSplitter, QTextEdit, QComboBox, QMessageBox,
    QHeaderView, QFrame
)
from PyQt5.QtCore import Qt, QTimer, pyqtSlot
from PyQt5.QtGui import QImage, QPixmap, QFont, QColor, QIcon

from src.plc.modbus_client import ModbusPLCClient
from src.plc.plc_simulator import PLCSimulator
from src.vision.camera_thread import CameraProcessingThread

logger = logging.getLogger(__name__)

DARK_STYLESHEET = """
QMainWindow {
    background-color: #121214;
    color: #E0E0E0;
    font-family: 'Segoe UI', Arial, sans-serif;
}
QWidget {
    background-color: #121214;
    color: #E0E0E0;
}
QGroupBox {
    border: 1px solid #2D2D35;
    border-radius: 8px;
    margin-top: 12px;
    font-weight: bold;
    color: #00E5FF;
    padding-top: 15px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 8px;
    background-color: #121214;
}
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 8px 16px;
    font-weight: bold;
}
QPushButton:hover {
    background-color: #1976D2;
}
QPushButton:pressed {
    background-color: #0D47A1;
}
QPushButton:disabled {
    background-color: #424242;
    color: #888888;
}
QPushButton#btn_danger {
    background-color: #F44336;
}
QPushButton#btn_danger:hover {
    background-color: #D32F2F;
}
QPushButton#btn_success {
    background-color: #4CAF50;
}
QPushButton#btn_success:hover {
    background-color: #388E3C;
}
QTabWidget::pane {
    border: 1px solid #2D2D35;
    background: #1A1A1E;
    border-radius: 6px;
}
QTabBar::tab {
    background: #25252B;
    color: #AAAAAA;
    padding: 10px 18px;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    font-weight: bold;
}
QTabBar::tab:selected {
    background: #1A1A1E;
    color: #00E5FF;
    border-bottom: 2px solid #00E5FF;
}
QLineEdit, QSpinBox, QComboBox {
    background-color: #25252B;
    border: 1px solid #3D3D48;
    color: #FFFFFF;
    padding: 6px;
    border-radius: 4px;
}
QTableWidget {
    background-color: #1A1A1E;
    gridline-color: #2D2D35;
    border: 1px solid #2D2D35;
}
QHeaderView::section {
    background-color: #25252B;
    color: #00E5FF;
    padding: 6px;
    border: 1px solid #2D2D35;
    font-weight: bold;
}
QTextEdit {
    background-color: #0A0A0C;
    border: 1px solid #2D2D35;
    color: #00FF66;
    font-family: 'Consolas', 'Courier New', monospace;
}
"""

class MainWindow(QMainWindow):
    def __init__(self, config_path="config.json"):
        super().__init__()
        self.config_path = config_path
        self.config = self._load_config()

        self.setWindowTitle("HỆ THỐNG PHÂN LOẠI SẢN PHẨM QR & MÀU SẮC - GIAO TIẾP PLC")
        self.resize(1400, 850)
        self.setStyleSheet(DARK_STYLESHEET)

        # Thống kê sản phẩm 5 Quận Đà Nẵng
        self.counters = {"TOTAL": 0, "GATE_1": 0, "GATE_2": 0, "GATE_3": 0, "GATE_4": 0, "GATE_5": 0, "REJECT": 0}

        # Khởi tạo PLC Simulator & Client
        plc_cfg = self.config.get("plc", {})
        self.plc_simulator = PLCSimulator(host=plc_cfg.get("ip", "127.0.0.1"), port=plc_cfg.get("port", 502))
        self.plc_client = ModbusPLCClient(
            host=plc_cfg.get("ip", "127.0.0.1"),
            port=plc_cfg.get("port", 502),
            slave_id=plc_cfg.get("slave_id", 1)
        )

        # Nếu bật chế độ Giả lập PLC
        if plc_cfg.get("simulation_mode", True):
            self.plc_simulator.start()
            self.plc_simulator.on_register_change = self._on_sim_register_changed

        # Khởi tạo Luồng Camera
        self.camera_thread = CameraProcessingThread(self.config, self.plc_client)
        self.camera_thread.frame_processed.connect(self.update_video_frame)
        self.camera_thread.detection_updated.connect(self.update_detection_info)
        self.camera_thread.product_scanned.connect(self.record_classification_history)
        self.camera_thread.log_message.connect(self.add_log)

        # Tạo Giao diện
        self._init_ui()

        # Tự động kết nối PLC & Bật Camera khi mở phần mềm
        QTimer.singleShot(500, self.start_system)

    def _load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
        return {}

    def _save_config(self):
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            self.add_log("Đã lưu cấu hình vào file config.json", "INFO")
        except Exception as e:
            self.add_log(f"Lỗi lưu cấu hình: {e}", "ERROR")

    def _init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 1. Header Bar
        header = self._create_header()
        main_layout.addWidget(header)

        # 2. Main Splitter (Left: Video & Status | Right: Control Tabs)
        splitter = QSplitter(Qt.Horizontal)
        
        left_widget = self._create_left_panel()
        right_widget = self._create_right_panel()

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([850, 550])

        main_layout.addWidget(splitter, 1)

        # 3. Bottom Console Log
        console_group = QGroupBox("Nhật ký Hệ thống (System Console Log)")
        console_layout = QVBoxLayout(console_group)
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(130)
        console_layout.addWidget(self.log_text)

        main_layout.addWidget(console_group)

    def _create_header(self):
        frame = QFrame()
        frame.setStyleSheet("background-color: #1A1A1E; border-radius: 8px; border: 1px solid #2D2D35;")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 10, 15, 10)

        title = QLabel("HỆ THỐNG PHÂN LOẠI SẢN PHẨM QR & MÀU SẮC")
        title.setFont(QFont("Segoe UI", 14, QFont.Bold))
        title.setStyleSheet("color: #00E5FF;")

        # Status Indicators
        self.lbl_cam_status = QLabel("● Camera: OFF")
        self.lbl_cam_status.setStyleSheet("color: #FF5252; font-weight: bold;")
        
        self.lbl_plc_status = QLabel("● PLC: Offline")
        self.lbl_plc_status.setStyleSheet("color: #FF5252; font-weight: bold;")

        # Action Buttons
        self.btn_toggle_cam = QPushButton("Bật Camera")
        self.btn_toggle_cam.setObjectName("btn_success")
        self.btn_toggle_cam.clicked.connect(self.toggle_camera)

        self.btn_connect_plc = QPushButton("Kết nối PLC")
        self.btn_connect_plc.clicked.connect(self.toggle_plc_connection)

        self.chk_sim_mode = QCheckBox("PLC Simulator Mode")
        self.chk_sim_mode.setChecked(self.config.get("plc", {}).get("simulation_mode", True))
        self.chk_sim_mode.stateChanged.connect(self.toggle_sim_mode)

        self.chk_fast_mode = QCheckBox("Băng Chuyền Siêu Tốc (1-Frame)")
        self.chk_fast_mode.setStyleSheet("color: #FFCC00; font-weight: bold;")
        self.chk_fast_mode.setChecked(self.config.get("system", {}).get("high_speed_conveyor_mode", True))
        self.chk_fast_mode.stateChanged.connect(self.toggle_fast_mode)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.lbl_cam_status)
        layout.addWidget(self.lbl_plc_status)
        layout.addWidget(self.chk_fast_mode)
        layout.addWidget(self.chk_sim_mode)
        layout.addWidget(self.btn_toggle_cam)
        layout.addWidget(self.btn_connect_plc)

        return frame

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)

        # Video Frame Container
        video_box = QGroupBox("Luồng Camera Webcam Thực tế (Live View)")
        v_layout = QVBoxLayout(video_box)
        
        self.lbl_video = QLabel()
        self.lbl_video.setAlignment(Qt.AlignCenter)
        self.lbl_video.setStyleSheet("background-color: #050507; border-radius: 6px;")
        self.lbl_video.setMinimumSize(640, 480)
        v_layout.addWidget(self.lbl_video, 1)

        # Live Detection Cards
        cards_layout = QHBoxLayout()
        
        self.card_qr = self._create_info_card("MÃ QR PHÁT HIỆN", "N/A", "#00E5FF")
        self.card_color = self._create_info_card("MÀU SẮC", "UNKNOWN", "#FFCC00")
        self.card_gate = self._create_info_card("CỬA PHÂN LOẠI", "CỬA 0", "#34C759")

        cards_layout.addWidget(self.card_qr["widget"])
        cards_layout.addWidget(self.card_color["widget"])
        cards_layout.addWidget(self.card_gate["widget"])

        layout.addWidget(video_box, 1)
        layout.addLayout(cards_layout)

        return panel

    def _create_info_card(self, title, default_val, color_hex):
        card = QWidget()
        card.setStyleSheet(f"background-color: #1A1A1E; border: 1px solid #2D2D35; border-radius: 8px;")
        c_layout = QVBoxLayout(card)
        c_layout.setContentsMargins(10, 8, 10, 8)
        
        t_lbl = QLabel(title)
        t_lbl.setStyleSheet("color: #AAAAAA; font-size: 11px; font-weight: bold;")
        
        v_lbl = QLabel(default_val)
        v_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        v_lbl.setStyleSheet(f"color: {color_hex};")
        v_lbl.setWordWrap(True)

        c_layout.addWidget(t_lbl)
        c_layout.addWidget(v_lbl)

        return {"widget": card, "value_label": v_lbl}

    def _create_right_panel(self):
        self.tabs = QTabWidget()

        # Tab 1: Counter & History
        tab_counter = self._create_tab_counter()
        
        # Tab 2: Color Calibration (HSV Tuning)
        tab_color = self._create_tab_color_calibration()

        # Tab 3: PLC Connection Settings & Manual Test
        tab_plc = self._create_tab_plc_settings()

        # Tab 4: Rules Config
        tab_rules = self._create_tab_rules()

        self.tabs.addTab(tab_counter, "Thống kê & Lịch sử")
        self.tabs.addTab(tab_color, "Tinh chỉnh Màu HSV")
        self.tabs.addTab(tab_plc, "Cấu hình PLC")
        self.tabs.addTab(tab_rules, "Quy tắc Phân loại")

        return self.tabs

    def _create_tab_counter(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Counter Cards Grid
        grid_group = QGroupBox("Bộ Đếm Sản Phẩm (Counters)")
        grid_layout = QFormLayout(grid_group)

        self.lbl_cnt_total = QLabel("0")
        self.lbl_cnt_total.setFont(QFont("Segoe UI", 16, QFont.Bold))
        self.lbl_cnt_total.setStyleSheet("color: #00E5FF;")

        self.lbl_cnt_g1 = QLabel("0")
        self.lbl_cnt_g1.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cnt_g1.setStyleSheet("color: #FF3B30;")

        self.lbl_cnt_g2 = QLabel("0")
        self.lbl_cnt_g2.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cnt_g2.setStyleSheet("color: #34C759;")

        self.lbl_cnt_g3 = QLabel("0")
        self.lbl_cnt_g3.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cnt_g4 = QLabel("0")
        self.lbl_cnt_g4.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cnt_g4.setStyleSheet("color: #FF9500;")

        self.lbl_cnt_g5 = QLabel("0")
        self.lbl_cnt_g5.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cnt_g5.setStyleSheet("color: #AF52DE;")

        self.lbl_cnt_reject = QLabel("0")
        self.lbl_cnt_reject.setFont(QFont("Segoe UI", 14, QFont.Bold))
        self.lbl_cnt_reject.setStyleSheet("color: #8E8E93;")

        grid_layout.addRow("TỔNG SẢN PHẨM:", self.lbl_cnt_total)
        grid_layout.addRow("Cửa 1 (Q. Hải Châu - Đỏ):", self.lbl_cnt_g1)
        grid_layout.addRow("Cửa 2 (Q. Thanh Khê - Xanh lá):", self.lbl_cnt_g2)
        grid_layout.addRow("Cửa 3 (Q. Liên Chiểu - Xanh dương):", self.lbl_cnt_g3)
        grid_layout.addRow("Cửa 4 (Q. Ngũ Hành Sơn):", self.lbl_cnt_g4)
        grid_layout.addRow("Cửa 5 (Q. Cẩm Lệ):", self.lbl_cnt_g5)
        grid_layout.addRow("Cửa Loại (Reject/Lỗi):", self.lbl_cnt_reject)

        btn_box = QHBoxLayout()
        btn_reset_cnt = QPushButton("Reset Bộ Đếm")
        btn_reset_cnt.clicked.connect(self.reset_counters)

        btn_gen_qr = QPushButton("Tạo & Mở Thư Mục Tem QR (5 Quận)")
        btn_gen_qr.setStyleSheet("background-color: #9C27B0; font-weight: bold;")
        btn_gen_qr.clicked.connect(self.generate_and_open_qr_folder)

        btn_box.addWidget(btn_reset_cnt)
        btn_box.addWidget(btn_gen_qr)
        grid_layout.addRow("", btn_box)

        # Log Table History
        history_group = QGroupBox("Lịch sử Phân loại Gần đây")
        h_layout = QVBoxLayout(history_group)

        self.tbl_history = QTableWidget(0, 4)
        self.tbl_history.setHorizontalHeaderLabels(["Thời gian", "Mã QR", "Màu sắc", "Cửa PLC"])
        self.tbl_history.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        h_layout.addWidget(self.tbl_history)

        layout.addWidget(grid_group)
        layout.addWidget(history_group, 1)

        return widget

    def _create_tab_color_calibration(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # Selector Color Name
        select_layout = QHBoxLayout()
        select_layout.addWidget(QLabel("Chọn màu tinh chỉnh:"))
        self.cmb_colors = QComboBox()
        self.cmb_colors.addItems(["RED", "GREEN", "BLUE"])
        self.cmb_colors.currentTextChanged.connect(self.on_color_selected)
        select_layout.addWidget(self.cmb_colors, 1)

        layout.addLayout(select_layout)

        # HSV Sliders Group
        hsv_group = QGroupBox("Ngưỡng HSV (Hue, Saturation, Value)")
        hsv_layout = QFormLayout(hsv_group)

        self.sld_h_min = self._create_slider(0, 180, 0, hsv_layout, "Hue Min:")
        self.sld_h_max = self._create_slider(0, 180, 180, hsv_layout, "Hue Max:")
        self.sld_s_min = self._create_slider(0, 255, 100, hsv_layout, "Sat Min:")
        self.sld_s_max = self._create_slider(0, 255, 255, hsv_layout, "Sat Max:")
        self.sld_v_min = self._create_slider(0, 255, 70, hsv_layout, "Val Min:")
        self.sld_v_max = self._create_slider(0, 255, 255, hsv_layout, "Val Max:")

        btn_save_hsv = QPushButton("Lưu Ngưỡng HSV Này")
        btn_save_hsv.setObjectName("btn_success")
        btn_save_hsv.clicked.connect(self.save_hsv_tuning)
        hsv_layout.addRow("", btn_save_hsv)

        layout.addWidget(hsv_group)
        layout.addStretch()

        # Update initial slider positions
        self.on_color_selected("RED")

        return widget

    def _create_slider(self, min_v, max_v, default_v, form_layout, label_text):
        layout = QHBoxLayout()
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_v, max_v)
        slider.setValue(default_v)
        
        lbl_val = QLabel(str(default_v))
        lbl_val.setFixedWidth(35)
        slider.valueChanged.connect(lambda v: lbl_val.setText(str(v)))
        slider.valueChanged.connect(self.on_slider_changed)

        layout.addWidget(slider)
        layout.addWidget(lbl_val)

        form_layout.addRow(label_text, layout)
        return slider

    def _create_tab_plc_settings(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        form_group = QGroupBox("Cấu hình Kết nối PLC Modbus TCP")
        form = QFormLayout(form_group)

        plc_cfg = self.config.get("plc", {})

        self.txt_plc_ip = QLineEdit(plc_cfg.get("ip", "127.0.0.1"))
        self.spin_plc_port = QSpinBox()
        self.spin_plc_port.setRange(1, 65535)
        self.spin_plc_port.setValue(plc_cfg.get("port", 502))

        self.spin_slave_id = QSpinBox()
        self.spin_slave_id.setRange(1, 247)
        self.spin_slave_id.setValue(plc_cfg.get("slave_id", 1))

        self.spin_reg_addr = QSpinBox()
        self.spin_reg_addr.setRange(0, 9999)
        self.spin_reg_addr.setValue(plc_cfg.get("register_address", 0))

        form.addRow("Địa chỉ IP PLC:", self.txt_plc_ip)
        form.addRow("Cổng (Port):", self.spin_plc_port)
        form.addRow("Modbus Slave ID:", self.spin_slave_id)
        form.addRow("Holding Register Address:", self.spin_reg_addr)

        btn_save_plc = QPushButton("Lưu Cấu hình PLC")
        btn_save_plc.clicked.connect(self.save_plc_config)
        form.addRow("", btn_save_plc)

        layout.addWidget(form_group)

        # Manual Trigger Group
        test_group = QGroupBox("Kiểm thử Tín hiệu Thủ công (Manual Test to PLC)")
        test_layout = QHBoxLayout(test_group)

        btn_t1 = QPushButton("Gửi Cửa 1 (Val: 1)")
        btn_t1.clicked.connect(lambda: self.send_manual_plc_signal(1))

        btn_t2 = QPushButton("Gửi Cửa 2 (Val: 2)")
        btn_t2.clicked.connect(lambda: self.send_manual_plc_signal(2))

        btn_t3 = QPushButton("Gửi Cửa 3 (Val: 3)")
        btn_t3.clicked.connect(lambda: self.send_manual_plc_signal(3))

        btn_treject = QPushButton("Gửi Cửa Loại (Val: 99)")
        btn_treject.setObjectName("btn_danger")
        btn_treject.clicked.connect(lambda: self.send_manual_plc_signal(99))

        test_layout.addWidget(btn_t1)
        test_layout.addWidget(btn_t2)
        test_layout.addWidget(btn_t3)
        test_layout.addWidget(btn_treject)

        layout.addWidget(test_group)
        layout.addStretch()

        return widget

    def _create_tab_rules(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)

        layout.addWidget(QLabel("Bảng Quy tắc Phân loại (Mapping Rules):"))

        self.tbl_rules = QTableWidget(0, 5)
        self.tbl_rules.setHorizontalHeaderLabels([
            "Tên Quy tắc", "Từ khóa QR", "Màu sắc", "Mã Cửa", "Giá trị Tín hiệu PLC"
        ])
        self.tbl_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.tbl_rules)

        self.load_rules_to_table()

        btn_save_rules = QPushButton("Lưu Quy Tắc Phân Loại")
        btn_save_rules.setObjectName("btn_success")
        btn_save_rules.clicked.connect(self.save_rules_from_table)
        layout.addWidget(btn_save_rules)

        return widget

    # ------------------- Logic Slots & Handlers -------------------

    def start_system(self):
        """Khởi động camera và kết nối PLC khi mở ứng dụng"""
        self.connect_plc()
        self.start_camera()

    def toggle_camera(self):
        if self.camera_thread.running:
            self.stop_camera()
        else:
            self.start_camera()

    def start_camera(self):
        if not self.camera_thread.running:
            self.camera_thread.start()
            self.lbl_cam_status.setText("● Camera: ON")
            self.lbl_cam_status.setStyleSheet("color: #34C759; font-weight: bold;")
            self.btn_toggle_cam.setText("Dừng Camera")
            self.btn_toggle_cam.setObjectName("btn_danger")
            self.btn_toggle_cam.setStyle(self.btn_toggle_cam.style())

    def stop_camera(self):
        if self.camera_thread.running:
            self.camera_thread.stop()
            self.lbl_cam_status.setText("● Camera: OFF")
            self.lbl_cam_status.setStyleSheet("color: #FF5252; font-weight: bold;")
            self.btn_toggle_cam.setText("Bật Camera")
            self.btn_toggle_cam.setObjectName("btn_success")
            self.btn_toggle_cam.setStyle(self.btn_toggle_cam.style())

    def toggle_plc_connection(self):
        if self.plc_client.connected:
            self.plc_client.disconnect()
            self.lbl_plc_status.setText("● PLC: Offline")
            self.lbl_plc_status.setStyleSheet("color: #FF5252; font-weight: bold;")
            self.btn_connect_plc.setText("Kết nối PLC")
        else:
            self.connect_plc()

    def connect_plc(self):
        self.add_log(f"Đang kết nối tới PLC tại {self.plc_client.host}:{self.plc_client.port}...", "INFO")
        success = self.plc_client.connect()
        if success:
            sim_str = " (SIMULATOR)" if self.chk_sim_mode.isChecked() else ""
            self.lbl_plc_status.setText(f"● PLC: Online{sim_str}")
            self.lbl_plc_status.setStyleSheet("color: #34C759; font-weight: bold;")
            self.btn_connect_plc.setText("Ngắt kết nối PLC")
            self.add_log(f"Kết nối PLC thành công!{sim_str}", "INFO")
        else:
            self.lbl_plc_status.setText("● PLC: Error")
            self.lbl_plc_status.setStyleSheet("color: #FF5252; font-weight: bold;")
            self.add_log(f"Không thể kết nối PLC: {self.plc_client.last_error}", "WARN")

    def toggle_sim_mode(self, state):
        sim_enabled = (state == Qt.Checked)
        self.config["plc"]["simulation_mode"] = sim_enabled
        self._save_config()

        if sim_enabled:
            self.plc_simulator.start()
            self.plc_simulator.on_register_change = self._on_sim_register_changed
            self.add_log("Đã BẬT trình Giả lập PLC (PLC Simulator).", "INFO")
        else:
            self.plc_simulator.stop()
            self.add_log("Đã TẮT trình Giả lập PLC.", "INFO")

        # Thử tái kết nối
        self.plc_client.disconnect()
        self.connect_plc()

    def toggle_fast_mode(self, state):
        fast_enabled = (state == Qt.Checked)
        if "system" not in self.config:
            self.config["system"] = {}
        self.config["system"]["high_speed_conveyor_mode"] = fast_enabled
        self.config["system"]["detection_confidence_frames"] = 1 if fast_enabled else 3
        self._save_config()

        if fast_enabled:
            self.add_log("Đã BẬT Chế độ Băng Chuyền Siêu Tốc (Bắt tín hiệu tức thì 1-Frame, Cooldown 0.5s).", "INFO")
        else:
            self.add_log("Đã BẬT Chế độ Lọc Nhiễu (Yêu cầu 3-Frame ổn định).", "INFO")

    @pyqtSlot(np.ndarray)
    def update_video_frame(self, frame):
        """Hiển thị hình ảnh từ OpenCV lên QLabel"""
        h, w, ch = frame.shape
        bytes_per_line = ch * w
        converted_format = QImage.Format_RGB888
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, converted_format)
        pixmap = QPixmap.fromImage(q_img)
        
        # Scale vừa vặn QLabel mà vẫn giữ tỷ lệ
        scaled_pixmap = pixmap.scaled(
            self.lbl_video.width(), self.lbl_video.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        )
        self.lbl_video.setPixmap(scaled_pixmap)

    @pyqtSlot(dict)
    def update_detection_info(self, info):
        """Cập nhật các thẻ thông tin sản phẩm trên UI"""
        qr_data = info.get("qr_data", "N/A")
        color = info.get("color", "UNKNOWN")
        cls = info.get("classification", {})
        
        gate_id = cls.get("gate_id", 0)
        plc_sig = cls.get("plc_signal_value", 0)

        self.card_qr["value_label"].setText(qr_data if qr_data != "NONE" else "Không có QR")
        self.card_color["value_label"].setText(f"{color} ({info.get('color_confidence', 0)}%)")
        
        if gate_id > 0:
            g_str = f"CỬA {gate_id} (Sig: {plc_sig})"
            self.card_gate["value_label"].setText(g_str)

    @pyqtSlot(dict)
    def record_classification_history(self, info):
        """Kích hoạt nhảy bộ đếm sản phẩm & thêm lịch sử quét"""
        cls = info.get("classification", {})
        gate_id = cls.get("gate_id", 1)
        curr_time = time.time()

        # Cooldown 0.5 giây để khớp với tốc độ băng chuyền nhanh
        if hasattr(self, "_last_history_time") and (curr_time - self._last_history_time) < 0.5:
            return
        self._last_history_time = curr_time

        # Cập nhật bộ đếm
        self.counters["TOTAL"] += 1
        if gate_id == 1:
            self.counters["GATE_1"] += 1
        elif gate_id == 2:
            self.counters["GATE_2"] += 1
        elif gate_id == 3:
            self.counters["GATE_3"] += 1
        elif gate_id == 4:
            self.counters["GATE_4"] += 1
        elif gate_id == 5:
            self.counters["GATE_5"] += 1
        else:
            self.counters["REJECT"] += 1

        # Cập nhật hiển thị giao diện tức thì
        self.lbl_cnt_total.setText(str(self.counters["TOTAL"]))
        self.lbl_cnt_g1.setText(str(self.counters["GATE_1"]))
        self.lbl_cnt_g2.setText(str(self.counters["GATE_2"]))
        self.lbl_cnt_g3.setText(str(self.counters["GATE_3"]))
        self.lbl_cnt_g4.setText(str(self.counters["GATE_4"]))
        self.lbl_cnt_g5.setText(str(self.counters["GATE_5"]))
        self.lbl_cnt_reject.setText(str(self.counters["REJECT"]))

        # Thêm dòng vào bảng lịch sử
        row = self.tbl_history.rowCount()
        self.tbl_history.insertRow(row)
        self.tbl_history.setItem(row, 0, QTableWidgetItem(info.get("timestamp", "")))
        self.tbl_history.setItem(row, 1, QTableWidgetItem(info.get("qr_data", "N/A")))
        self.tbl_history.setItem(row, 2, QTableWidgetItem(info.get("color", "N/A")))
        self.tbl_history.setItem(row, 3, QTableWidgetItem(f"Cửa {gate_id}"))

        # Giới hạn 50 dòng log gần nhất
        if self.tbl_history.rowCount() > 50:
            self.tbl_history.removeRow(0)

        # Chuyển focus nhẹ bảng lịch sử xuống dòng mới nhất
        self.tbl_history.scrollToBottom()

    def reset_counters(self):
        for k in self.counters:
            self.counters[k] = 0
        self.lbl_cnt_total.setText("0")
        self.lbl_cnt_g1.setText("0")
        self.lbl_cnt_g2.setText("0")
        self.lbl_cnt_g3.setText("0")
        self.lbl_cnt_g4.setText("0")
        self.lbl_cnt_g5.setText("0")
        self.lbl_cnt_reject.setText("0")
        self.tbl_history.setRowCount(0)
        self.add_log("Đã reset tất cả bộ đếm sản phẩm.", "INFO")

    def generate_and_open_qr_folder(self):
        """Tạo mã QR tem in dán cho 5 Quận và mở thư mục qr_codes"""
        try:
            from tools.generate_qr_codes import generate_district_qr_codes
            files = generate_district_qr_codes("qr_codes")
            
            # Mở thư mục Windows Explorer
            qr_dir = os.path.abspath("qr_codes")
            os.startfile(qr_dir)
            
            self.add_log(f"Đã tạo {len(files)} mã QR và mở thư mục: {qr_dir}", "INFO")
            QMessageBox.information(
                self, "Thành công", 
                f"Đã tạo thành công 5 mã QR cho các Quận/Huyện Đà Nẵng!\nThư mục tem: {qr_dir}"
            )
        except Exception as e:
            self.add_log(f"Lỗi tạo mã QR: {e}", "ERROR")
            QMessageBox.critical(self, "Lỗi", f"Không thể tạo mã QR: {e}")

    def on_color_selected(self, color_name):
        colors = self.config.get("colors", {})
        c_cfg = colors.get(color_name, {})
        lower1 = c_cfg.get("lower1", [0, 0, 0])
        upper1 = c_cfg.get("upper1", [180, 255, 255])

        self.sld_h_min.setValue(lower1[0])
        self.sld_h_max.setValue(upper1[0])
        self.sld_s_min.setValue(lower1[1])
        self.sld_s_max.setValue(upper1[1])
        self.sld_v_min.setValue(lower1[2])
        self.sld_v_max.setValue(upper1[2])

    def on_slider_changed(self):
        color_name = self.cmb_colors.currentText()
        if "colors" not in self.config:
            self.config["colors"] = {}
        if color_name not in self.config["colors"]:
            self.config["colors"][color_name] = {}

        self.config["colors"][color_name]["lower1"] = [
            self.sld_h_min.value(), self.sld_s_min.value(), self.sld_v_min.value()
        ]
        self.config["colors"][color_name]["upper1"] = [
            self.sld_h_max.value(), self.sld_s_max.value(), self.sld_v_max.value()
        ]

        # Cập nhật ngay lập tức sang luồng camera
        self.camera_thread.update_color_config(self.config["colors"])

    def save_hsv_tuning(self):
        self._save_config()
        QMessageBox.information(self, "Thông báo", "Đã lưu cài đặt ngưỡng màu HSV mới!")

    def save_plc_config(self):
        self.config["plc"]["ip"] = self.txt_plc_ip.text()
        self.config["plc"]["port"] = self.spin_plc_port.value()
        self.config["plc"]["slave_id"] = self.spin_slave_id.value()
        self.config["plc"]["register_address"] = self.spin_reg_addr.value()

        self._save_config()

        # Re-connect với thông số mới
        self.plc_client.host = self.config["plc"]["ip"]
        self.plc_client.port = self.config["plc"]["port"]
        self.plc_client.slave_id = self.config["plc"]["slave_id"]
        
        self.plc_client.disconnect()
        self.connect_plc()

    def send_manual_plc_signal(self, val):
        reg = self.config.get("plc", {}).get("register_address", 0)
        success = self.plc_client.write_register(reg, val)
        if success:
            self.add_log(f"[Thủ công] Đã gửi tín hiệu {val} tới PLC Holding Register {reg}", "INFO")
        else:
            self.add_log(f"[Thủ công] Lỗi gửi PLC: {self.plc_client.last_error}", "ERROR")

    def load_rules_to_table(self):
        rules = self.config.get("rules", [])
        self.tbl_rules.setRowCount(0)
        for r in rules:
            row = self.tbl_rules.rowCount()
            self.tbl_rules.insertRow(row)
            self.tbl_rules.setItem(row, 0, QTableWidgetItem(r.get("name", "")))
            self.tbl_rules.setItem(row, 1, QTableWidgetItem(r.get("qr_contains", "")))
            self.tbl_rules.setItem(row, 2, QTableWidgetItem(r.get("color", "")))
            self.tbl_rules.setItem(row, 3, QTableWidgetItem(str(r.get("gate_id", 1))))
            self.tbl_rules.setItem(row, 4, QTableWidgetItem(str(r.get("plc_signal_value", 1))))

    def save_rules_from_table(self):
        new_rules = []
        for r in range(self.tbl_rules.rowCount()):
            name = self.tbl_rules.item(r, 0).text() if self.tbl_rules.item(r, 0) else ""
            qr = self.tbl_rules.item(r, 1).text() if self.tbl_rules.item(r, 1) else ""
            color = self.tbl_rules.item(r, 2).text() if self.tbl_rules.item(r, 2) else ""
            gate = int(self.tbl_rules.item(r, 3).text()) if self.tbl_rules.item(r, 3) and self.tbl_rules.item(r, 3).text().isdigit() else 1
            sig = int(self.tbl_rules.item(r, 4).text()) if self.tbl_rules.item(r, 4) and self.tbl_rules.item(r, 4).text().isdigit() else 1

            new_rules.append({
                "name": name,
                "qr_contains": qr,
                "color": color,
                "gate_id": gate,
                "plc_signal_value": sig
            })

        self.config["rules"] = new_rules
        self.camera_thread.update_rules_config(new_rules)
        self._save_config()
        QMessageBox.information(self, "Thông báo", "Đã cập nhật Bảng Quy tắc Phân loại thành công!")

    def _on_sim_register_changed(self, reg_addr, reg_val):
        """Callback từ PLC Simulator hiển thị trên Console Log (Thread-safe)"""
        msg = f"[SIMULATOR GIẢ LẬP] Đã ghi nhận Holding Register {reg_addr} = {reg_val}"
        self.camera_thread.log_message.emit(msg, "INFO")

    @pyqtSlot(str, str)
    def add_log(self, message, level="INFO"):
        t_str = time.strftime("%H:%M:%S")
        color = "#00FF66" if level == "INFO" else ("#FFCC00" if level == "WARN" else "#FF3B30")
        formatted = f'<span style="color:#888;">[{t_str}]</span> <span style="color:{color};">[{level}] {message}</span>'
        self.log_text.append(formatted)

    def closeEvent(self, event):
        """Đảm bảo giải phóng tài nguyên khi thoát ứng dụng"""
        self.stop_camera()
        self.plc_client.disconnect()
        if self.plc_simulator.running:
            self.plc_simulator.stop()
        event.accept()
