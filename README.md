# 🚦 Hệ Thống Đèn Giao Thông Thông Minh 4 Hướng (ITS-SCADA v6.0)
**Kiến trúc Master–Slave: Raspberry Pi 5 (AI Computer Vision & Web Server) ⇄ Arduino Uno R3 (USB Serial COM)**

Dự án thiết kế và chế tạo hệ thống điều khiển đèn tín hiệu giao thông ngã tư 4 hướng (Bắc – Nam – Đông – Tây) ứng dụng **Thị giác máy tính (OpenCV MOG2 / YOLOv8)** để đếm mật độ phương tiện thời gian thực, tự động phân bổ thời gian đèn xanh thích nghi (AI Adaptive) và giám sát trực tuyến trên giao diện **Smart Traffic Command Center (Digital Twin 60 FPS)**.

---

## 🏗️ 1. Cấu Trúc Thư Mục Dự Án

```text
giaothong/
├── src/                                  # Mã nguồn Python trung tâm (Master - Raspberry Pi 5)
│   ├── config.py                         # Cấu hình tham số, thời gian pha & chân Arduino Uno
│   ├── core/                             # Bộ điều khiển trung tâm & Cơ sở dữ liệu
│   │   ├── traffic_controller.py         # Máy trạng thái hữu hạn (FSM) & Thuật toán AI Adaptive
│   │   └── database.py                   # Lưu trữ lịch sử pha & mật độ xe (SQLite3 / SQLAlchemy)
│   ├── hardware/                         # Tầng giao tiếp phần cứng (HAL - USB Serial 115200 bps)
│   │   ├── arduino_serial.py             # Cầu nối tự động dò cổng COM (/dev/ttyUSB0, /dev/ttyACM0)
│   │   ├── gpio_driver.py                # Điều khiển 12 đèn LED (Pin 2 → 13 trên Arduino Uno)
│   │   └── lcd_display.py                # Điều khiển màn hình LCD 1602 I2C (Chân A4/A5)
│   ├── vision/                           # Tầng Thị giác máy tính (Computer Vision)
│   │   └── vision.py                     # Nhận diện & đếm xe 4 vùng ROI (MOG2 / YOLOv8)
│   └── web/                              # Tầng Giao diện & Dịch vụ Web (Flask SCADA)
│       ├── web_app.py                    # REST API & MJPEG Video Streaming Server
│       ├── templates/                    # Giao diện HTML5 (index.html, camera.html)
│       └── static/                       # Tài nguyên CSS, JS (Engine vật lý xe 60 FPS), SVG
├── firmware/                             # Mã nguồn nạp cho vi điều khiển Arduino (.ino)
│   ├── arduino_uno_traffic/              # Firmware chính cho Arduino Uno R3 (Pin 2→13, A4/A5)
│   │   └── arduino_uno_traffic.ino
│   └── arduino_mega_traffic/             # Firmware mở rộng cho Arduino Mega 2560
│       └── arduino_mega_traffic.ino
├── docs/                                 # Tài liệu thuyết minh & Báo cáo khoa học
│   ├── NGUYEN_LY_HOAT_DONG_CHI_TIET.txt  # Báo cáo chi tiết 10 chương + 10 câu hỏi phản biện
│   └── NGUYEN_LY_HOAT_DONG.txt           # Tóm tắt nguyên lý vận hành hệ thống
├── scripts/                              # Kịch bản khởi chạy & dừng hệ thống
│   ├── run.sh
│   └── stop.sh
├── tests/                                # Kịch bản kiểm thử phần cứng
│   └── test_hardware_phase1.py
├── main.py                               # Điểm khởi chạy chính (Entry Point)
├── run.sh                                # Lệnh khởi chạy nhanh toàn bộ dự án
├── stop.sh                               # Lệnh dừng an toàn & tắt toàn bộ đèn LED
└── requirements.txt                      # Danh sách thư viện Python
```

---

## 🔌 2. Sơ Đồ Đấu Dây Phần Cứng (Arduino Uno R3)

> **Lưu ý**: Chân **`0 (RX)`** và **`1 (TX)`** trên Arduino Uno R3 được **để trống** phục vụ truyền thông USB Serial (`115200 bps`) với Raspberry Pi 5.

### A. 12 Đèn LED Giao Thông (`Digital Pin 2 → Pin 13`)
Mỗi chân Digital nối qua điện trở hạn dòng `220Ω – 330Ω` vào cực Dương (Anode) của LED, cực Âm (Cathode) nối chung vào `GND` của Arduino Uno:

| Hướng Giao Thông | Đèn ĐỎ (`RED`) | Đèn VÀNG (`YELLOW`) | Đèn XANH (`GREEN`) |
| :--- | :---: | :---: | :---: |
| **⬆️ BẮC (`NORTH`)** | **Pin 2** | **Pin 3** | **Pin 4** |
| **⬇️ NAM (`SOUTH`)** | **Pin 5** | **Pin 6** | **Pin 7** |
| **➡️ ĐÔNG (`EAST`)** | **Pin 8** | **Pin 9** | **Pin 10** |
| **⬅️ TÂY (`WEST`)** | **Pin 11** | **Pin 12** | **Pin 13** |

### B. Màn Hình LCD 1602 I2C (`PCF8574` cắm trên Arduino Uno R3)
* **VCC** → Chân **5V** trên Arduino Uno
* **GND** → Chân **GND** trên Arduino Uno
* **SDA** → Chân **A4** (hoặc chân `SDA` cạnh `AREF`)
* **SCL** → Chân **A5** (hoặc chân `SCL` cạnh `AREF`)

---

## 🚀 3. Hướng Dẫn Cài Đặt & Khởi Chạy

### Bước 1: Nạp code cho Arduino Uno R3
1. Mở tệp `firmware/arduino_uno_traffic/arduino_uno_traffic.ino` bằng **Arduino IDE**.
2. Chọn **Tools → Board → Arduino Uno** và cổng COM tương ứng, sau đó nhấn **Upload** *(Code sử dụng thư viện chuẩn `<Wire.h>`, không cần cài thêm thư viện ngoài)*.
3. Cắm cáp USB từ Arduino Uno R3 vào cổng USB của Raspberry Pi 5.

### Bước 2: Cài đặt môi trường trên Raspberry Pi 5
```bash
git clone <URL_GITHUB_CUA_BAN>
cd giaothong
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Bước 3: Khởi chạy bằng 1 lệnh duy nhất
```bash
./run.sh
```
* **Bảng điều khiển trung tâm (Dashboard)**: `http://localhost:5000` (hoặc `http://<IP_CUA_PI>:5000`)
* **Trang Camera AI trực tiếp**: `http://localhost:5000/camera`
* **Dừng hệ thống an toàn**: Nhấn `Ctrl + C` hoặc chạy `./stop.sh`

