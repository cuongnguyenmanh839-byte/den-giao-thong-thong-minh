#!/bin/bash
# ==============================================================================
# HỆ THỐNG ĐÈN GIAO THÔNG THÔNG MINH 4 HƯỚNG – RASPBERRY PI 5
# Script 1 lệnh duy nhất: Tự động chuẩn bị môi trường và khởi chạy toàn bộ dự án
# Cách dùng: ./run.sh
# ==============================================================================

# Thoát nếu gặp lỗi không mong muốn
set -e

# Màu sắc hiển thị terminal
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Chuyển vào đúng thư mục dự án
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo -e "${CYAN}${BOLD}"
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   HỆ THỐNG ĐÈN GIAO THÔNG THÔNG MINH - PI 5 + ARDUINO UNO    ║"
echo "║          Khởi chạy toàn bộ hệ thống bằng 1 lệnh              ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 1. Dọn dẹp tiến trình cũ để tránh xung đột cổng 5000
echo -e "${BLUE}[1/4] Dọn dẹp các tiến trình cũ...${NC}"
pkill -f "python3 main.py" 2>/dev/null || true
fuser -k 5000/tcp 2>/dev/null || true
sleep 1

# 2. Kích hoạt môi trường Python
echo -e "${BLUE}[2/4] Kiểm tra môi trường Python...${NC}"
if [ -d "venv" ]; then
    echo -e "      Kích hoạt virtual environment: ${GREEN}venv${NC}"
    source venv/bin/activate
elif [ -d "/home/pi/Desktop/giaothong/venv" ]; then
    echo -e "      Kích hoạt virtual environment: ${GREEN}/home/pi/Desktop/giaothong/venv${NC}"
    source /home/pi/Desktop/giaothong/venv/bin/activate
else
    echo -e "      ${YELLOW}Dùng Python hệ thống (system-wide)${NC}"
fi

# 3. Lấy địa chỉ IP mạng nội bộ
echo -e "${BLUE}[3/4] Xác định địa chỉ mạng...${NC}"
PI_IP=$(hostname -I | awk '{print $1}')
if [ -z "$PI_IP" ]; then
    PI_IP="localhost"
fi

# 4. Khởi chạy hệ thống chính
echo -e "${GREEN}${BOLD}[4/4] Khởi động hệ thống giao thông thành công!${NC}"
echo "--------------------------------------------------------------"
echo -e "🚦 ${BOLD}12 Đèn LED & LCD 1602:${NC}       Điều khiển qua Arduino Uno R3 (COM/USB)"
echo -e "🌐 ${BOLD}Giao diện Dashboard Web:${NC}     ${CYAN}${BOLD}http://${PI_IP}:5000${NC}"
echo -e "💻 ${BOLD}Truy cập tại chỗ trên Pi:${NC}    ${CYAN}${BOLD}http://localhost:5000${NC}"
echo -e "📷 ${BOLD}Trang Camera riêng biệt:${NC}     ${CYAN}${BOLD}http://${PI_IP}:5000/camera${NC}"
echo "--------------------------------------------------------------"
echo -e "${YELLOW}Nhấn [Ctrl + C] bất cứ lúc nào để tắt an toàn và tắt toàn bộ đèn LED.${NC}"
echo "--------------------------------------------------------------"

# Chạy Python main.py
exec python3 main.py
