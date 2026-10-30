"""
traffic_controller.py – Máy trạng thái điều khiển đèn giao thông 4 hướng
Chế độ 1: Cố định (FIXED)  |  Chế độ 2: Thích nghi (ADAPTIVE)
"""
import time
import logging
import threading
from config import (PHASE_ORDER, FIXED_MODE_TIMING, ADAPTIVE_MODE_TIMING,
                    PRIORITY_WEIGHTS, DENSITY_THRESHOLDS, GREEN_TIME_BY_DENSITY,
                    TrafficState, OperationMode)

logger = logging.getLogger(__name__)

class TrafficController:
    """
    Máy trạng thái điều khiển đèn giao thông.
    Chạy trên luồng riêng – không bao giờ block luồng nhận diện xe.
    """

    def __init__(self, gpio_driver, lcd_display, database=None):
        self._gpio   = gpio_driver
        self._lcd    = lcd_display
        self._db     = database
        self._lock   = threading.Lock()
        self._running = False
        self._thread  = None

        # Trạng thái hiện tại
        self._mode           = OperationMode.FIXED
        self._state          = TrafficState.ALL_RED
        self._phase_idx      = 0               # index trong PHASE_ORDER
        self._active_dir     = None            # hướng đang được xanh
        self._active_color   = 'RED'
        self._phase_start    = time.time()
        self._phase_duration = 0
        self._time_remaining = 0

        # Dữ liệu mật độ từ vision (cập nhật bởi luồng khác)
        self._vehicle_counts  = {d: 0 for d in PHASE_ORDER}
        self._wait_times      = {d: 0.0 for d in PHASE_ORDER}  # giây đã chờ

        # Thống kê
        self._phase_count    = 0
        self._last_phase_end = {d: time.time() for d in PHASE_ORDER}

    # ──────────────────────────────────────────────────────────
    # Điều khiển vòng lặp chính
    # ──────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._gpio.all_red()
        self._lcd.show("He thong", "khoi dong...")
        time.sleep(1)
        self._thread = threading.Thread(target=self._loop, name="TrafficController", daemon=True)
        self._thread.start()
        logger.info("TrafficController: đã khởi động")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        self._gpio.all_red()
        logger.info("TrafficController: đã dừng")

    def _loop(self):
        """Vòng lặp chính – chạy máy trạng thái."""
        # Bắt đầu pha đầu tiên
        self._start_next_phase()

        while self._running:
            # Nếu đang ở chế độ thủ công (test phần cứng), tạm dừng máy trạng thái
            if self._mode == OperationMode.MANUAL:
                time.sleep(0.3)
                continue

            elapsed = time.time() - self._phase_start
            remaining = max(0, int(self._phase_duration - elapsed))

            with self._lock:
                self._time_remaining = remaining

            # Cập nhật LCD mỗi giây
            if self._active_dir:
                self._lcd.show_phase(self._active_dir, self._active_color, remaining)

            # Kiểm tra hết pha
            if elapsed >= self._phase_duration:
                self._advance_phase()

            time.sleep(0.5)

    def _advance_phase(self):
        """Chuyển sang trạng thái tiếp theo trong chuỗi GREEN→YELLOW→SAFETY→GREEN..."""
        if self._state == TrafficState.GREEN_PHASE:
            # Green → Yellow
            self._state = TrafficState.YELLOW_PHASE
            if self._active_dir:
                self._gpio.set_yellow(self._active_dir)
                self._active_color = 'YELLOW'
            timing = (FIXED_MODE_TIMING if self._mode == OperationMode.FIXED
                      else ADAPTIVE_MODE_TIMING)
            self._phase_start    = time.time()
            self._phase_duration = timing['YELLOW_TIME']

        elif self._state == TrafficState.YELLOW_PHASE:
            # Yellow → Safety gap (all red)
            if self._active_dir and self._db:
                dur = time.time() - self._last_phase_end[self._active_dir]
                self._db.log_phase(self._active_dir, 'GREEN', dur, self._mode)
            self._state = TrafficState.SAFETY_GAP
            self._gpio.all_red()
            self._active_color = 'RED'
            timing = (FIXED_MODE_TIMING if self._mode == OperationMode.FIXED
                      else ADAPTIVE_MODE_TIMING)
            self._phase_start    = time.time()
            self._phase_duration = timing['SAFETY_GAP']

        elif self._state in (TrafficState.SAFETY_GAP, TrafficState.ALL_RED):
            # Safety gap → chọn pha tiếp
            self._start_next_phase()

    def _start_next_phase(self):
        """Chọn hướng tiếp theo và bắt đầu pha xanh."""
        # Cập nhật thời gian chờ
        now = time.time()
        for d in PHASE_ORDER:
            if d != self._active_dir:
                self._wait_times[d] += 0.5  # approximate

        # Chọn hướng
        if self._mode == OperationMode.FIXED:
            self._phase_idx = (self._phase_idx + 1) % len(PHASE_ORDER)
            next_dir = PHASE_ORDER[self._phase_idx]
            green_time = FIXED_MODE_TIMING['GREEN_TIME']
        else:
            next_dir, green_time = self._select_adaptive_phase()

        self._active_dir   = next_dir
        self._active_color = 'GREEN'
        self._state        = TrafficState.GREEN_PHASE
        self._phase_start  = time.time()
        self._phase_duration = green_time
        self._last_phase_end[next_dir] = time.time()
        self._wait_times[next_dir] = 0  # reset thời gian chờ
        self._phase_count += 1

        self._gpio.set_phase(next_dir)
        logger.info(f"Pha {self._phase_count}: {next_dir} XANH {green_time:.0f}s [mode={self._mode}]")

    def _select_adaptive_phase(self) -> tuple:
        """Thuật toán chọn pha thông minh dựa trên mật độ và thời gian chờ."""
        timing = ADAPTIVE_MODE_TIMING
        best_dir   = None
        best_score = -1

        with self._lock:
            counts = dict(self._vehicle_counts)
            waits  = dict(self._wait_times)

        max_count = max(counts.values()) if any(counts.values()) else 1
        max_wait  = max(waits.values()) if any(waits.values()) else 1

        for d in PHASE_ORDER:
            # Tránh hướng vừa xanh xong (trừ khi chỉ còn 1 hướng)
            if d == self._active_dir and len(PHASE_ORDER) > 1:
                continue

            count_score = counts[d] / max(max_count, 1)
            wait_score  = waits[d]  / max(max_wait, 1)
            score = (PRIORITY_WEIGHTS['VEHICLE_COUNT'] * count_score +
                     PRIORITY_WEIGHTS['WAIT_TIME']     * wait_score)

            # Starvation protection: hướng chờ quá lâu được ưu tiên tuyệt đối
            if waits[d] >= timing['MAX_WAIT']:
                score = 999
                logger.warning(f"Starvation protection: {d} đã chờ {waits[d]:.0f}s")

            if score > best_score:
                best_score = score
                best_dir = d

        if best_dir is None:
            best_dir = PHASE_ORDER[(self._phase_idx + 1) % len(PHASE_ORDER)]

        # Tính thời gian xanh theo mật độ
        cnt = counts.get(best_dir, 0)
        if cnt <= DENSITY_THRESHOLDS['LOW']:
            green_time = GREEN_TIME_BY_DENSITY['LOW']
        elif cnt <= DENSITY_THRESHOLDS['MEDIUM']:
            green_time = GREEN_TIME_BY_DENSITY['MEDIUM']
        else:
            green_time = GREEN_TIME_BY_DENSITY['HIGH']

        green_time = max(timing['GREEN_MIN'], min(timing['GREEN_MAX'], green_time))
        self._phase_idx = PHASE_ORDER.index(best_dir)
        return best_dir, green_time

    # ──────────────────────────────────────────────────────────
    # API cập nhật từ bên ngoài (thread-safe)
    # ──────────────────────────────────────────────────────────
    def update_vehicle_counts(self, counts: dict):
        """Gọi từ luồng vision để cập nhật số xe mỗi hướng."""
        with self._lock:
            for d in PHASE_ORDER:
                self._vehicle_counts[d] = counts.get(d, 0)

    def set_mode(self, mode: str):
        """Chuyển chế độ hoạt động."""
        if mode not in [OperationMode.FIXED, OperationMode.ADAPTIVE, OperationMode.SAFE, OperationMode.MANUAL]:
            logger.error(f"Chế độ không hợp lệ: {mode}")
            return
        old = self._mode
        self._mode = mode
        if mode != OperationMode.MANUAL:
            if old == OperationMode.MANUAL:
                self._start_next_phase()
            else:
                self._phase_start = time.time()
        self._lcd.show_mode(mode)
        logger.info(f"Chuyển chế độ: {old} → {mode}")
        if self._db:
            self._db.log_event('INFO', f'Mode change: {old} → {mode}')

    def enter_safe_mode(self, reason: str = ""):
        """Chuyển về chế độ an toàn (đèn cố định)."""
        logger.warning(f"Safe mode: {reason}")
        self._mode = OperationMode.SAFE
        if self._db:
            self._db.log_event('WARNING', f'Safe mode: {reason}')

    # ──────────────────────────────────────────────────────────
    # Đọc trạng thái (thread-safe)
    # ──────────────────────────────────────────────────────────
    def get_status(self) -> dict:
        with self._lock:
            return {
                'mode':          self._mode,
                'state':         self._state,
                'active_dir':    self._active_dir,
                'active_color':  self._active_color,
                'time_remaining': self._time_remaining,
                'phase_count':   self._phase_count,
                'vehicle_counts': dict(self._vehicle_counts),
                'wait_times':    {d: round(w, 1) for d, w in self._wait_times.items()},
                'gpio_state':    self._gpio.get_state(),
                'lcd_text':      self._lcd.get_text() if self._lcd else ['', ''],
            }
