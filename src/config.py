"""
config.py – Cấu hình trung tâm cho hệ thống đèn giao thông thông minh
Dự án: Đèn Giao Thông Thông Minh 4 Hướng – Raspberry Pi 5 + Arduino Uno R3 (UART/COM)
Phiên bản: 2.1 (Kiến trúc Master-Slave qua cổng Serial USB)
"""

# ============================================================
# CẤU HÌNH KẾT NỐI ARDUINO UNO R3 QUA CỔNG COM (USB SERIAL)
# ============================================================
SERIAL_CONFIG = {
    'PORT': 'AUTO',                  # 'AUTO' = tự động dò /dev/ttyACM0, /dev/ttyUSB0...
    'CANDIDATE_PORTS': [
        '/dev/ttyACM0',
        '/dev/ttyACM1',
        '/dev/ttyUSB0',
        '/dev/ttyUSB1',
    ],
    'BAUDRATE': 115200,              # Tốc độ truyền chuẩn 115200 bps
    'TIMEOUT': 1.0,                  # Timeout đọc Serial (giây)
    'WRITE_TIMEOUT': 1.0,            # Timeout ghi Serial (giây)
    'BOOT_DELAY': 2.0,               # Thời gian chờ Arduino Uno reset sau khi mở cổng COM
}

# ============================================================
# PHÂN CÔNG CHÂN DIGITAL TRÊN ARDUINO UNO R3 (Dãy Pin 2 → 13)
# Lưu ý: Chân 0 (RX) và 1 (TX) dành riêng cho giao tiếp USB Serial với Pi.
# 12 chân Digital từ Pin 2 đến Pin 13 vừa khít cho 12 đèn LED (4 hướng x 3 màu).
# Logic: HIGH (5V) = đèn SÁNG, LOW (0V) = đèn TẮT
# ============================================================
GPIO_CONFIG = {
    'NORTH': {'RED': 2,  'YELLOW': 3,  'GREEN': 4},    # Bắc  (Pin 2, 3, 4)
    'SOUTH': {'RED': 5,  'YELLOW': 6,  'GREEN': 7},    # Nam  (Pin 5, 6, 7)
    'EAST':  {'RED': 8,  'YELLOW': 9,  'GREEN': 10},   # Đông (Pin 8, 9, 10)
    'WEST':  {'RED': 11, 'YELLOW': 12, 'GREEN': 13},   # Tây  (Pin 11, 12, 13)
}

# Thứ tự 12 bit khi đóng gói lệnh Serial "LEDS:xxxxxxxxxxxx"
SERIAL_LED_ORDER = [
    ('NORTH', 'RED'), ('NORTH', 'YELLOW'), ('NORTH', 'GREEN'),
    ('SOUTH', 'RED'), ('SOUTH', 'YELLOW'), ('SOUTH', 'GREEN'),
    ('EAST',  'RED'), ('EAST',  'YELLOW'), ('EAST',  'GREEN'),
    ('WEST',  'RED'), ('WEST',  'YELLOW'), ('WEST',  'GREEN'),
]

# Nhãn hiển thị cho từng hướng
DIRECTION_LABELS = {
    'NORTH': 'Bắc',
    'SOUTH': 'Nam',
    'EAST':  'Đông',
    'WEST':  'Tây',
}

# Thứ tự quay vòng pha (4 pha độc lập)
PHASE_ORDER = ['NORTH', 'EAST', 'SOUTH', 'WEST']

# ============================================================
# CẤU HÌNH I2C LCD 16x2 (CẮM TRÊN ARDUINO UNO: SDA=A4, SCL=A5)
# ============================================================
LCD_I2C_BUS = 1
LCD_I2C_ADDRESS = 0x27           # Địa chỉ I2C trên Arduino Uno (0x27 hoặc 0x3F)
LCD_COLS = 16
LCD_ROWS = 2
LCD_ENABLED = True

# ============================================================
# CẤU HÌNH CAMERA (CẮM TRÊN RASPBERRY PI)
# ============================================================
CAMERA_INDEX = 0                 # /dev/video0 – USB webcam
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
CAMERA_FPS = 30
CAMERA_WARMUP_SECONDS = 2

# ============================================================
# CẤU HÌNH THỜI GIAN ĐÈN (giây)
# CHẾ ĐỘ 1: Đèn cố định
# ============================================================
FIXED_MODE_TIMING = {
    'GREEN_TIME':  30,
    'YELLOW_TIME': 3,
    'RED_MIN_TIME': 3,
    'SAFETY_GAP':  1,
}

# ============================================================
# CẤU HÌNH THUẬT TOÁN THÍCH NGHI (CHẾ ĐỘ 2)
# ============================================================
ADAPTIVE_MODE_TIMING = {
    'GREEN_MIN':   10,
    'GREEN_MAX':   60,
    'YELLOW_TIME': 3,
    'SAFETY_GAP':  1,
    'MAX_WAIT':    120,
}

PRIORITY_WEIGHTS = {
    'VEHICLE_COUNT': 0.6,
    'WAIT_TIME':     0.4,
}

DENSITY_THRESHOLDS = {
    'LOW':    2,
    'MEDIUM': 5,
    'HIGH':   float('inf'),
}

GREEN_TIME_BY_DENSITY = {
    'LOW':    15,
    'MEDIUM': 30,
    'HIGH':   50,
}

DETECTION_SMOOTHING = {
    'WINDOW_SIZE':     5,
    'UPDATE_INTERVAL': 2.0,
    'MIN_CONFIDENCE':  0.45,
}

# ============================================================
# CẤU HÌNH NHẬN DIỆN XE (YOLOv8 / MOG2)
# ============================================================
DETECTION_CONFIG = {
    'MODEL_PATH': 'models/yolov8n.pt',
    'CONFIDENCE_THRESHOLD': 0.45,
    'NMS_IOU_THRESHOLD': 0.45,
    'DEVICE': 'cpu',
    'INFERENCE_SIZE': 320,
    'VEHICLE_CLASSES': [2, 3, 5, 7],
    'VEHICLE_CLASS_NAMES': ['car', 'motorcycle', 'bus', 'truck'],
}

DETECTION_ZONES = {
    'NORTH': [0.25, 0.0,  0.75, 0.4],
    'SOUTH': [0.25, 0.6,  0.75, 1.0],
    'EAST':  [0.6,  0.25, 1.0,  0.75],
    'WEST':  [0.0,  0.25, 0.4,  0.75],
}

# ============================================================
# CẤU HÌNH WEB DASHBOARD (Flask)
# ============================================================
WEB_CONFIG = {
    'HOST': '0.0.0.0',
    'PORT': 5000,
    'DEBUG': False,
    'SECRET_KEY': 'trafficlight2025rpi5_uno_r3',
    'STREAM_FPS': 15,
}

# ============================================================
# CẤU HÌNH DATABASE
# ============================================================
DB_CONFIG = {
    'PATH': 'data/traffic.db',
    'LOG_INTERVAL': 5,
    'MAX_HISTORY_DAYS': 7,
}

# ============================================================
# CẤU HÌNH LOG
# ============================================================
LOG_CONFIG = {
    'LEVEL': 'INFO',
    'FILE': 'logs/traffic.log',
    'MAX_BYTES': 10 * 1024 * 1024,
    'BACKUP_COUNT': 3,
}

# ============================================================
# CHẾ ĐỘ HOẠT ĐỘNG
# ============================================================
SIMULATION_MODE = False          # False = giao tiếp thực tế với Arduino Uno qua cổng COM

# ============================================================
# HẰNG SỐ TRẠNG THÁI
# ============================================================
class TrafficState:
    ALL_RED      = 'ALL_RED'
    GREEN_PHASE  = 'GREEN'
    YELLOW_PHASE = 'YELLOW'
    SAFETY_GAP   = 'SAFETY_GAP'

class OperationMode:
    FIXED    = 'FIXED'
    ADAPTIVE = 'ADAPTIVE'
    MANUAL   = 'MANUAL'
    SAFE     = 'SAFE'
