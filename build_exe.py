import os
import subprocess

def build_windows_exe():
    """
    Đóng gói ứng dụng thành 1 TỆP EXE DUY NHẤT (--onefile).
    Người dùng có thể copy ĐÚNG 1 FILE EXE đi bất kỳ máy tính Windows nào mà KHÔNG LO bị thiếu thư mục _internal hay python311.dll!
    """
    print("[INFO] Bat dau dong goi phan mem thanh 1 FILE EXE DUY NHAT cho Windows...")

    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",               # ĐÓNG GÓI THÀNH 1 FILE EXE DUY NHẤT!
        "--windowed",              # Chạy ẩn cửa sổ đen console
        "--name=HeThongPhanLoaiPLC_SingleFile",
        "--add-data=config.json;.", # Nhúng kèm config.json
        "main.py"
    ]

    try:
        result = subprocess.run(cmd, check=True)
        print("\n=======================================================")
        print("[SUCCESS] DA DONG GOI THANH CONG 1 FILE EXE DUY NHAT!")
        print("Tep EXE duy nhat nam tai: dist\\HeThongPhanLoaiPLC_SingleFile.exe")
        print("-> Ban chi can copy dung 1 file này sang bat ky may tinh nao de chay!")
        print("=======================================================\n")
    except Exception as e:
        print(f"[ERROR] Loi dong goi EXE: {e}")

if __name__ == "__main__":
    build_windows_exe()
