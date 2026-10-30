"""
arduino_serial.py – Lớp giao tiếp Serial (UART/COM) giữa Raspberry Pi 5 và Arduino Uno R3
Quản lý kết nối tự động qua cổng USB (/dev/ttyACM0, /dev/ttyUSB0...),
đồng bộ trạng thái 12 đèn LED (Pin 2→13) và màn hình LCD 1602 I2C (Pin A4/A5).
"""
import glob
import logging
import threading
import time
from config import SERIAL_CONFIG, SIMULATION_MODE

logger = logging.getLogger(__name__)

try:
    import serial
    import serial.tools.list_ports
    _HAS_PYSERIAL = True
except ImportError:
    _HAS_PYSERIAL = False
    logger.warning("Không tìm thấy thư viện pyserial – chạy ở chế độ mô phỏng")


class ArduinoSerialBridge:
    """
    Singleton quản lý kết nối cổng COM (USB Serial) tới Arduino Uno R3.
    Đảm bảo thread-safe khi cả GPIODriver và LCDDisplay cùng gửi lệnh.
    """
    _instance = None
    _instance_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        self._lock = threading.RLock()
        self._ser = None
        self._port_name = None
        self._connected = False
        self._lcd_hw_ok = False
        self._last_led_bits = "100100100100"
        self._last_lcd_lines = ("He thong GT", "Khoi dong...")

        if not SIMULATION_MODE and _HAS_PYSERIAL:
            self.connect()
        else:
            logger.info("ArduinoSerialBridge: Chế độ SIMULATION MODE")

    # ──────────────────────────────────────────────────────────
    # Tự động dò cổng COM của Arduino Uno R3
    # ──────────────────────────────────────────────────────────
    def _detect_ports(self) -> list[str]:
        """Trả về danh sách các cổng Serial tiềm năng của Arduino Uno."""
        candidates = []
        cfg_port = SERIAL_CONFIG.get('PORT', 'AUTO')
        if cfg_port and cfg_port.upper() != 'AUTO':
            candidates.append(cfg_port)

        # Ưu tiên quét qua pyserial list_ports (nhận diện Arduino Uno / CH340 / ATmega328P / ACM)
        if _HAS_PYSERIAL:
            try:
                ports = list(serial.tools.list_ports.comports())
                for p in ports:
                    desc = f"{p.device} {p.description} {p.manufacturer or ''}".lower()
                    if any(k in desc for k in ['arduino', 'uno', 'ch340', 'cp210', 'ftdi', 'ttyacm', 'ttyusb']):
                        if p.device not in candidates:
                            candidates.append(p.device)
                for p in ports:
                    if ('ttyACM' in p.device or 'ttyUSB' in p.device) and p.device not in candidates:
                        candidates.append(p.device)
            except Exception as e:
                logger.debug(f"Lỗi quét list_ports: {e}")

        # Bổ sung từ danh sách cấu hình và glob hệ thống
        for p in SERIAL_CONFIG.get('CANDIDATE_PORTS', []):
            if p not in candidates:
                candidates.append(p)
        for pattern in ['/dev/ttyACM*', '/dev/ttyUSB*']:
            for p in sorted(glob.glob(pattern)):
                if p not in candidates:
                    candidates.append(p)

        return candidates

    def connect(self) -> bool:
        """Mở kết nối Serial tới Arduino Uno R3."""
        if SIMULATION_MODE or not _HAS_PYSERIAL:
            self._connected = False
            return False

        with self._lock:
            self._close_Unsafe()
            candidates = self._detect_ports()
            if not candidates:
                logger.warning("ArduinoSerialBridge: Không tìm thấy cổng COM (/dev/ttyACM* hoặc /dev/ttyUSB*) – chạy mô phỏng")
                self._connected = False
                return False

            baud = SERIAL_CONFIG.get('BAUDRATE', 115200)
            timeout = SERIAL_CONFIG.get('TIMEOUT', 1.0)
            w_timeout = SERIAL_CONFIG.get('WRITE_TIMEOUT', 1.0)
            boot_delay = SERIAL_CONFIG.get('BOOT_DELAY', 2.0)

            for port in candidates:
                try:
                    logger.info(f"ArduinoSerialBridge: Đang thử kết nối cổng {port} @ {baud} bps...")
                    ser = serial.Serial(
                        port=port,
                        baudrate=baud,
                        timeout=timeout,
                        write_timeout=w_timeout
                    )
                    # Khi mở cổng Serial, Arduino Uno tự động reset qua chân DTR
                    time.sleep(boot_delay)

                    # Đọc thông điệp khởi động nếu có
                    boot_msgs = []
                    while ser.in_waiting > 0:
                        line = ser.readline().decode('utf-8', errors='ignore').strip()
                        if line:
                            boot_msgs.append(line)
                            if 'LCD:1' in line:
                                self._lcd_hw_ok = True
                            elif 'LCD:0' in line:
                                self._lcd_hw_ok = False

                    self._ser = ser
                    self._port_name = port
                    self._connected = True

                    # Gửi lệnh PING kiểm tra phản hồi
                    resp = self._send_command_unsafe("PING")
                    if resp and 'LCD:1' in resp:
                        self._lcd_hw_ok = True
                    elif not boot_msgs and not resp:
                        self._lcd_hw_ok = True

                    logger.info(
                        f"✓ ĐÃ KẾT NỐI ARDUINO UNO R3 tại {port} ({baud} bps) "
                        f"| Boot: {boot_msgs or 'OK'}"
                    )

                    # Đồng bộ lại trạng thái đèn và LCD hiện tại xuống Arduino Uno
                    self._send_command_unsafe(f"LEDS:{self._last_led_bits}")
                    l1, l2 = self._last_lcd_lines
                    self._send_command_unsafe(f"LCD:{l1}|{l2}")
                    return True

                except Exception as e:
                    logger.debug(f"Không mở được cổng {port}: {e}")
                    continue

            logger.warning("ArduinoSerialBridge: Chưa kết nối được Arduino Uno – hệ thống chạy ở chế độ mô phỏng")
            self._connected = False
            return False

    def reconnect(self) -> bool:
        """Thử quét và kết nối lại với Arduino Uno R3."""
        logger.info("ArduinoSerialBridge: Đang quét lại cổng COM để kết nối Arduino Uno...")
        return self.connect()

    def _close_Unsafe(self):
        if self._ser is not None:
            try:
                self._ser.close()
            except Exception:
                pass
            self._ser = None
        self._connected = False
        self._port_name = None

    def close(self):
        """Đóng kết nối Serial an toàn."""
        with self._lock:
            if self._connected and self._ser:
                try:
                    self._send_command_unsafe("LEDS:000000000000")
                    self._send_command_unsafe("LCD:He thong|da tat an toan")
                except Exception:
                    pass
            self._close_Unsafe()
            logger.info("ArduinoSerialBridge: Đã đóng cổng Serial")

    # ──────────────────────────────────────────────────────────
    # Gửi lệnh điều khiển xuống Arduino Uno
    # ──────────────────────────────────────────────────────────
    def _send_command_unsafe(self, cmd: str) -> str:
        """Gửi 1 dòng lệnh ASCII kết thúc bằng \\n (yêu cầu đã giữ lock)."""
        if not self._connected or self._ser is None:
            return ""
        try:
            payload = (cmd.strip() + "\n").encode('ascii', errors='replace')
            self._ser.write(payload)
            self._ser.flush()

            # Đọc phản hồi nhanh nếu Arduino gửi trả ngay
            time.sleep(0.005)
            responses = []
            while self._ser.in_waiting > 0:
                line = self._ser.readline().decode('utf-8', errors='ignore').strip()
                if line:
                    responses.append(line)
                    if 'LCD:1' in line:
                        self._lcd_hw_ok = True
                    elif 'LCD:0' in line:
                        self._lcd_hw_ok = False
            return " ".join(responses)
        except Exception as e:
            logger.error(f"Lỗi truyền Serial ({self._port_name}): {e} – ngắt kết nối tạm thời")
            self._close_Unsafe()
            return ""

    def send_leds(self, bit_string: str) -> bool:
        """
        Gửi trạng thái 12 đèn LED xuống Arduino Uno.
        Định dạng: 'LEDS:100100001100' (12 ký tự '0' hoặc '1' ứng với Pin 2→13)
        """
        with self._lock:
            self._last_led_bits = bit_string
            if not self._connected:
                return False
            self._send_command_unsafe(f"LEDS:{bit_string}")
            return self._connected

    def send_lcd(self, line1: str, line2: str) -> bool:
        """
        Gửi 2 dòng văn bản (tối đa 16 ký tự/dòng) xuống Arduino Uno để in ra LCD 1602 I2C.
        Định dạng: 'LCD:Dong 1          |Dong 2          '
        """
        clean1 = str(line1).replace('|', ' ').replace('\n', ' ').replace('\r', '')[:16].ljust(16)
        clean2 = str(line2).replace('|', ' ').replace('\n', ' ').replace('\r', '')[:16].ljust(16)
        with self._lock:
            self._last_lcd_lines = (clean1, clean2)
            if not self._connected:
                return False
            self._send_command_unsafe(f"LCD:{clean1}|{clean2}")
            return self._connected

    # ──────────────────────────────────────────────────────────
    # Trạng thái kết nối
    # ──────────────────────────────────────────────────────────
    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def port_name(self) -> str:
        return self._port_name or "Chưa kết nối"

    @property
    def is_lcd_ok(self) -> bool:
        return self._connected and self._lcd_hw_ok


# Alias tương thích ngược
ArduinoMegaBridge = ArduinoSerialBridge
