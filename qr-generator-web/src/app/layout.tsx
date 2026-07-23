import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Tạo Mã QR Phân Loại Hàng Hóa - Đà Nẵng | Vercel QR Generator",
  description: "Web app tạo mã QR in tem dán phân loại hàng hóa theo 5 Quận Đà Nẵng kết nối Webcam PLC Classifier.",
  keywords: ["QR Code Generator", "Đà Nẵng", "Phân loại hàng hóa", "PLC", "Vercel"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="vi">
      <body className="min-h-screen antialiased bg-slate-950 text-slate-100">
        {children}
      </body>
    </html>
  );
}
