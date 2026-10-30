#!/bin/bash
# ==============================================================================
# Script dừng toàn bộ hệ thống đèn giao thông và tắt an toàn các đèn LED
# Cách dùng: ./stop.sh
# ==============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Đang dừng hệ thống đèn giao thông..."
pkill -f "python3 main.py" 2>/dev/null || true
fuser -k 5000/tcp 2>/dev/null || true

# Tắt toàn bộ 12 chân LED bằng Python nhanh
python3 -c "
try:
    from gpiozero import LED
    pins = [18, 25, 14, 17, 27, 22, 10, 9, 11, 5, 6, 13]
    for p in pins:
        try:
            led = LED(p)
            led.off()
            led.close()
        except:
            pass
except:
    pass
" 2>/dev/null || true

echo "✓ Hệ thống đã dừng hoàn toàn và tắt sạch toàn bộ đèn LED!"
