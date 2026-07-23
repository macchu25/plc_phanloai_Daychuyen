import cv2
import logging

logger = logging.getLogger(__name__)

class QRScanner:
    """
    Module quét và giải mã mã QR từ hình ảnh bằng OpenCV QRCodeDetector 
    và hỗ trợ pyzbar nếu có cài đặt.
    """
    def __init__(self):
        self.opencv_detector = cv2.QRCodeDetector()
        self.has_pyzbar = False
        try:
            from pyzbar import pyzbar
            self.pyzbar = pyzbar
            self.has_pyzbar = True
            logger.info("PyZbar module loaded successfully.")
        except Exception:
            logger.info("PyZbar not available. Using OpenCV QRCodeDetector.")

    def detect_and_decode(self, frame):
        """
        Phát hiện mã QR trong frame hình ảnh.
        Trả về: list các dict {"data": str, "bbox": np.ndarray}
        """
        results = []
        if frame is None:
            return results

        # 1. Thử giải mã bằng pyzbar nếu có (tốc độ & độ nhạy tốt hơn)
        if self.has_pyzbar:
            try:
                decoded_objects = self.pyzbar.decode(frame)
                for obj in decoded_objects:
                    qr_data = obj.data.decode("utf-8", errors="ignore")
                    pts = obj.polygon
                    if len(pts) == 4:
                        bbox = [[p.x, p.y] for p in pts]
                    else:
                        rect = obj.rect
                        bbox = [
                            [rect.left, rect.top],
                            [rect.left + rect.width, rect.top],
                            [rect.left + rect.width, rect.top + rect.height],
                            [rect.left, rect.top + rect.height]
                        ]
                    results.append({
                        "data": qr_data,
                        "bbox": bbox,
                        "method": "pyzbar"
                    })
                if results:
                    return results
            except Exception as e:
                logger.warning(f"PyZbar error: {e}")

        # 2. Thuật toán OpenCV mặc định nếu pyzbar không tìm thấy hoặc chưa cài
        try:
            retval, decoded_info, points, _ = self.opencv_detector.detectAndDecodeMulti(frame)
            if retval and points is not None:
                for info, point in zip(decoded_info, points):
                    if info:
                        results.append({
                            "data": info,
                            "bbox": point.astype(int).tolist(),
                            "method": "opencv"
                        })
            elif not retval:
                # Thử single detect
                data, bbox, _ = self.opencv_detector.detectAndDecode(frame)
                if data and bbox is not None:
                    results.append({
                        "data": data,
                        "bbox": bbox[0].astype(int).tolist(),
                        "method": "opencv"
                    })
        except Exception as e:
            logger.warning(f"OpenCV QR detect error: {e}")

        return results
