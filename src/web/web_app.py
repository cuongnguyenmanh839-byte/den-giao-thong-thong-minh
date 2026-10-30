"""
web_app.py – Flask dashboard cho hệ thống đèn giao thông thông minh
"""
import os
import logging
from flask import Flask, render_template, Response, jsonify, request
from flask_cors import CORS
from config import WEB_CONFIG, OperationMode

logger = logging.getLogger(__name__)

_WEB_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(
    __name__,
    template_folder=os.path.join(_WEB_DIR, 'templates'),
    static_folder=os.path.join(_WEB_DIR, 'static')
)
app.secret_key = WEB_CONFIG['SECRET_KEY']
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
CORS(app)

# Tham chiếu tới các module (sẽ được gán bởi main.py)
_controller = None
_vision     = None
_database   = None
_gpio       = None
_lcd        = None

def init(controller, vision, database, gpio, lcd):
    global _controller, _vision, _database, _gpio, _lcd
    _controller = controller
    _vision     = vision
    _database   = database
    _gpio       = gpio
    _lcd        = lcd

# ─── Routes ───────────────────────────────────────────────
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/camera')
def camera_page():
    return render_template('camera.html')

@app.route('/video_feed')
def video_feed():
    """Stream MJPEG từ camera."""
    def generate():
        import time
        while True:
            if _vision:
                frame = _vision.get_frame_jpeg()
                if frame:
                    yield (b'--frame\r\nContent-Type:image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(1.0 / WEB_CONFIG['STREAM_FPS'])
    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/api/status')
def api_status():
    data = {}
    if _controller:
        data = _controller.get_status()
    if 'lcd_text' not in data:
        data['lcd_text'] = _lcd.get_text() if _lcd else ['', '']
    data['lcd_ok'] = (_lcd and not _lcd._sim) if _lcd else False
    data['gpio_sim'] = (_gpio and _gpio._simulation) if _gpio else True
    data['serial_port'] = getattr(_gpio, 'port_name', 'Chưa kết nối') if _gpio else 'Chưa kết nối'
    return jsonify(data)

@app.route('/api/vision')
def api_vision():
    data = {
        'counts': {},
        'density_levels': {},
        'camera_ok': False,
        'fps': 0,
    }
    if _vision:
        data['counts']         = _vision.get_counts()
        data['density_levels'] = _vision.get_density_levels()
        data['camera_ok']      = _vision.is_camera_ok()
        data['fps']            = _vision.get_fps()
        data['source_mode']    = getattr(_vision, '_source_mode', 'CAMERA')
        data['show_zones']     = getattr(_vision, '_show_zones', False)
    return jsonify(data)

@app.route('/api/vision/source', methods=['POST'])
def api_vision_source():
    body = request.get_json(silent=True) or {}
    src = body.get('source', 'CAMERA').upper()
    if _vision and hasattr(_vision, 'set_source_mode'):
        _vision.set_source_mode(src)
        return jsonify({'ok': True, 'source': src})
    return jsonify({'ok': True})

@app.route('/api/vision/set_manual', methods=['POST'])
def api_vision_set_manual():
    body = request.get_json(silent=True) or {}
    counts = body.get('counts', {})
    if _vision and hasattr(_vision, 'set_manual_counts'):
        _vision.set_source_mode('MANUAL')
        _vision.set_manual_counts(counts)
        return jsonify({'ok': True, 'counts': _vision.get_counts()})
    return jsonify({'ok': True})

@app.route('/api/vision/toggle_zones', methods=['POST'])
def api_vision_toggle_zones():
    if _vision and hasattr(_vision, 'toggle_show_zones'):
        show = _vision.toggle_show_zones()
        return jsonify({'ok': True, 'show_zones': show})
    return jsonify({'ok': True})

@app.route('/api/lcd/reconnect', methods=['POST'])
def api_lcd_reconnect():
    """Thử quét cổng COM và kết nối lại với Arduino Mega 2560 + LCD I2C."""
    ok = False
    if _gpio and hasattr(_gpio, 'reconnect'):
        ok = _gpio.reconnect()
    elif _lcd and hasattr(_lcd, 'reconnect'):
        ok = _lcd.reconnect()
    port = getattr(_gpio, 'port_name', 'Chưa kết nối') if _gpio else 'Chưa kết nối'
    return jsonify({'ok': ok, 'lcd_ok': ok, 'serial_port': port})

@app.route('/api/set_mode', methods=['POST'])
def api_set_mode():
    body = request.get_json(silent=True) or {}
    mode = body.get('mode', '').upper()
    valid = [OperationMode.FIXED, OperationMode.ADAPTIVE, OperationMode.SAFE, OperationMode.MANUAL]
    if mode not in valid:
        return jsonify({'error': f'Mode không hợp lệ: {mode}'}), 400
    if _controller:
        _controller.set_mode(mode)
    return jsonify({'ok': True, 'mode': mode})

@app.route('/api/manual/light', methods=['POST'])
def api_manual_light():
    """Bật/tắt 1 đèn LED cụ thể để kiểm tra đứt dây."""
    body = request.get_json(silent=True) or {}
    direction = body.get('direction', '').upper()
    color = body.get('color', '').upper()
    state = bool(body.get('state', True))
    if _controller and _controller.get_status().get('mode') != OperationMode.MANUAL:
        _controller.set_mode(OperationMode.MANUAL)
    if _gpio and direction in ['NORTH', 'SOUTH', 'EAST', 'WEST'] and color in ['RED', 'YELLOW', 'GREEN']:
        _gpio.set_light(direction, color, state)
        return jsonify({'ok': True, 'direction': direction, 'color': color, 'state': state, 'gpio_state': _gpio.get_state()})
    return jsonify({'error': 'Tham số không hợp lệ'}), 400

@app.route('/api/manual/all', methods=['POST'])
def api_manual_all():
    """Bật tất cả 12 đèn hoặc tắt hết."""
    body = request.get_json(silent=True) or {}
    turn_on = bool(body.get('turn_on', True))
    if _controller:
        _controller.set_mode(OperationMode.MANUAL)
    if _gpio:
        if turn_on:
            for d in ['NORTH', 'SOUTH', 'EAST', 'WEST']:
                _gpio.set_direction_state(d, red=True, yellow=True, green=True)
        else:
            _gpio.all_off()
        return jsonify({'ok': True, 'gpio_state': _gpio.get_state()})
    return jsonify({'ok': True})

@app.route('/api/manual/self_test', methods=['POST'])
def api_manual_self_test():
    """Chạy kiểm tra lần lượt từng đèn một trong 12 đèn."""
    import threading
    if _controller:
        _controller.set_mode(OperationMode.MANUAL)
    def run_seq():
        if _gpio:
            _gpio.self_test(delay=0.4)
    threading.Thread(target=run_seq, daemon=True).start()
    return jsonify({'ok': True, 'message': 'Đang kiểm tra lần lượt 12 đèn...'})

@app.route('/api/history/vehicles')
def api_history_vehicles():
    minutes = request.args.get('minutes', 60, type=int)
    data = _database.get_vehicle_history(minutes) if _database else []
    return jsonify(data)

@app.route('/api/history/phases')
def api_history_phases():
    data = _database.get_phase_history(50) if _database else []
    return jsonify(data)

@app.route('/api/history/events')
def api_history_events():
    data = _database.get_events(30) if _database else []
    return jsonify(data)

def run():
    logger.info(f"Web dashboard: http://0.0.0.0:{WEB_CONFIG['PORT']}")
    app.run(host=WEB_CONFIG['HOST'], port=WEB_CONFIG['PORT'],
            debug=False, threaded=True, use_reloader=False)
