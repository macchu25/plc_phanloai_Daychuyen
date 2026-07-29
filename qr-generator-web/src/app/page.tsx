"use client";

import React, { useState, useEffect, useRef } from "react";
import QRCode from "qrcode";

interface DistrictItem {
  id: string;
  name: string;
  code: string;
  gate: number;
  color: string;
  description: string;
  count: number;
  streetAddress?: string;
}

interface ProvinceAPIItem {
  code: number;
  name: string;
}

interface DistrictAPIItem {
  code: number;
  name: string;
}

const DEFAULT_DISTRICTS: DistrictItem[] = [
  {
    id: "hai_chau",
    name: "Quận Hải Châu",
    code: "DISTRICT_HAI_CHAU",
    gate: 1,
    color: "#EF4444", // Red
    description: "Cửa số 1 - Khu vực Trung tâm",
    count: 1,
  },
  {
    id: "thanh_khe",
    name: "Quận Thanh Khê",
    code: "DISTRICT_THANH_KHE",
    gate: 2,
    color: "#22C55E", // Green
    description: "Cửa số 2 - Khu vực Phía Tây",
    count: 1,
  },
  {
    id: "lien_chieu",
    name: "Quận Liên Chiểu",
    code: "DISTRICT_LIEN_CHIEU",
    gate: 3,
    color: "#3B82F6", // Blue
    description: "Cửa số 3 - Khu Công Nghiệp",
    count: 1,
  },
  {
    id: "ngu_hanh_son",
    name: "Quận Ngũ Hành Sơn",
    code: "DISTRICT_NGU_HANH_SON",
    gate: 4,
    color: "#F97316", // Orange
    description: "Cửa số 4 - Khu Phía Nam & Du Lịch",
    count: 1,
  },
  {
    id: "cam_le",
    name: "Quận Cẩm Lệ",
    code: "DISTRICT_CAM_LE",
    gate: 5,
    color: "#A855F7", // Purple
    description: "Cửa số 5 - Khu Vực Nội Địa",
    count: 1,
  },
];

// Fallback provinces list if API is offline
const FALLBACK_PROVINCES = [
  { code: 48, name: "Thành phố Đà Nẵng" },
  { code: 79, name: "Thành phố Hồ Chí Minh" },
  { code: 1, name: "Thành phố Hà Nội" },
  { code: 74, name: "Tỉnh Bình Dương" },
  { code: 75, name: "Tỉnh Đồng Nai" },
  { code: 31, name: "Thành phố Hải Phòng" },
  { code: 92, name: "Thành phố Cần Thơ" },
];

export default function QRGeneratorPage() {
  const [selectedDistrict, setSelectedDistrict] = useState<DistrictItem>(DEFAULT_DISTRICTS[0]);
  const [batchItems, setBatchItems] = useState<DistrictItem[]>(DEFAULT_DISTRICTS);

  // States cho API Tỉnh / Thành & Quận / Huyện
  const [provinces, setProvinces] = useState<ProvinceAPIItem[]>(FALLBACK_PROVINCES);
  const [apiDistricts, setApiDistricts] = useState<DistrictAPIItem[]>([]);
  const [selectedProvinceCode, setSelectedProvinceCode] = useState<number>(48);
  const [selectedDistrictCode, setSelectedDistrictCode] = useState<number | "">("");
  const [selectedGateNumber, setSelectedGateNumber] = useState<number>(1);
  const [loadingProvinces, setLoadingProvinces] = useState(false);
  const [loadingDistricts, setLoadingDistricts] = useState(false);

  // Dynamic Custom inputs
  const [streetAddress, setStreetAddress] = useState("");
  const [customName, setCustomName] = useState("");
  const [customCode, setCustomCode] = useState("");
  const [customGate, setCustomGate] = useState(1);
  const [orderId, setOrderId] = useState("");

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  // 1. Fetch danh sách 63 Tỉnh Thành từ API công khai Việt Nam
  useEffect(() => {
    async function fetchProvinces() {
      setLoadingProvinces(true);
      try {
        const res = await fetch("https://provinces.open-api.vn/api/p/");
        if (res.ok) {
          const data = await res.json();
          setProvinces(data);
        }
      } catch (err) {
        console.warn("Could not fetch online provinces, using fallback.", err);
      } finally {
        setLoadingProvinces(false);
      }
    }
    fetchProvinces();
  }, []);

  // 2. Fetch danh sách Quận Huyện theo Tỉnh Thành được chọn
  useEffect(() => {
    if (!selectedProvinceCode) return;
    async function fetchDistricts() {
      setLoadingDistricts(true);
      try {
        const res = await fetch(`https://provinces.open-api.vn/api/p/${selectedProvinceCode}?depth=2`);
        if (res.ok) {
          const data = await res.json();
          setApiDistricts(data.districts || []);
          if (data.districts && data.districts.length > 0) {
            setSelectedDistrictCode(data.districts[0].code);
          }
        }
      } catch (err) {
        console.warn("Could not fetch districts for province", selectedProvinceCode, err);
      } finally {
        setLoadingDistricts(false);
      }
    }
    fetchDistricts();
  }, [selectedProvinceCode]);

  // Helper tạo URL Google Maps thu gọn + Nhúng Cửa PLC Tự Động (_GATE_X) giúp máy tính PLC nhận diện tức thì
  const getGoogleMapsURL = (districtName: string, districtCode: string, street: string, gate: number) => {
    const fullLocation = street
      ? `${street}, ${districtName}`
      : districtName;
    const query = encodeURIComponent(fullLocation);
    return `https://maps.google.com/?q=${query}#${districtCode}_GATE_${gate}`;
  };

  // Render single QR code preview on Canvas
  useEffect(() => {
    if (canvasRef.current) {
      const mapsURL = getGoogleMapsURL(
        selectedDistrict.name,
        selectedDistrict.code,
        selectedDistrict.streetAddress || streetAddress,
        selectedDistrict.gate
      );
      const qrData = orderId
        ? `${mapsURL}_ORD_${orderId}`
        : mapsURL;

      QRCode.toCanvas(canvasRef.current, qrData, {
        width: 240,
        margin: 2,
        color: {
          dark: "#000000",
          light: "#FFFFFF",
        },
      }, (error) => {
        if (error) console.error("Error generating QR:", error);
      });
    }
  }, [selectedDistrict, streetAddress, orderId]);

  const handleDownloadPNG = () => {
    if (canvasRef.current) {
      const link = document.createElement("a");
      link.download = `QR_${selectedDistrict.id.toUpperCase()}.png`;
      link.href = canvasRef.current.toDataURL("image/png");
      link.click();
    }
  };

  const handlePrint = () => {
    window.print();
  };

  // Helper chuyển đổi tiếng Việt có dấu sang slug ASCII chuẩn cho QR Code
  const removeAccents = (str: string) => {
    return str
      .normalize("NFD")
      .replace(/[\u0300-\u036f]/g, "")
      .replace(/đ/g, "d")
      .replace(/Đ/g, "D")
      .toUpperCase()
      .replace(/[^A-Z0-9]/g, "_");
  };

  // Tạo mã QR từ API Tỉnh/Quận + Số nhà địa chỉ cụ thể
  const handleAddAPIDistrict = () => {
    const prov = provinces.find((p) => p.code === Number(selectedProvinceCode));
    const dist = apiDistricts.find((d) => d.code === Number(selectedDistrictCode));

    if (!dist) return;

    const asciiName = removeAccents(dist.name);
    const generatedCode = `DISTRICT_${asciiName}`;

    const newDistrict: DistrictItem = {
      id: `${selectedProvinceCode}_${selectedDistrictCode}_${Date.now()}`,
      name: `${dist.name} (${prov?.name || ""})`,
      code: generatedCode,
      gate: Number(selectedGateNumber),
      color: "#06B6D4",
      description: streetAddress
        ? `ĐC: ${streetAddress}, ${dist.name}`
        : `Tỉnh/Thành: ${prov?.name || ""} | Cửa PLC: ${selectedGateNumber}`,
      count: 1,
      streetAddress: streetAddress.trim(),
    };

    setBatchItems((prev) => [...prev, newDistrict]);
    setSelectedDistrict(newDistrict);
  };

  const handleAddCustomDistrict = () => {
    if (!customName || !customCode) return;
    const newDistrict: DistrictItem = {
      id: customCode.toLowerCase().replace(/\s+/g, "_"),
      name: customName,
      code: customCode.toUpperCase(),
      gate: Number(customGate),
      color: "#06B6D4",
      description: `Cửa số ${customGate} - Tùy chỉnh`,
      count: 1,
      streetAddress: streetAddress.trim(),
    };
    setBatchItems((prev) => [...prev, newDistrict]);
    setSelectedDistrict(newDistrict);
    setCustomName("");
    setCustomCode("");
  };

  const updateBatchCount = (id: string, delta: number) => {
    setBatchItems((prev) =>
      prev.map((item) =>
        item.id === id ? { ...item, count: Math.max(0, item.count + delta) } : item
      )
    );
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 p-4 md:p-8">
      {/* Top Header Navigation (No Print) */}
      <header className="no-print max-w-6xl mx-auto mb-8 border-b border-slate-800 pb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-semibold mb-2">
            <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse"></span>
            Hệ Thống Tem Dán Giao Hàng & Phân Loại PLC
          </div>
          <h1 className="text-2xl md:text-3xl font-extrabold bg-gradient-to-r from-cyan-400 via-blue-500 to-indigo-500 bg-clip-text text-transparent">
            TẠO MÃ QR ĐỊA CHỈ GIAO HÀNG & PHÂN LOẠI
          </h1>
          <p className="text-slate-400 text-sm mt-1">
            Quét bằng Điện Thoại mở vị trí Số Nhà trên Google Maps | Quét bằng Webcam kích hoạt Cửa PLC
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={handlePrint}
            className="px-4 py-2 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold rounded-lg shadow-lg shadow-blue-500/20 transition-all flex items-center gap-2"
          >
            🖨️ In Tem Hàng Loạt
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="no-print max-w-6xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Left Column: API Select Form & Controls */}
        <div className="lg:col-span-7 space-y-6">
          {/* 1. API Form Selector + Street Address Input */}
          <div className="bg-slate-900/90 border border-cyan-500/40 rounded-xl p-5 backdrop-blur-sm shadow-xl ring-1 ring-cyan-500/20">
            <h2 className="text-sm font-bold text-cyan-400 tracking-wider uppercase mb-3 flex items-center gap-2">
              🏡 Nhập Địa Chỉ Cụ Thể (Số Nhà, Đường, Quận/Huyện)
            </h2>
            <p className="text-xs text-slate-400 mb-4">
              Điện thoại quét mã sẽ định vị chính xác tới Tận Số Nhà trên Google Maps!
            </p>

            <div className="space-y-3">
              {/* Input: Số nhà, Tên đường cụ thể */}
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1">
                  1. Số nhà, Tên đường (Địa chỉ cụ thể):
                </label>
                <input
                  type="text"
                  placeholder="VD: 123 Nguyễn Văn Linh, Phường Nam Dương"
                  value={streetAddress}
                  onChange={(e) => setStreetAddress(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-yellow-300 font-bold focus:outline-none focus:border-cyan-500"
                />
              </div>

              {/* Select 2: Tỉnh / Thành phố */}
              <div>
                <label className="text-xs font-bold text-slate-300 block mb-1">
                  2. Chọn Tỉnh / Thành phố:
                </label>
                <select
                  value={selectedProvinceCode}
                  onChange={(e) => setSelectedProvinceCode(Number(e.target.value))}
                  className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-cyan-400 font-bold focus:outline-none focus:border-cyan-500 cursor-pointer"
                >
                  {provinces.map((prov) => (
                    <option key={prov.code} value={prov.code}>
                      {prov.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Select 3: Quận / Huyện & Select 4: Cửa PLC */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1">
                    3. Chọn Quận / Huyện:
                  </label>
                  <select
                    value={selectedDistrictCode}
                    onChange={(e) => setSelectedDistrictCode(Number(e.target.value))}
                    disabled={loadingDistricts}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-bold focus:outline-none focus:border-cyan-500 cursor-pointer disabled:opacity-50"
                  >
                    {loadingDistricts ? (
                      <option>Đang tải danh sách Quận/Huyện...</option>
                    ) : (
                      apiDistricts.map((dist) => (
                        <option key={dist.code} value={dist.code}>
                          {dist.name}
                        </option>
                      ))
                    )}
                  </select>
                </div>

                <div>
                  <label className="text-xs font-bold text-slate-300 block mb-1">
                    4. Gán Cửa PLC (Signal):
                  </label>
                  <select
                    value={selectedGateNumber}
                    onChange={(e) => setSelectedGateNumber(Number(e.target.value))}
                    className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-emerald-400 font-bold focus:outline-none focus:border-cyan-500 cursor-pointer"
                  >
                    {[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 99].map((g) => (
                      <option key={g} value={g}>
                        {g === 99 ? "Cửa Loại (Reject - Sig: 99)" : `Cửa số ${g} (Signal: ${g})`}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Action button */}
              <button
                onClick={handleAddAPIDistrict}
                className="w-full mt-2 py-3 bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white font-extrabold rounded-lg text-sm transition-all shadow-lg shadow-cyan-600/20 flex items-center justify-center gap-2"
              >
                <span>➕ Tạo Mã QR Số Nhà & Thêm Vào In Tem</span>
              </button>
            </div>
          </div>

          {/* 2. Preset Buttons Grid (Đà Nẵng Nhanh) */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
            <h2 className="text-sm font-bold text-cyan-400 tracking-wider uppercase mb-4 flex items-center gap-2">
              📍 Nút Chọn Nhanh (5 Quận Đà Nẵng)
            </h2>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {DEFAULT_DISTRICTS.map((item) => {
                const isSelected = selectedDistrict.id === item.id;
                return (
                  <button
                    key={item.id}
                    onClick={() => setSelectedDistrict(item)}
                    className={`p-4 rounded-xl border text-left transition-all ${
                      isSelected
                        ? "bg-slate-800 border-cyan-500 ring-2 ring-cyan-500/30 shadow-lg shadow-cyan-500/10"
                        : "bg-slate-900 border-slate-800 hover:border-slate-700 hover:bg-slate-850"
                    }`}
                  >
                    <div className="flex justify-between items-center mb-1">
                      <span className="font-bold text-base text-slate-100">{item.name}</span>
                      <span
                        className="px-2 py-0.5 rounded text-xs font-bold text-white"
                        style={{ backgroundColor: item.color }}
                      >
                        Cửa {item.gate}
                      </span>
                    </div>
                    <p className="text-xs text-slate-400">{item.description}</p>
                    <code className="text-[11px] text-cyan-400 mt-2 block font-mono">
                      {item.code}
                    </code>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3. Batch Print Quantity Selector */}
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-5 backdrop-blur-sm">
            <h2 className="text-sm font-bold text-cyan-400 tracking-wider uppercase mb-4 flex items-center justify-between">
              <span>📋 Danh Sách Tem Cần In Hàng Loạt</span>
              <button
                onClick={handlePrint}
                className="text-xs bg-blue-600 hover:bg-blue-500 text-white px-3 py-1 rounded font-bold transition-all"
              >
                🖨️ In Trang Này
              </button>
            </h2>
            <div className="space-y-2 max-h-72 overflow-y-auto pr-1">
              {batchItems.map((item) => (
                <div
                  key={item.id}
                  className="flex items-center justify-between p-3 bg-slate-950 border border-slate-800/80 rounded-lg"
                >
                  <div>
                    <span className="font-bold text-sm text-slate-200">{item.name}</span>
                    {item.streetAddress && (
                      <span className="text-xs text-yellow-400 block font-semibold">
                        📍 {item.streetAddress}
                      </span>
                    )}
                    <span className="text-xs text-cyan-400 font-mono">(Cửa {item.gate})</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => updateBatchCount(item.id, -1)}
                      className="w-7 h-7 bg-slate-800 hover:bg-slate-700 rounded text-slate-200 font-bold flex items-center justify-center"
                    >
                      -
                    </button>
                    <span className="w-8 text-center font-bold text-cyan-400 text-sm">
                      {item.count}
                    </span>
                    <button
                      onClick={() => updateBatchCount(item.id, 1)}
                      className="w-7 h-7 bg-slate-800 hover:bg-slate-700 rounded text-slate-200 font-bold flex items-center justify-center"
                    >
                      +
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Right Column: Live Card Preview & PNG Download */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-slate-900/80 border border-slate-800 rounded-xl p-6 backdrop-blur-sm sticky top-8 text-center">
            <h2 className="text-sm font-bold text-cyan-400 tracking-wider uppercase mb-4">
              🖼️ Xem Trước Tem Dán Giao Hàng
            </h2>

            {/* Sticker Preview Card */}
            <div className="inline-block bg-white text-black p-5 rounded-2xl shadow-2xl border-4 border-slate-800 max-w-xs mx-auto text-center w-full">
              <div className="border-b-2 border-dashed border-gray-300 pb-3 mb-3">
                <span className="text-xs font-black tracking-widest text-gray-500 block uppercase">
                  VIETNAM LOGISTICS
                </span>

                {/* Hiển thị Số nhà, Tên đường nếu có */}
                {(selectedDistrict.streetAddress || streetAddress) && (
                  <div className="text-sm font-black text-blue-700 uppercase mt-1 leading-snug">
                    📍 {selectedDistrict.streetAddress || streetAddress}
                  </div>
                )}

                <span className="text-base font-extrabold text-black uppercase block leading-tight mt-0.5">
                  {selectedDistrict.name}
                </span>
              </div>

              {/* QR Code Canvas */}
              <div className="flex justify-center my-2">
                <canvas ref={canvasRef} className="rounded-lg shadow-sm border border-gray-100" />
              </div>

              <div className="mt-3 pt-3 border-t-2 border-dashed border-gray-300">
                <div className="inline-block bg-black text-white px-3 py-1 rounded-full text-xs font-black tracking-wider uppercase mb-1">
                  CỬA PLC SỐ: {selectedDistrict.gate}
                </div>
                <div className="text-[10px] font-bold text-gray-600 mt-1">
                  📱 ĐT quét mở vị trí Số Nhà trên Google Maps
                </div>
              </div>
            </div>

            {/* Optional Order ID Input */}
            <div className="mt-6 text-left">
              <label className="text-xs text-slate-400 font-bold block mb-1">
                Gắn Mã Đơn Hàng (Tùy chọn):
              </label>
              <input
                type="text"
                placeholder="VD: ORD-99823"
                value={orderId}
                onChange={(e) => setOrderId(e.target.value)}
                className="w-full bg-slate-950 border border-slate-800 rounded-lg px-3 py-2 text-sm text-slate-100 font-mono focus:outline-none focus:border-cyan-500"
              />
            </div>

            {/* Actions */}
            <div className="mt-6 flex gap-3">
              <button
                onClick={handleDownloadPNG}
                className="flex-1 py-3 bg-cyan-600 hover:bg-cyan-500 text-white font-bold rounded-xl text-sm transition-all shadow-lg shadow-cyan-600/20"
              >
                💾 Tải Ảnh PNG In Tem
              </button>
            </div>
          </div>
        </div>
      </main>

      {/* Printable Sheet Layout (Only visible during Window Print) */}
      <div className="hidden print:block print-area">
        {batchItems.flatMap((item) =>
          Array.from({ length: item.count }).map((_, index) => (
            <PrintableCard key={`${item.id}-${index}`} district={item} />
          ))
        )}
      </div>
    </div>
  );
}

// Printable Card Component for Sticker Sheet
function PrintableCard({ district }: { district: DistrictItem }) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  useEffect(() => {
    if (canvasRef.current) {
      const fullAddr = district.streetAddress
        ? `${district.streetAddress}, ${district.name} Viet Nam`
        : `${district.name} Viet Nam`;
      const mapsURL = `https://maps.google.com/?q=${encodeURIComponent(fullAddr)}#${district.code}_GATE_${district.gate}`;

      QRCode.toCanvas(canvasRef.current, mapsURL, {
        width: 180,
        margin: 1,
      });
    }
  }, [district]);

  return (
    <div className="print-card p-4 text-center border-2 border-black rounded-lg bg-white text-black">
      <div className="text-xs font-bold uppercase text-gray-600">VIETNAM LOGISTICS</div>
      {district.streetAddress && (
        <div className="text-xs font-black text-blue-700 uppercase leading-snug">
          📍 {district.streetAddress}
        </div>
      )}
      <div className="text-base font-black uppercase text-black leading-tight">{district.name}</div>
      <div className="flex justify-center my-2">
        <canvas ref={canvasRef} />
      </div>
      <div className="bg-black text-white font-black px-2 py-0.5 rounded text-xs inline-block">
        CỬA PLC: {district.gate}
      </div>
      <div className="text-[9px] font-bold text-gray-600 mt-1">📱 ĐT Quét Định Vị Số Nhà Google Maps</div>
    </div>
  );
}
