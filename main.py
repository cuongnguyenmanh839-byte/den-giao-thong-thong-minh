#!/usr/bin/env python3
"""
main.py – Điểm khởi chạy hệ thống đèn giao thông thông minh 4 hướng
Kiến trúc Master–Slave: Raspberry Pi 5 (AI Vision & Web) + Arduino Uno R3 (COM/UART)

Chạy: ./run.sh  hoặc  python3 main.py
"""
import sys
import os
import signal
import logging
from logging.handlers import RotatingFileHandler

# ─── Đăng ký đường dẫn các phân hệ trong thư mục src/ ─────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
for sub in ['src', 'src/core', 'src/hardware', 'src/vision', 'src/web']:
    p = os.path.join(ROOT_DIR, sub)
    if p not in sys.path:
        sys.path.insert(0, p)

from config import LOG_CONFIG, WEB_CONFIG, SIMULATION_MODE

# ─── Thiết lập logging ────────────────────────────────────
os.makedirs(os.path.join(ROOT_DIR, 'logs'), exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, 'data'), exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, 'models'), exist_ok=True)

fmt = logging.Formatter('%(asctime)s [%(levelname)s] %(name)s: %(message)s')
fh  = RotatingFileHandler(
    os.path.join(ROOT_DIR, LOG_CONFIG['FILE']),
    maxBytes=LOG_CONFIG['MAX_BYTES'],
    backupCount=LOG_CONFIG['BACKUP_COUNT']
)
fh.setFormatter(fmt)
ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(fmt)
logging.basicConfig(level=getattr(logging, LOG_CONFIG['LEVEL']), handlers=[fh, ch])
logger = logging.getLogger('main')

# ─── Import các phân hệ ───────────────────────────────────
from gpio_driver        import GPIODriver
from lcd_display        import LCDDisplay
from database           import Database
from traffic_controller import TrafficController, OperationMode
from vision             import VisionModule
import web_app

# ─── Biến toàn cục ────────────────────────────────────────
gpio    = None
lcd     = None
db      = None
ctrl    = None
vision  = None


def shutdown(sig=None, frame=None):
    """Dọn dẹp an toàn khi thoát."""
    logger.info("=== Đang tắt hệ thống ===")
    if vision: vision.stop()
    if ctrl:   ctrl.stop()
    if lcd:    lcd.cleanup()
    if gpio:   gpio.cleanup()
    logger.info("=== Hệ thống đã tắt an toàn ===")
    sys.exit(0)


signal.signal(signal.SIGINT,  shutdown)
signal.signal(signal.SIGTERM, shutdown)


def main():
    global gpio, lcd, db, ctrl, vision

    logger.info("=" * 60)
    logger.info("ĐÈN GIAO THÔNG THÔNG MINH 4 HƯỚNG – PI 5 + ARDUINO UNO R3")
    logger.info(f"Simulation mode: {SIMULATION_MODE}")
    logger.info("=" * 60)

    # 1. Khởi tạo giao tiếp Arduino Uno (12 LED Pin 2→13)
    logger.info("[1/5] Khởi tạo kết nối COM với Arduino Uno R3...")
    gpio = GPIODriver()

    # 2. Khởi tạo LCD 1602 I2C (trên Arduino Uno Pin A4/A5)
    logger.info("[2/5] Khởi tạo LCD 1602 I2C qua Arduino Uno...")
    lcd = LCDDisplay()
    lcd.show("He thong GT", "Dang khoi dong")

    # 3. Khởi tạo Database
    logger.info("[3/5] Khởi tạo Database...")
    db = Database()
    db.log_event('INFO', 'Hệ thống khởi động')

    # 4. Khởi tạo TrafficController
    logger.info("[4/5] Khởi tạo Traffic Controller...")
    ctrl = TrafficController(gpio, lcd, db)
    ctrl.start()
    ctrl.set_mode(OperationMode.FIXED)

    # 5. Khởi tạo Vision
    logger.info("[5/5] Khởi tạo Vision Module...")
    vision = VisionModule(ctrl, db)
    vision.start()

    # 6. Khởi tạo Web App
    web_app.init(ctrl, vision, db, gpio, lcd)
    lcd.show("Dashboard san", f":{WEB_CONFIG['PORT']}")

    ip = _get_ip()
    logger.info("=" * 60)
    logger.info("✓ Hệ thống đã sẵn sàng!")
    logger.info(f"✓ Dashboard: http://{ip}:{WEB_CONFIG['PORT']}")
    logger.info("✓ Ctrl+C để tắt")
    logger.info("=" * 60)

    # Chạy Flask (blocking, chạy trên luồng chính)
    web_app.run()


def _get_ip() -> str:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return '0.0.0.0'


if __name__ == '__main__':
    main()
