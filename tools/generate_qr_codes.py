import os
import qrcode
from PIL import Image, ImageDraw, ImageFont

def generate_district_qr_codes(output_dir="qr_codes"):
    """
    Tạo các mã QR cho các Quận/Huyện tại Đà Nẵng với URL thu gọn (Short URL),
    ô vuông đen trắng lớn hơn 300% giúp Webcam đọc cực nhanh từ màn hình hoặc tem in dán.
    """
    os.makedirs(output_dir, exist_ok=True)

    districts = [
        {
            "name": "Hải Châu",
            "label_ascii": "HAI CHAU",
            "code": "DISTRICT_HAI_CHAU",
            "maps_url": "https://maps.google.com/?q=Quan+Hai+Chau+Da+Nang#DISTRICT_HAI_CHAU",
            "gate": 1,
            "filename": "qr_hai_chau.png"
        },
        {
            "name": "Thanh Khê",
            "label_ascii": "THANH KHE",
            "code": "DISTRICT_THANH_KHE",
            "maps_url": "https://maps.google.com/?q=Quan+Thanh+Khe+Da+Nang#DISTRICT_THANH_KHE",
            "gate": 2,
            "filename": "qr_thanh_khe.png"
        },
        {
            "name": "Liên Chiểu",
            "label_ascii": "LIEN CHIEU",
            "code": "DISTRICT_LIEN_CHIEU",
            "maps_url": "https://maps.google.com/?q=Quan+Lien+Chieu+Da+Nang#DISTRICT_LIEN_CHIEU",
            "gate": 3,
            "filename": "qr_lien_chieu.png"
        },
        {
            "name": "Ngũ Hành Sơn",
            "label_ascii": "NGU HANH SON",
            "code": "DISTRICT_NGU_HANH_SON",
            "maps_url": "https://maps.google.com/?q=Quan+Ngu+Hanh+Son+Da+Nang#DISTRICT_NGU_HANH_SON",
            "gate": 4,
            "filename": "qr_ngu_hanh_son.png"
        },
        {
            "name": "Cẩm Lệ",
            "label_ascii": "CAM LE",
            "code": "DISTRICT_CAM_LE",
            "maps_url": "https://maps.google.com/?q=Quan+Cam+Le+Da+Nang#DISTRICT_CAM_LE",
            "gate": 5,
            "filename": "qr_cam_le.png"
        }
    ]

    generated_files = []

    for d in districts:
        # 1. Tạo QR Code image với URL thu gọn (tạo các ô đen trắng to sắc nét)
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L, # Dùng L level để ô QR to dễ quét nhất
            box_size=12,
            border=4,
        )
        qr.add_data(d["maps_url"])
        qr.make(fit=True)

        qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        qw, qh = qr_img.size

        # 2. Tạo hình thẻ tem in dán hàng
        card_w = qw
        card_h = qh + 75
        card_img = Image.new("RGB", (card_w, card_h), "white")
        card_img.paste(qr_img, (0, 0))

        # 3. Vẽ nhãn tên Quận & Cửa phân loại PLC
        draw = ImageDraw.Draw(card_img)
        
        try:
            font_title = ImageFont.truetype("arial.ttf", 18)
            font_sub = ImageFont.truetype("arial.ttf", 13)
            font_hint = ImageFont.truetype("arial.ttf", 11)
        except Exception:
            font_title = ImageFont.load_default()
            font_sub = ImageFont.load_default()
            font_hint = ImageFont.load_default()

        title_text = f"QUAN {d['label_ascii']}"
        sub_text = f"CUA PLC: {d['gate']} | {d['code']}"
        hint_text = "Quet DT -> Mo Google Maps vi tri"

        draw.text((card_w // 2, qh + 8), title_text, fill="black", font=font_title, anchor="mt")
        draw.text((card_w // 2, qh + 32), sub_text, fill="#1D4ED8", font=font_sub, anchor="mt")
        draw.text((card_w // 2, qh + 52), hint_text, fill="#4B5563", font=font_hint, anchor="mt")

        # 4. Lưu ảnh tem QR
        file_path = os.path.join(output_dir, d["filename"])
        card_img.save(file_path)
        generated_files.append(file_path)

        print(f"[OK] Da tao ma QR thu gon: {file_path} (Quan {d['label_ascii']} -> Cua {d['gate']})")

    abs_dir = os.path.abspath(output_dir)
    print(f"\n[SUCCESS] DA TAO THANH CONG {len(generated_files)} MA QR TAI: {abs_dir}")
    return generated_files

if __name__ == "__main__":
    generate_district_qr_codes()
