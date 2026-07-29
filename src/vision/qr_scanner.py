import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)

class QRScanner:
    """
    Module quét và giải mã mã QR đa tầng (Multi-pass QR Decoder):
    Tự động lọc tương phản CLAHE, xám hóa, binarization giúp đọc mã QR 
    từ màn hình điện thoại / máy tính bị chói bóng hoặc mã QR tem in dán hàng.
    """
    def __init__(self):
        self.detector = cv2.QRCodeDetector()

    def detect_and_decode(self, frame):
        """
        Phát hiện mã QR trong frame hình ảnh với nhiều cấp độ xử lý.
        Trả về: list các dict {"data": str, "bbox": np.ndarray}
        """
        if frame is None:
            return []

        results = []

        # Các biến thể xử lý hình ảnh khử chói bóng màn hình điện thoại
        processed_frames = []

        # 1. Khung hình gốc
        processed_frames.append(frame)

        # 2. Khung hình Xám (Grayscale)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        processed_frames.append(gray)

        # 3. Nâng tương phản CLAHE (Cực tốt để đọc QR từ màn hình ĐT bị lóa bóng đèn)
        try:
            clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
            enhanced_gray = clahe.apply(gray)
            processed_frames.append(enhanced_gray)

            # 4. Ngưỡng nhị phân Binarization (Otsu Threshold)
            _, thresh = cv2.threshold(enhanced_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            processed_frames.append(thresh)
        except Exception:
            pass

        # 5. Phóng to vùng trung tâm (Center Crop Zoom 1.3x) nếu QR nhỏ
        fh, fw = frame.shape[:2]
        ch_start, ch_end = int(fh * 0.15), int(fh * 0.85)
        cw_start, cw_end = int(fw * 0.15), int(fw * 0.85)
        cropped_center = gray[ch_start:ch_end, cw_start:cw_end]
        if cropped_center.size > 0:
            zoomed = cv2.resize(cropped_center, (fw, fh), interpolation=cv2.INTER_CUBIC)
            processed_frames.append(zoomed)

        # Thử đọc qua lần lượt các dạng ảnh
        for img in processed_frames:
            try:
                # 1. Thử Detect Multi
                retval, decoded_info, points, _ = self.detector.detectAndDecodeMulti(img)
                if retval and points is not None:
                    for info, point in zip(decoded_info, points):
                        if info and info.strip():
                            results.append({
                                "data": info.strip(),
                                "bbox": point.astype(int).tolist(),
                                "method": "opencv_multi"
                            })
                    if results:
                        return results

                # 2. Thử Detect Single
                data, bbox, _ = self.detector.detectAndDecode(img)
                if data and data.strip() and bbox is not None:
                    results.append({
                        "data": data.strip(),
                        "bbox": bbox[0].astype(int).tolist(),
                        "method": "opencv_single"
                    })
                    return results

            except Exception:
                continue

        return results
