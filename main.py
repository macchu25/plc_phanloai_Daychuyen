import sys
import logging

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

def main():
    try:
        from PyQt5.QtWidgets import QApplication
        from src.ui.main_window import MainWindow
    except ImportError as e:
        print(f"[ERROR] Thư viện PyQt5 chưa được cài đặt: {e}")
        print("Vui lòng chạy lệnh: pip install -r requirements.txt")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setApplicationName("Hệ Thống Phân Loại Sản Phẩm QR & Màu Sắc Kết Nối PLC")

    window = MainWindow(config_path="config.json")
    window.show()

    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
