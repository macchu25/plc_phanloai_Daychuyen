import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class ColorDetector:
    """
    Module nhận diện màu sắc dựa trên không gian màu HSV và ngưỡng cài đặt.
    """
    def __init__(self, color_config=None):
        self.color_config = color_config or self._get_default_colors()

    def _get_default_colors(self):
        return {
            "RED": {
                "lower1": [0, 120, 70], "upper1": [10, 255, 255],
                "lower2": [170, 120, 70], "upper2": [180, 255, 255],
                "display_color": "#FF3B30"
            },
            "GREEN": {
                "lower1": [35, 80, 70], "upper1": [85, 255, 255],
                "display_color": "#34C759"
            },
            "BLUE": {
                "lower1": [90, 80, 70], "upper1": [130, 255, 255],
                "display_color": "#007AFF"
            },
            "YELLOW": {
                "lower1": [15, 100, 100], "upper1": [35, 255, 255],
                "display_color": "#FFCC00"
            }
        }

    def update_config(self, new_config):
        """Cập nhật dải HSV từ giao diện GUI"""
        self.color_config = new_config

    def detect_color(self, frame, roi_rect=None, min_ratio=0.04):
        """
        Nhận diện màu chủ đạo trong vùng ROI hoặc toàn bộ khung hình.
        roi_rect: (x, y, w, h) hoặc None
        min_ratio: Ngưỡng tỷ lệ phủ diện tích tối thiểu (0.04 = 4%)
        """
        if frame is None:
            return {"dominant_color": "UNKNOWN", "score": 0.0, "best_contour": None}

        # 1. Cắt vùng ROI nếu có
        if roi_rect is not None:
            x, y, w, h = roi_rect
            # Đảm bảo nằm trong kích thước frame
            fh, fw = frame.shape[:2]
            x, y = max(0, x), max(0, y)
            w, h = min(fw - x, w), min(fh - y, h)
            if w <= 0 or h <= 0:
                cropped = frame
                offset_x, offset_y = 0, 0
            else:
                cropped = frame[y:y+h, x:x+w]
                offset_x, offset_y = x, y
        else:
            cropped = frame
            offset_x, offset_y = 0, 0

        # Lọc nhiễu nhẹ
        blurred = cv2.GaussianBlur(cropped, (5, 5), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        total_pixels = cropped.shape[0] * cropped.shape[1]

        best_color = "UNKNOWN"
        max_ratio = 0.0
        best_contour = None
        best_mask = None
        color_scores = {}

        # 2. Duyệt qua từng dải màu định nghĩa
        for color_name, params in self.color_config.items():
            lower1 = np.array(params.get("lower1", [0, 0, 0]), dtype=np.uint8)
            upper1 = np.array(params.get("upper1", [180, 255, 255]), dtype=np.uint8)
            
            mask = cv2.inRange(hsv, lower1, upper1)

            # Trường hợp đặc biệt của màu Đỏ (Red có 2 khoảng HSV 0-10 và 170-180)
            if "lower2" in params and "upper2" in params:
                lower2 = np.array(params["lower2"], dtype=np.uint8)
                upper2 = np.array(params["upper2"], dtype=np.uint8)
                mask2 = cv2.inRange(hsv, lower2, upper2)
                mask = cv2.bitwise_or(mask, mask2)

            # Khử nhiễu Morphological (Opening & Closing)
            kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

            matched_pixels = cv2.countNonZero(mask)
            ratio = matched_pixels / float(total_pixels) if total_pixels > 0 else 0
            color_scores[color_name] = ratio

            # Cần tỷ lệ màu vượt ngưỡng tối thiểu (mặc định > 4% để lọc da người và phông nền)
            if ratio >= min_ratio and ratio > max_ratio:
                max_ratio = ratio
                best_color = color_name
                best_mask = mask

                # Tìm contour lớn nhất đại diện cho vật thể có màu
                contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                if contours:
                    c = max(contours, key=cv2.contourArea)
                    # Chuyển đổi tọa độ contour về tọa độ gốc của frame
                    c_adjusted = c.copy()
                    c_adjusted[:, :, 0] += offset_x
                    c_adjusted[:, :, 1] += offset_y
                    best_contour = c_adjusted

        return {
            "dominant_color": best_color,
            "confidence": round(max_ratio * 100, 1),
            "color_scores": color_scores,
            "best_contour": best_contour,
            "mask": best_mask
        }
