"""
lcd_display.py – Điều khiển màn hình LCD 16x2 I2C thông qua Arduino Uno R3 (Cổng COM)
Màn hình LCD 1602 I2C được đấu vào chân SDA (A4) và SCL (A5) trên Arduino Uno R3.
Tự động đồng bộ nội dung lên cả LCD phần cứng và LCD ảo trên Web Dashboard.
"""
import time
import logging
from config import LCD_COLS, LCD_ROWS, LCD_ENABLED, SIMULATION_MODE
from arduino_serial import ArduinoSerialBridge

logger = logging.getLogger(__name__)


class LCDDisplay:
    def __init__(self):
        self._bridge = ArduinoSerialBridge.get_instance()
        self._current = ["", ""]

        if not self._sim:
            logger.info(
                f"LCD: Đã kết nối qua Arduino Uno ({self._bridge.port_name}) "
                f"– I2C SDA=A4, SCL=A5"
            )
        else:
            logger.info("LCD: Chế độ mô phỏng (Web Virtual LCD 1602)")

    @property
    def _sim(self) -> bool:
        """Trả về True nếu chưa kết nối Arduino Uno hoặc LCD bị tắt."""
        if SIMULATION_MODE or not LCD_ENABLED:
            return True
        return not self._bridge.is_connected

    def reconnect(self) -> bool:
        """Thử quét cổng COM và kết nối lại với Arduino Uno + LCD I2C."""
        logger.info("LCD: Đang thử kết nối lại Arduino Uno & màn hình LCD qua cổng COM...")
        ok = self._bridge.reconnect()
        if ok:
            l1, l2 = self._current if any(self._current) else ("He thong GT", "San sang!")
            self._bridge.send_lcd(l1, l2)
            return True
        return False

    def show(self, line1: str = "", line2: str = ""):
        """Hiển thị 2 dòng (tối đa 16 ký tự/dòng) lên LCD 1602 trên Arduino Uno."""
        l1 = str(line1)[:LCD_COLS]
        l2 = str(line2)[:LCD_COLS]
        if self._current == [l1, l2]:
            return  # Không gửi lặp lại nếu nội dung không đổi
        self._current = [l1, l2]

        # Gửi lệnh LCD:line1|line2 xuống Arduino Uno qua cổng Serial
        sent = self._bridge.send_lcd(l1, l2)
        if not sent:
            logger.debug(f"[LCD-SIM] │{l1:<16}│ / │{l2:<16}│")

    def show_phase(self, direction: str, color: str, remaining: int):
        """Hiển thị pha đèn hiện tại và số giây đếm ngược."""
        dir_map = {'NORTH': 'Bac', 'SOUTH': 'Nam', 'EAST': 'Dong', 'WEST': 'Tay'}
        col_map = {'GREEN': 'XANH', 'YELLOW': 'VANG', 'RED': 'DO'}
        d = dir_map.get(direction, direction[:4])
        c = col_map.get(color, color)
        self.show(f"{d}: {c}", f"Con lai: {remaining:2d}s")

    def show_mode(self, mode: str):
        """Hiển thị chế độ hoạt động."""
        mode_map = {
            'FIXED':    'Co dinh (30s)',
            'ADAPTIVE': 'Thong minh AI',
            'SAFE':     'An toan (DO)',
            'MANUAL':   'Test thu cong',
        }
        self.show("Che do:", mode_map.get(mode, mode))

    def get_text(self):
        """Trả về 2 dòng nội dung hiện thời của LCD (phục vụ Web Dashboard)."""
        return list(self._current)

    def clear(self):
        self._current = ["", ""]
        self._bridge.send_lcd("", "")

    def cleanup(self):
        try:
            self.show("He thong", "dung lai...")
            time.sleep(0.2)
        except Exception:
            pass
