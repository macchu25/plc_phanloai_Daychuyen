# 🚀 Next.js QR Code Generator & Label Printer (Vercel Ready)

Web application tạo và in tem dán mã QR phân loại hàng hóa cho 5 Quận/Huyện tại Đà Nẵng (Hải Châu, Thanh Khê, Liên Chiểu, Ngũ Hành Sơn, Cẩm Lệ), kết nối trực tiếp với **Hệ thống phân loại Webcam PLC (Python Desktop App)**.

---

## 🛠️ Tính Năng Nổi Bật

1. **Đồng bộ mã QR với Hệ thống PLC:**
   - Mã QR sinh ra từ Web tuân thủ chuẩn payload mà ứng dụng Webcam PLC trên PC đọc được:
     - `DISTRICT_HAI_CHAU` -> **Cửa PLC 1**
     - `DISTRICT_THANH_KHE` -> **Cửa PLC 2**
     - `DISTRICT_LIEN_CHIEU` -> **Cửa PLC 3**
     - `DISTRICT_NGU_HANH_SON` -> **Cửa PLC 4**
     - `DISTRICT_CAM_LE` -> **Cửa PLC 5**

2. **In Tem Hàng Loạt (Batch Label Printer):**
   - Chọn số lượng tem cần in cho từng quận/huyện.
   - Bấm nút **"In Tem Hàng Loạt"** để in trực tiếp ra máy in tem nhiệt hoặc giấy decal dán thùng hàng (`window.print()`).

3. **Tải Ảnh PNG Tem Dán:**
   - Tải về ảnh PNG sắc nét từng tem để lưu trữ hoặc gửi máy in chuyên dụng.

4. **Tối ưu Deploy Vercel:**
   - Xây dựng bằng Next.js App Router.
   - Tốc độ tải trang tức thì, chuẩn responsive trên điện thoại, máy tính bảng và máy tính.

---

## 📦 Hướng Dẫn Chạy Trên Máy Cụm Local

```bash
cd qr-generator-web
npm install
npm run dev
```

Truy cập: `http://localhost:3000`

---

## 🌐 Hướng Dẫn Deploy Lên Vercel (Miễn Phí)

### Phương án 1: Deploy qua Vercel CLI
```bash
npx vercel
```

### Phương án 2: Deploy qua Vercel Web Dashboard
1. Đẩy thư mục `qr-generator-web` lên **GitHub**.
2. Truy cập [vercel.com](https://vercel.com/new) -> Chọn repository vừa đẩy.
3. Bấm **Deploy**. Vercel sẽ tự động build và cấp cho bạn đường link tên miền dạng: `https://your-qr-generator.vercel.app`.
