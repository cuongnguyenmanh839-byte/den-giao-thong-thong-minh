"""
gpio_driver.py – Lớp điều khiển 12 đèn LED giao thông thông qua Arduino Uno R3 (Cổng COM / Serial)
Hỗ trợ cả phần cứng thực (Arduino Uno qua /dev/ttyACM0, /dev/ttyUSB0) và chế độ mô phỏng.

Sơ đồ chân trên Arduino Uno R3 (Dãy Digital 2 → 13):
- BẮC  (NORTH): Đỏ = Pin 2,  Vàng = Pin 3,  Xanh = Pin 4
- NAM  (SOUTH): Đỏ = Pin 5,  Vàng = Pin 6,  Xanh = Pin 7
- ĐÔNG (EAST):  Đỏ = Pin 8,  Vàng = Pin 9,  Xanh = Pin 10
- TÂY  (WEST):  Đỏ = Pin 11, Vàng = Pin 12, Xanh = Pin 13
(Chân 0 RX và 1 TX để trống dành cho giao tiếp USB Serial với Raspberry Pi)
Logic: HIGH (5V) = đèn SÁNG, LOW (0V) = đèn TẮT
"""
import os
import sys
import logging
import time

_HW_DIR = os.path.dirname(os.path.abspath(__file__))
_SRC_DIR = os.path.dirname(_HW_DIR)
for _p in (_HW_DIR, _SRC_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from config import GPIO_CONFIG, SERIAL_LED_ORDER, SIMULATION_MODE
from arduino_serial import ArduinoSerialBridge

logger = logging.getLogger(__name__)


class GPIODriver:
    """
    Lớp điều khiển toàn bộ 12 đèn giao thông qua Arduino Uno R3 (USB Serial COM).
    """

    RED    = 'RED'
    YELLOW = 'YELLOW'
    GREEN  = 'GREEN'
    ALL_COLORS = [RED, YELLOW, GREEN]

    def __init__(self):
        self._bridge = ArduinoSerialBridge.get_instance()
        self._pin_state: dict[str, dict[str, bool]] = {}

        for direction in GPIO_CONFIG:
            self._pin_state[direction] = {
                'RED': False, 'YELLOW': False, 'GREEN': False
            }

        if self._bridge.is_connected:
            logger.info(
                f"GPIODriver: Đã kết nối Arduino Uno R3 qua cổng {self._bridge.port_name} "
                f"(Điều khiển 12 LED tại Pin 2→13)"
            )
        else:
            logger.info("GPIODriver: Chưa kết nối Arduino Uno – chạy ở chế độ SIMULATION MODE")

    @property
    def _simulation(self) -> bool:
        """Trả về True nếu đang chạy mô phỏng (chưa cắm cáp USB Arduino Uno)."""
        return SIMULATION_MODE or (not self._bridge.is_connected)

    @property
    def port_name(self) -> str:
        """Tên cổng COM hiện tại (ví dụ: /dev/ttyACM0 hoặc /dev/ttyUSB0)."""
        return self._bridge.port_name

    def reconnect(self) -> bool:
        """Thử kết nối lại với Arduino Uno qua cổng COM."""
        ok = self._bridge.reconnect()
        if ok:
            self._sync_to_arduino()
        return ok

    # ──────────────────────────────────────────────────────────
    # Đồng bộ khung dữ liệu 12-bit xuống Arduino Uno
    # ──────────────────────────────────────────────────────────
    def _build_bit_string(self) -> str:
        """Đóng gói trạng thái 12 đèn thành chuỗi 12 ký tự '0'/'1'."""
        bits = []
        for direction, color in SERIAL_LED_ORDER:
            is_on = self._pin_state.get(direction, {}).get(color, False)
            bits.append('1' if is_on else '0')
        return "".join(bits)

    def _sync_to_arduino(self):
        """Gửi gói tin LEDS:xxxxxxxxxxxx qua cổng COM xuống Arduino Uno."""
        bit_str = self._build_bit_string()
        self._bridge.send_leds(bit_str)

    # ──────────────────────────────────────────────────────────
    # API điều khiển công khai
    # ──────────────────────────────────────────────────────────
    def set_light(self, direction: str, color: str, state: bool, _sync: bool = True):
        """
        Bật/tắt một đèn cụ thể trên Arduino Uno.

        Args:
            direction: 'NORTH', 'SOUTH', 'EAST', 'WEST'
            color:     'RED', 'YELLOW', 'GREEN'
            state:     True = sáng (5V HIGH), False = tắt (0V LOW)
        """
        if direction not in GPIO_CONFIG:
            logger.error(f"Hướng không hợp lệ: {direction}")
            return
        if color not in self.ALL_COLORS:
            logger.error(f"Màu không hợp lệ: {color}")
            return

        pin = GPIO_CONFIG[direction][color]
        self._pin_state[direction][color] = bool(state)

        if _sync:
            self._sync_to_arduino()
            if self._simulation:
                status = "BẬT ●" if state else "TẮT ○"
                logger.debug(f"[SIM-UNO] {direction}.{color}(Pin {pin}) → {status}")

    def set_direction_state(self, direction: str, red: bool, yellow: bool, green: bool, _sync: bool = True):
        """
        Đặt trạng thái cả 3 đèn của một hướng cùng lúc.
        """
        self.set_light(direction, 'RED',    red,    _sync=False)
        self.set_light(direction, 'YELLOW', yellow, _sync=False)
        self.set_light(direction, 'GREEN',  green,  _sync=False)
        if _sync:
            self._sync_to_arduino()

    def all_red(self):
        """Bật đèn ĐỎ tất cả 4 hướng – trạng thái an toàn."""
        for direction in GPIO_CONFIG:
            self.set_direction_state(direction, red=True, yellow=False, green=False, _sync=False)
        self._sync_to_arduino()
        logger.info("[UNO-SERIAL] ALL RED – trạng thái an toàn (Pin 2, 5, 8, 11 = HIGH)")

    def all_off(self):
        """Tắt toàn bộ 12 đèn trên Arduino Uno."""
        for direction in GPIO_CONFIG:
            self.set_direction_state(direction, red=False, yellow=False, green=False, _sync=False)
        self._sync_to_arduino()
        logger.info("[UNO-SERIAL] ALL OFF (Pin 2→13 = LOW)")

    def set_phase(self, active_direction: str):
        """
        Đặt pha: 1 hướng XANH, tất cả 3 hướng còn lại ĐỎ.
        """
        for direction in GPIO_CONFIG:
            if direction == active_direction:
                self.set_direction_state(direction, red=False, yellow=False, green=True, _sync=False)
            else:
                self.set_direction_state(direction, red=True, yellow=False, green=False, _sync=False)
        self._sync_to_arduino()
        logger.info(f"[UNO-SERIAL] Phase XANH: {active_direction}")

    def set_yellow(self, direction: str):
        """
        Chuyển 1 hướng sang VÀNG, giữ nguyên các hướng khác (ĐỎ).
        """
        self.set_direction_state(direction, red=False, yellow=True, green=False, _sync=True)
        logger.info(f"[UNO-SERIAL] Phase VÀNG: {direction}")

    # ──────────────────────────────────────────────────────────
    # Đọc trạng thái
    # ──────────────────────────────────────────────────────────
    def get_state(self) -> dict:
        """Trả về trạng thái hiện tại của tất cả 12 đèn."""
        return {
            direction: dict(colors)
            for direction, colors in self._pin_state.items()
        }

    def get_direction_state(self, direction: str) -> dict:
        """Trả về trạng thái 3 đèn của một hướng."""
        return dict(self._pin_state.get(direction, {}))

    # ──────────────────────────────────────────────────────────
    # Kiểm tra phần cứng
    # ──────────────────────────────────────────────────────────
    def self_test(self, delay: float = 0.5):
        """
        Chạy tự kiểm tra: bật tuần tự từng đèn của từng hướng trên Arduino Uno (Pin 2→13).
        """
        logger.info("GPIODriver: Bắt đầu self-test 12 LED qua Arduino Uno...")
        directions = list(GPIO_CONFIG.keys())

        self.all_off()
        time.sleep(delay)

        for direction in directions:
            for color in self.ALL_COLORS:
                pin = GPIO_CONFIG[direction][color]
                logger.info(f"  Test: {direction} {color} (Uno Pin {pin})")
                self.set_light(direction, color, True)
                time.sleep(delay)
                self.set_light(direction, color, False)
                time.sleep(0.1)

        logger.info("  Test: ALL RED")
        self.all_red()
        time.sleep(delay)
        self.all_off()

        logger.info("GPIODriver: Self-test hoàn thành")

    # ──────────────────────────────────────────────────────────
    # Dọn dẹp
    # ──────────────────────────────────────────────────────────
    def cleanup(self):
        """Tắt đèn và đóng cổng COM an toàn khi kết thúc chương trình."""
        try:
            self.all_off()
            self._bridge.close()
            logger.info("GPIODriver: Đã tắt 12 LED và đóng kết nối Arduino Uno")
        except Exception as e:
            logger.error(f"GPIODriver cleanup lỗi: {e}")

    def __del__(self):
        try:
            self.cleanup()
        except Exception:
            pass


# ════════════════════════════════════════════════════════════
# Chạy trực tiếp để test kết nối Serial với Arduino Uno
# ════════════════════════════════════════════════════════════
if __name__ == '__main__':
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s [%(levelname)s] %(message)s'
    )

    driver = GPIODriver()
    print("=" * 60)
    print("ARDUINO UNO R3 SERIAL LED DRIVER TEST (Pin 2 -> 13)")
    print(f"Cổng kết nối: {driver.port_name} | Simulation: {driver._simulation}")
    print("=" * 60)

    print("\n[1] Test ALL RED (2s)...")
    driver.all_red()
    time.sleep(2)

    print("\n[2] Test từng pha (1s mỗi hướng)...")
    for direction in ['NORTH', 'EAST', 'SOUTH', 'WEST']:
        print(f"    → Xanh: {direction}")
        driver.set_phase(direction)
        time.sleep(1)

        print(f"    → Vàng: {direction}")
        driver.set_yellow(direction)
        time.sleep(0.5)

    print("\n[3] Self-test (0.3s/đèn)...")
    driver.self_test(delay=0.3)

    driver.cleanup()
    print("\n✓ Test Arduino Uno Driver hoàn thành!")
