import cv2
import time
import numpy as np
import logging
from PyQt5.QtCore import QThread, pyqtSignal
from src.vision.qr_scanner import QRScanner
from src.vision.color_detector import ColorDetector

logger = logging.getLogger(__name__)

class CameraProcessingThread(QThread):
    """
    Luồng xử lý hình ảnh độc lập: Thu nạp webcam, đọc mã QR, nhận diện màu sắc, 
    khớp quy tắc phân loại và phát tín hiệu cho GUI & PLC.
    """
    # Signals truyền dữ liệu lên giao diện Desktop UI
    frame_processed = pyqtSignal(np.ndarray)            # Frame OpenCV đã vẽ chú thích
    detection_updated = pyqtSignal(dict)                # Thông tin sản phẩm vừa phân loại
    product_scanned = pyqtSignal(dict)                  # Tín hiệu quét sản phẩm thành công để nhảy bộ đếm
    log_message = pyqtSignal(str, str)                  # (Thông báo, Mức độ "INFO"/"WARN"/"ERROR")
    
    def __init__(self, config, plc_client):
        super().__init__()
        self.config = config
        self.plc_client = plc_client
        self.running = False
        
        self.qr_scanner = QRScanner()
        self.color_detector = ColorDetector(config.get("colors"))
        
        self.cap = None
        self.device_index = config.get("camera", {}).get("device_index", 0)
        self.roi_box = config.get("system", {}).get("roi_box", [340, 160, 600, 400])
        
        # Biến lọc tín hiệu chống nháy (Debouncing)
        self.last_sent_signal = None
        self.last_sent_time = 0
        self.confidence_counter = 0
        self.pending_classification = None

    def update_color_config(self, new_color_config):
        """Cập nhật cấu hình màu sắc khi người dùng chỉnh slider trên GUI"""
        self.config["colors"] = new_color_config
        self.color_detector.update_config(new_color_config)

    def update_rules_config(self, new_rules):
        """Cập nhật các quy tắc phân loại từ GUI"""
        self.config["rules"] = new_rules

    def run(self):
        """Vòng lặp chính thu nạp camera và phân tích"""
        self.running = True
        
        # Mở camera
        self.cap = cv2.VideoCapture(self.device_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            # Thử lại không cần CAP_DSHOW
            self.cap = cv2.VideoCapture(self.device_index)

        if not self.cap.isOpened():
            self.log_message.emit(f"Không thể mở Webcam (Device index: {self.device_index})", "ERROR")
            self.running = False
            return

        self.log_message.emit(f"Đã khởi chạy Webcam #{self.device_index} thành công.", "INFO")

        # Cài đặt độ phân giải nếu có
        cam_cfg = self.config.get("camera", {})
        if "width" in cam_cfg:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, cam_cfg["width"])
        if "height" in cam_cfg:
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cam_cfg["height"])

        while self.running:
            ret, frame = self.cap.read()
            if not ret or frame is None:
                time.sleep(0.03)
                continue

            # Lật hình gương cho webcam tự nhiên
            frame = cv2.flip(frame, 1)

            # 1. Đọc mã QR
            qr_results = self.qr_scanner.detect_and_decode(frame)
            qr_data = qr_results[0]["data"] if qr_results else None

            # 2. Nhận diện màu sắc trong khung ROI
            x, y, w, h = self.roi_box
            color_result = self.color_detector.detect_color(frame, (x, y, w, h))
            dominant_color = color_result.get("dominant_color", "UNKNOWN")
            color_confidence = color_result.get("confidence", 0.0)
            color_contour = color_result.get("best_contour")

            # 3. Phân loại sản phẩm dựa trên Rules
            classification = self._classify_product(qr_data, dominant_color)

            # 4. Debounce & Gửi tín hiệu PLC
            self._handle_plc_trigger(classification)

            # 5. Vẽ chú thích đồ họa trực quan trên Frame
            annotated_frame = self._draw_annotations(
                frame, qr_results, color_result, classification
            )

            # Phát tín hiệu sang GUI
            self.frame_processed.emit(annotated_frame)
            self.detection_updated.emit({
                "qr_data": qr_data or "N/A",
                "color": dominant_color,
                "color_confidence": color_confidence,
                "classification": classification,
                "timestamp": time.strftime("%H:%M:%S")
            })

            time.sleep(0.005)  # Tối ưu tốc độ xử lý nhanh nhất cho băng chuyền

        if self.cap:
            self.cap.release()
        self.log_message.emit("Đã dừng luồng Webcam.", "INFO")

    def stop(self):
        self.running = False
        self.wait()

    def _remove_accents(self, text):
        import unicodedata
        if not text:
            return ""
        text = unicodedata.normalize('NFD', text)
        text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
        return text.replace('đ', 'd').replace('Đ', 'D').upper()

    def _classify_product(self, qr_data, color_name):
        """Khớp dữ liệu QR và Màu sắc với bảng Quy tắc Phân loại (Rules)"""
        rules = self.config.get("rules", [])
        
        clean_qr = self._remove_accents(qr_data).replace("+", "_").replace(" ", "_") if qr_data else ""

        for rule in rules:
            rule_name = rule.get("name", "N/A")
            req_qr = self._remove_accents(rule.get("qr_contains", "")).replace("+", "_").replace(" ", "_")
            req_color = rule.get("color", "")

            # Kiểm tra xem mã QR (dù là URL Google Maps hay chuỗi mã) và màu sắc có khớp không
            qr_match = (not req_qr) or (clean_qr and req_qr in clean_qr)
            color_match = (not req_color) or (color_name.upper() == req_color.upper())

            if qr_match and color_match and (qr_data or color_name != "UNKNOWN"):
                return {
                    "matched": True,
                    "rule_name": rule_name,
                    "gate_id": rule.get("gate_id", 1),
                    "plc_signal_value": rule.get("plc_signal_value", 1),
                    "color": color_name,
                    "qr_data": qr_data or "None"
                }

        # Nếu phát hiện vật thể/QR nhưng không khớp rule nào -> Reject / Cửa mặc định
        if qr_data or color_name != "UNKNOWN":
            def_rule = self.config.get("default_rule", {})
            return {
                "matched": False,
                "rule_name": def_rule.get("name", "Khó xác định (Reject)"),
                "gate_id": def_rule.get("gate_id", 99),
                "plc_signal_value": def_rule.get("plc_signal_value", 99),
                "color": color_name,
                "qr_data": qr_data or "None"
            }

        return {
            "matched": False,
            "rule_name": "Đang chờ sản phẩm...",
            "gate_id": 0,
            "plc_signal_value": 0,
            "color": "NONE",
            "qr_data": "NONE"
        }

    def _handle_plc_trigger(self, classification):
        """Cơ chế lọc tín hiệu ổn định và truyền tới PLC"""
        val = classification["plc_signal_value"]
        current_time = time.time()

        # Không gửi tín hiệu rỗng (0 = không có sản phẩm)
        if val == 0:
            self.confidence_counter = 0
            self.pending_classification = None
            return

        # Đếm số khung hình liên tiếp
        if val == self.pending_classification:
            self.confidence_counter += 1
        else:
            self.pending_classification = val
            self.confidence_counter = 1

        req_frames = self.config.get("system", {}).get("detection_confidence_frames", 1)
        cooldown = 0.5 if self.config.get("system", {}).get("high_speed_conveyor_mode", True) else 1.5

        if self.confidence_counter >= req_frames:
            # Tránh gửi lặp lại tín hiệu cùng loại quá nhanh (cooldown 0.5 giây)
            if val != self.last_sent_signal or (current_time - self.last_sent_time) > cooldown:
                self.last_sent_signal = val
                self.last_sent_time = current_time
                reg_addr = self.config.get("plc", {}).get("register_address", 0)
                
                qr = classification.get("qr_data", "N/A")
                color = classification.get("color", "N/A")
                rule = classification.get("rule_name", "N/A")
                gate = classification.get("gate_id", 0)

                # In ngay lập tức ra terminal console
                log_str = f"[QUÉT TỐC ĐỘ CAO] QR: '{qr}' | Màu: '{color}' => {rule} (Cửa: {gate}, Signal: {val})"
                print(log_str)
                logger.info(log_str)

                # Phát tín hiệu nhảy bộ đếm sản phẩm trên GUI
                scan_payload = {
                    "qr_data": qr,
                    "color": color,
                    "classification": classification,
                    "timestamp": time.strftime("%H:%M:%S")
                }
                self.product_scanned.emit(scan_payload)

                # Gửi tín hiệu PLC
                success = self.plc_client.write_register(reg_addr, val)
                if success:
                    self.log_message.emit(
                        f"[QUÉT MỚI] QR: '{qr}' | Màu: '{color}' => {rule} -> Tín hiệu PLC: {val} (Cửa {gate})", 
                        "INFO"
                    )
                else:
                    self.log_message.emit(
                        f"[QUÉT MỚI] QR: '{qr}' | Màu: '{color}' => Lỗi gửi PLC: {self.plc_client.last_error}", 
                        "ERROR"
                    )

    def _draw_annotations(self, frame, qr_results, color_result, classification):
        """Vẽ chú thích đồ họa đẹp mắt trên hình ảnh thu được từ Webcam"""
        out = frame.copy()

        # 1. Vẽ vùng ROI chính (Region of Interest)
        rx, ry, rw, rh = self.roi_box
        cv2.rectangle(out, (rx, ry), (rx + rw, ry + rh), (255, 255, 255), 2)
        cv2.putText(out, "VUNG PHAN LOAI (ROI)", (rx + 5, ry - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1, cv2.LINE_AA)

        # 2. Vẽ Contour nhận diện màu sắc
        contour = color_result.get("best_contour")
        dominant_color = color_result.get("dominant_color", "UNKNOWN")
        if contour is not None and dominant_color != "UNKNOWN":
            cv2.drawContours(out, [contour], -1, (0, 255, 255), 2)
            M = cv2.moments(contour)
            if M["m00"] != 0:
                cx = int(M["m10"] / M["m00"])
                cy = int(M["m01"] / M["m00"])
                cv2.putText(out, f"MAU: {dominant_color}", (cx - 30, cy),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)

        # 3. Vẽ Bounding Box xung quanh mã QR
        for qr in qr_results:
            bbox = qr.get("bbox")
            qr_data = qr.get("data")
            if bbox:
                pts = np.array(bbox, np.int32).reshape((-1, 1, 2))
                cv2.polylines(out, [pts], True, (0, 255, 0), 3)
                x_qr, y_qr = pts[0][0]
                cv2.putText(out, f"QR: {qr_data}", (x_qr, y_qr - 10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

        # 4. Vẽ Thanh Trạng Thái HUD ở phía trên khung hình (Header Overlay)
        header_color = (40, 40, 40)
        cv2.rectangle(out, (0, 0), (out.shape[1], 45), header_color, -1)

        rule_name = classification.get("rule_name", "N/A")
        gate_id = classification.get("gate_id", 0)
        plc_val = classification.get("plc_signal_value", 0)

        status_text = f"CUA CUA: {gate_id} | SIG: {plc_val} | {rule_name}"
        text_color = (0, 255, 0) if classification.get("matched") else (200, 200, 200)
        
        cv2.putText(out, status_text, (15, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2, cv2.LINE_AA)

        return out
