#!/usr/bin/env python3
"""
test_hardware_phase1.py – Kiểm tra phần cứng Giai đoạn 1
Chạy: python3 tests/test_hardware_phase1.py

Không cần nối đủ phần cứng – script tự phát hiện những gì có sẵn.
"""
import sys
import time
import subprocess

# ─── Màu sắc terminal ───────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
BLUE   = "\033[94m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):    print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg):  print(f"  {RED}✗{RESET} {msg}")
def warn(msg):  print(f"  {YELLOW}!{RESET} {msg}")
def info(msg):  print(f"  {BLUE}→{RESET} {msg}")
def header(msg):print(f"\n{BOLD}{msg}{RESET}\n" + "─"*50)

results = {}

# ════════════════════════════════════════════════════════════
# TEST 1: Kiểm tra Python version
# ════════════════════════════════════════════════════════════
header("TEST 1: Python Environment")
ver = sys.version_info
if ver.major == 3 and ver.minor >= 9:
    ok(f"Python {ver.major}.{ver.minor}.{ver.micro} ✓")
    results['python'] = True
else:
    fail(f"Python {ver.major}.{ver.minor} – Cần Python 3.9+")
    results['python'] = False

# ════════════════════════════════════════════════════════════
# TEST 2: Kiểm tra thư viện cần thiết
# ════════════════════════════════════════════════════════════
header("TEST 2: Kiểm tra thư viện Python")
libs = {
    'RPi.GPIO':     'RPi.GPIO',
    'smbus2':       'smbus2',
    'cv2':          'opencv-python',
    'flask':        'flask',
    'flask_cors':   'flask-cors',
    'sqlalchemy':   'SQLAlchemy',
}
missing_libs = []
for import_name, pkg_name in libs.items():
    try:
        __import__(import_name)
        ok(f"{import_name}")
    except ImportError:
        fail(f"{import_name} – Cài bằng: pip install {pkg_name}")
        missing_libs.append(pkg_name)

if missing_libs:
    warn(f"Thiếu {len(missing_libs)} thư viện. Chạy:")
    print(f"    pip install {' '.join(missing_libs)}")
    results['libs'] = False
else:
    ok("Tất cả thư viện đã có")
    results['libs'] = True

# ════════════════════════════════════════════════════════════
# TEST 3: Kiểm tra I2C và LCD
# ════════════════════════════════════════════════════════════
header("TEST 3: Quét I2C – LCD 16x2")
try:
    result = subprocess.run(['sudo', 'i2cdetect', '-y', '1'],
                            capture_output=True, text=True, timeout=10)
    output = result.stdout
    print(output)
    # Tìm địa chỉ I2C
    found_addresses = []
    for line in output.splitlines():
        parts = line.split(':')
        if len(parts) == 2:
            for token in parts[1].split():
                if token != '--':
                    found_addresses.append(token)
    if found_addresses:
        ok(f"Tìm thấy thiết bị I2C tại địa chỉ: {', '.join(['0x'+a for a in found_addresses])}")
        if '27' in found_addresses:
            ok("LCD tại 0x27 – ĐÃ XÁC NHẬN")
        elif '3f' in found_addresses:
            ok("LCD tại 0x3F – Cập nhật LCD_I2C_ADDRESS = 0x3F trong config.py")
        else:
            warn(f"Thiết bị lạ: {found_addresses} – Kiểm tra lại kết nối LCD")
        results['i2c'] = True
    else:
        fail("Không tìm thấy thiết bị I2C")
        info("Kiểm tra: sudo raspi-config → Interface Options → I2C → Enable")
        info("Kiểm tra dây VCC(5V), GND, SDA(Pin3), SCL(Pin5)")
        results['i2c'] = False
except FileNotFoundError:
    fail("Lệnh i2cdetect không tìm thấy. Cài: sudo apt install i2c-tools")
    results['i2c'] = False
except subprocess.TimeoutExpired:
    fail("i2cdetect timeout")
    results['i2c'] = False

# ════════════════════════════════════════════════════════════
# TEST 4: Kiểm tra Camera USB
# ════════════════════════════════════════════════════════════
header("TEST 4: Camera USB")
import os
video_devices = [f for f in os.listdir('/dev') if f.startswith('video')]
if video_devices:
    ok(f"Tìm thấy: {', '.join(['/dev/'+d for d in sorted(video_devices)])}")
    # Thử mở camera
    try:
        import cv2
        cap = cv2.VideoCapture(0)
        if cap.isOpened():
            ret, frame = cap.read()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                ok(f"Camera đọc frame thành công: {w}x{h} pixels")
                cv2.imwrite('/tmp/test_phase1_camera.jpg', frame)
                ok("Đã lưu ảnh test: /tmp/test_phase1_camera.jpg")
                results['camera'] = True
            else:
                fail("Camera mở được nhưng không đọc được frame")
                results['camera'] = False
            cap.release()
        else:
            fail("Không thể mở /dev/video0")
            results['camera'] = False
    except ImportError:
        warn("OpenCV chưa cài – bỏ qua test frame, thiết bị video đã nhận diện")
        results['camera'] = True
else:
    fail("Không tìm thấy /dev/video* – Cắm camera USB và thử lại")
    results['camera'] = False

# ════════════════════════════════════════════════════════════
# TEST 5: Kiểm tra GPIO – Test đèn ĐỎ Bắc (GPIO18)
# ════════════════════════════════════════════════════════════
header("TEST 5: GPIO – Test đèn ĐỎ Bắc (GPIO18)")
try:
    import RPi.GPIO as GPIO
    GPIO.setmode(GPIO.BCM)
    GPIO.setwarnings(False)

    test_pin = 18  # ĐỎ Bắc
    GPIO.setup(test_pin, GPIO.OUT)

    print(f"  Bật GPIO{test_pin} (ĐỎ Bắc)...", end='', flush=True)
    GPIO.output(test_pin, GPIO.HIGH)
    time.sleep(1.5)
    print(" BẬT")

    print(f"  Tắt GPIO{test_pin} (ĐỎ Bắc)...", end='', flush=True)
    GPIO.output(test_pin, GPIO.LOW)
    time.sleep(0.5)
    print(" TẮT")

    GPIO.cleanup()
    ok("GPIO test hoàn thành – Xác nhận đèn ĐỎ Bắc có sáng không?")
    results['gpio'] = True

except ImportError:
    fail("RPi.GPIO chưa cài. Cài: pip install RPi.GPIO")
    results['gpio'] = False
except RuntimeError as e:
    fail(f"GPIO lỗi: {e}")
    info("Đảm bảo chạy với: sudo python3 hoặc user 'pi' trong group gpio")
    results['gpio'] = False

# ════════════════════════════════════════════════════════════
# TEST 6: Kiểm tra đường dẫn model YOLO
# ════════════════════════════════════════════════════════════
header("TEST 6: Model nhận diện xe")
model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models', 'yolov8n.pt')
if os.path.exists(model_path):
    size_mb = os.path.getsize(model_path) / (1024*1024)
    ok(f"yolov8n.pt tồn tại ({size_mb:.1f} MB)")
    results['model'] = True
else:
    warn("Chưa có models/yolov8n.pt")
    info("Tải model: pip install ultralytics && python3 -c \"from ultralytics import YOLO; YOLO('yolov8n.pt')\"")
    info("Hoặc copy file .pt vào thư mục models/")
    results['model'] = False

# ════════════════════════════════════════════════════════════
# KẾT QUẢ TỔNG HỢP
# ════════════════════════════════════════════════════════════
header("KẾT QUẢ TỔNG HỢP GIAI ĐOẠN 1")

passed = sum(1 for v in results.values() if v)
total  = len(results)

for name, status in results.items():
    icon = f"{GREEN}✓{RESET}" if status else f"{RED}✗{RESET}"
    labels = {
        'python': 'Python version',
        'libs':   'Thư viện Python',
        'i2c':    'I2C / LCD',
        'camera': 'Camera USB',
        'gpio':   'GPIO / Đèn',
        'model':  'Model YOLOv8',
    }
    print(f"  {icon} {labels.get(name, name)}")

print(f"\n{BOLD}Kết quả: {passed}/{total} mục đạt{RESET}")

if passed == total:
    print(f"\n{GREEN}{BOLD}✓ GIAI ĐOẠN 1 HOÀN THÀNH – Sẵn sàng sang Giai đoạn 2!{RESET}")
elif passed >= 4:
    print(f"\n{YELLOW}{BOLD}! Hầu hết đạt – Xem mục chưa đạt và khắc phục trước khi tiếp tục{RESET}")
else:
    print(f"\n{RED}{BOLD}✗ Cần khắc phục nhiều mục trước khi sang Giai đoạn 2{RESET}")
