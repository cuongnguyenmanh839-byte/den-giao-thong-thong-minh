"""
vision.py – Thu hình từ camera USB và nhận diện phương tiện bằng YOLOv8
Chạy trên luồng riêng, cập nhật kết quả cho TrafficController.
"""
import cv2, time, logging, threading
import numpy as np
from collections import deque
from config import (CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, CAMERA_FPS,
                    CAMERA_WARMUP_SECONDS, DETECTION_CONFIG, DETECTION_ZONES,
                    DETECTION_SMOOTHING, PHASE_ORDER, SIMULATION_MODE)

logger = logging.getLogger(__name__)

class VisionModule:
    def __init__(self, controller=None, database=None):
        self._ctrl     = controller
        self._db       = database
        self._lock     = threading.Lock()
        self._running  = False
        self._thread   = None
        self._cap      = None
        self._model    = None
        self._ok       = False

        # Chế độ nguồn dữ liệu: 'CAMERA' hoặc 'MANUAL' (giả lập thủ công để test thuật toán)
        self._source_mode = 'CAMERA'
        self._manual_counts = {d: 0 for d in PHASE_ORDER}
        self._show_zones = False  # Mặc định tắt các khung vẽ che hình ảnh

        # Bộ lọc chuyển động thực tế (Background Subtractor MOG2)
        self._bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=300, varThreshold=50, detectShadows=False)

        # Kết quả nhận diện
        self._counts        = {d: 0 for d in PHASE_ORDER}
        self._density_level = {d: 'LOW' for d in PHASE_ORDER}
        self._frame_annotated = None
        self._fps_actual    = 0
        self._last_frame_time = 0
        # Smoothing buffer
        self._count_history = {d: deque(maxlen=DETECTION_SMOOTHING['WINDOW_SIZE'])
                               for d in PHASE_ORDER}
        self._last_update   = 0

        self._init_camera()
        if not SIMULATION_MODE:
            self._init_model()

    # ──────────────────────────────────────────────────────────
    # Khởi tạo
    # ──────────────────────────────────────────────────────────
    def _init_camera(self):
        try:
            self._cap = cv2.VideoCapture(CAMERA_INDEX)
            self._cap.set(cv2.CAP_PROP_FRAME_WIDTH,  CAMERA_WIDTH)
            self._cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self._cap.set(cv2.CAP_PROP_FPS, CAMERA_FPS)
            self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            time.sleep(CAMERA_WARMUP_SECONDS)
            if self._cap.isOpened():
                ret, _ = self._cap.read()
                if ret:
                    self._ok = True
                    logger.info(f"Camera: khởi tạo OK (/dev/video{CAMERA_INDEX})")
                    return
            logger.error("Camera: không đọc được frame")
        except Exception as e:
            logger.error(f"Camera: lỗi {e}")
        self._ok = False

    def _init_model(self):
        try:
            from ultralytics import YOLO
            self._model = YOLO(DETECTION_CONFIG['MODEL_PATH'])
            logger.info("YOLO model: tải OK")
        except Exception as e:
            logger.warning(f"YOLO: không tải được ({e}) – dùng background subtraction")
            self._model = None

    # ──────────────────────────────────────────────────────────
    # Vòng lặp xử lý
    # ──────────────────────────────────────────────────────────
    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, name="Vision", daemon=True)
        self._thread.start()
        logger.info("VisionModule: đã khởi động")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        if self._cap:
            self._cap.release()
        logger.info("VisionModule: đã dừng")

    def _loop(self):
        interval = DETECTION_SMOOTHING['UPDATE_INTERVAL']
        while self._running:
            t0 = time.time()
            if not self._ok:
                time.sleep(2)
                self._init_camera()
                continue

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Camera: mất frame")
                time.sleep(0.1)
                continue

            # Nhận diện
            if self._model and not SIMULATION_MODE:
                counts, annotated = self._detect_yolo(frame)
            else:
                counts, annotated = self._detect_simple(frame)

            # Smoothing
            for d in PHASE_ORDER:
                self._count_history[d].append(counts[d])

            # Chỉ cập nhật controller theo interval
            now = time.time()
            if now - self._last_update >= interval:
                smooth = {d: int(round(sum(self._count_history[d]) /
                                       max(len(self._count_history[d]), 1)))
                          for d in PHASE_ORDER}
                with self._lock:
                    self._counts = smooth
                    for d in PHASE_ORDER:
                        c = smooth[d]
                        self._density_level[d] = ('HIGH' if c > 5 else
                                                   'MEDIUM' if c > 2 else 'LOW')
                if self._ctrl:
                    self._ctrl.update_vehicle_counts(smooth)
                if self._db:
                    self._db.log_vehicles(smooth)
                self._last_update = now

            # Lưu frame có annotation
            with self._lock:
                self._frame_annotated = annotated.copy()

            # FPS
            elapsed = time.time() - t0
            self._fps_actual = round(1.0 / max(elapsed, 0.001))
            sleep_t = max(0, 0.033 - elapsed)  # ~30fps max
            time.sleep(sleep_t)

    # ──────────────────────────────────────────────────────────
    # Nhận diện bằng YOLO
    # ──────────────────────────────────────────────────────────
    def _detect_yolo(self, frame):
        cfg = DETECTION_CONFIG
        results = self._model(frame, conf=cfg['CONFIDENCE_THRESHOLD'],
                              iou=cfg['NMS_IOU_THRESHOLD'],
                              imgsz=cfg['INFERENCE_SIZE'],
                              classes=cfg['VEHICLE_CLASSES'],
                              verbose=False)
        annotated = frame.copy()
        counts = {d: 0 for d in PHASE_ORDER}
        h, w = frame.shape[:2]

        # Vẽ vùng nhận diện
        self._draw_zones(annotated, w, h)

        for r in results:
            for box in r.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                conf = float(box.conf[0])
                cls_id = int(box.cls[0])
                label = cfg['VEHICLE_CLASS_NAMES'][cfg['VEHICLE_CLASSES'].index(cls_id)] if cls_id in cfg['VEHICLE_CLASSES'] else 'vehicle'

                # Xác định hướng
                direction = self._point_to_zone(cx / w, cy / h)
                if direction:
                    counts[direction] += 1
                    color = {'NORTH':(0,255,0),'SOUTH':(0,200,255),
                             'EAST':(255,100,0),'WEST':(100,0,255)}.get(direction,(255,255,255))
                    cv2.rectangle(annotated, (x1,y1),(x2,y2), color, 2)
                    cv2.putText(annotated, f"{label} {conf:.2f}", (x1, y1-5),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1)

        self._draw_counts(annotated, counts, w, h)
        return counts, annotated

    # ──────────────────────────────────────────────────────────
    # Nhận diện đơn giản (Background Subtraction – không cần YOLO)
    # ──────────────────────────────────────────────────────────
    # ──────────────────────────────────────────────────────────
    # Nhận diện: Chuyển động MOG2 hoặc Giả lập thủ công
    # ──────────────────────────────────────────────────────────
    def _detect_simple(self, frame):
        annotated = frame.copy()
        h, w = frame.shape[:2]
        counts = {d: 0 for d in PHASE_ORDER}

        # Nếu đang ở chế độ giả lập thủ công (manual simulation)
        if self._source_mode == 'MANUAL':
            counts = dict(self._manual_counts)
            cv2.putText(annotated, "CHE DO GIA LAP THU CONG", (10, 25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
            if self._show_zones:
                self._draw_zones(annotated, w, h)
            self._draw_counts(annotated, counts, w, h)
            return counts, annotated

        # Chế độ camera thực tế: Lọc chuyển động MOG2
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        fg = self._bg_subtractor.apply(blur)

        # Khử nhiễu
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel)
        fg = cv2.dilate(fg, kernel, iterations=2)

        contours, _ = cv2.findContours(fg, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for c in contours:
            area = cv2.contourArea(c)
            # Chỉ nhận diện vật thể có kích thước đáng kể (xe mô hình, tay di chuyển)
            if area > 2500:
                x, y, wb, hb = cv2.boundingRect(c)
                cx = x + wb // 2
                cy = y + hb // 2
                direction = self._point_to_zone(cx / w, cy / h)
                if direction:
                    counts[direction] += 1
                    cv2.rectangle(annotated, (x, y), (x + wb, y + hb), (0, 255, 0), 2)
                    cv2.putText(annotated, f"Xe ({direction})", (x, y - 6),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

        if self._show_zones:
            self._draw_zones(annotated, w, h)

        self._draw_counts(annotated, counts, w, h)
        return counts, annotated

    # ──────────────────────────────────────────────────────────
    # Vẽ hỗ trợ
    # ──────────────────────────────────────────────────────────
    def _draw_zones(self, frame, w, h):
        colors = {'NORTH':(0,255,0),'SOUTH':(0,200,255),'EAST':(255,100,0),'WEST':(100,0,255)}
        for d, zone in DETECTION_ZONES.items():
            x1 = int(zone[0]*w); y1 = int(zone[1]*h)
            x2 = int(zone[2]*w); y2 = int(zone[3]*h)
            cv2.rectangle(frame, (x1, y1), (x2, y2), colors[d], 1)
            cv2.putText(frame, d, (x1 + 4, y1 + 16),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, colors[d], 1)

    def _draw_counts(self, frame, counts, w, h):
        y = 20 if self._source_mode != 'MANUAL' else 50
        for d, cnt in counts.items():
            lv = 'CAO' if cnt > 5 else 'TB' if cnt > 2 else 'THAP'
            cv2.putText(frame, f"{d[:1]}: {cnt}xe ({lv})", (10, y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
            y += 18
        cv2.putText(frame, f"FPS:{self._fps_actual}", (w - 75, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 0), 1)

    def _point_to_zone(self, rx, ry) -> str:
        """Xác định điểm (rx,ry) thuộc vùng nào (tọa độ tương đối 0-1)."""
        for d, zone in DETECTION_ZONES.items():
            if zone[0] <= rx <= zone[2] and zone[1] <= ry <= zone[3]:
                return d
        return None

    # ──────────────────────────────────────────────────────────
    # API điều khiển nguồn dữ liệu và giả lập
    # ──────────────────────────────────────────────────────────
    def set_source_mode(self, mode: str):
        with self._lock:
            self._source_mode = mode.upper()
            logger.info(f"VisionModule: Đổi nguồn dữ liệu sang {self._source_mode}")

    def set_manual_counts(self, counts: dict):
        with self._lock:
            for d in PHASE_ORDER:
                if d in counts:
                    self._manual_counts[d] = max(0, int(counts[d]))
            if self._source_mode == 'MANUAL':
                self._counts = dict(self._manual_counts)
                for d in PHASE_ORDER:
                    c = self._counts[d]
                    self._density_level[d] = ('HIGH' if c > 5 else 'MEDIUM' if c > 2 else 'LOW')
                if self._ctrl:
                    self._ctrl.update_vehicle_counts(self._counts)

    def toggle_show_zones(self) -> bool:
        with self._lock:
            self._show_zones = not self._show_zones
            return self._show_zones

    # ──────────────────────────────────────────────────────────
    # API đọc kết quả (thread-safe)
    # ──────────────────────────────────────────────────────────
    def get_counts(self) -> dict:
        with self._lock:
            return dict(self._counts)

    def get_density_levels(self) -> dict:
        with self._lock:
            return dict(self._density_level)

    def get_frame_jpeg(self) -> bytes:
        """Trả về frame JPEG để stream lên web."""
        with self._lock:
            frame = self._frame_annotated
        if frame is None:
            return b''
        ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
        return buf.tobytes() if ret else b''

    def is_camera_ok(self) -> bool:
        return self._ok

    def get_fps(self) -> int:
        return self._fps_actual
