/*
 * ============================================================================
 * DỰ ÁN: HỆ THỐNG ĐÈN GIAO THÔNG THÔNG MINH 4 HƯỚNG
 * VI ĐIỀU KHIỂN TRUNG GIAN: ARDUINO UNO R3 (GIAO TIẾP USB SERIAL VỚI PI 5)
 * ============================================================================
 *
 * 1. SƠ ĐỒ ĐẤU DÂY 12 ĐÈN LED (DÃY CHÂN DIGITAL 2 -> 13 TRÊN ARDUINO UNO R3):
 *    * Lưu ý: Chân 0 (RX) và 1 (TX) để trống dành cho truyền thông USB Serial với Pi.
 *    - HƯỚNG BẮC  (NORTH): ĐỎ = Pin 2  | VÀNG = Pin 3  | XANH = Pin 4
 *    - HƯỚNG NAM  (SOUTH): ĐỎ = Pin 5  | VÀNG = Pin 6  | XANH = Pin 7
 *    - HƯỚNG ĐÔNG (EAST):  ĐỎ = Pin 8  | VÀNG = Pin 9  | XANH = Pin 10
 *    - HƯỚNG TÂY  (WEST):  ĐỎ = Pin 11 | VÀNG = Pin 12 | XANH = Pin 13
 *    (Mỗi chân nối qua điện trở 220Ω - 330Ω vào cực Dương Anode LED, Cathode nối GND)
 *
 * 2. SƠ ĐỒ ĐẤU DÂY MÀN HÌNH LCD 1602 I2C (PCF8574) TRÊN ARDUINO UNO R3:
 *    - VCC  -> Chân 5V  trên Arduino Uno
 *    - GND  -> Chân GND trên Arduino Uno
 *    - SDA  -> Chân A4 (hoặc chân SDA cạnh AREF) trên Arduino Uno
 *    - SCL  -> Chân A5 (hoặc chân SCL cạnh AREF) trên Arduino Uno
 *
 * 3. TẬP LỆNH GIAO TIẾP UART/SERIAL (BAUDRATE: 115200 bps, KẾT THÚC BẰNG '\n'):
 *    - "LEDS:100100001100" : Điều khiển đồng loạt 12 chân LED (Pin 2 -> Pin 13)
 *    - "LCD:Dong 1|Dong 2" : Hiển thị 2 dòng văn bản lên màn hình LCD 1602 I2C
 *    - "ALL_RED"           : Bật 4 đèn Đỏ an toàn, tắt các đèn còn lại
 *    - "ALL_OFF"           : Tắt toàn bộ 12 đèn LED
 *    - "PING"              : Kiểm tra kết nối và trạng thái màn hình I2C
 *
 * ƯU ĐIỂM: Code tích hợp sẵn trình điều khiển I2C PCF8574 bằng thư viện chuẩn <Wire.h>,
 * KHÔNG CẦN cài thêm bất kỳ thư viện ngoài nào trong Arduino IDE!
 * ============================================================================
 */

#include <Arduino.h>
#include <Wire.h>

// ─── Danh sách 12 chân LED trên Arduino Uno (Pin 2 -> Pin 13) ────────────────
const uint8_t LED_PINS[12] = {
  2,  3,  4,   // NORTH: RED (2),  YELLOW (3),  GREEN (4)
  5,  6,  7,   // SOUTH: RED (5),  YELLOW (6),  GREEN (7)
  8,  9,  10,  // EAST:  RED (8),  YELLOW (9),  GREEN (10)
  11, 12, 13   // WEST:  RED (11), YELLOW (12), GREEN (13)
};

// ─── Cấu hình trình điều khiển LCD 1602 I2C (PCF8574 + HD44780) ────────────
#define LCD_BACKLIGHT 0x08
#define LCD_ENABLE    0x04
#define LCD_CHR       0x01
#define LCD_CMD       0x00
#define LCD_LINE_1    0x80
#define LCD_LINE_2    0xC0

uint8_t lcdAddr = 0x27;
bool lcdFound = false;
String serialBuffer = "";

// ─── Các hàm giao tiếp trực tiếp I2C PCF8574 cho LCD 1602 ──────────────────
void lcdWriteI2C(uint8_t data) {
  if (!lcdFound) return;
  Wire.beginTransmission(lcdAddr);
  Wire.write(data | LCD_BACKLIGHT);
  Wire.endTransmission();
}

void lcdPulseEnable(uint8_t data) {
  lcdWriteI2C(data | LCD_ENABLE);
  delayMicroseconds(500);
  lcdWriteI2C(data & ~LCD_ENABLE);
  delayMicroseconds(100);
}

void lcdSendByte(uint8_t bits, uint8_t mode) {
  if (!lcdFound) return;
  uint8_t highNibble = mode | (bits & 0xF0) | LCD_BACKLIGHT;
  uint8_t lowNibble  = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT;
  lcdWriteI2C(highNibble);
  lcdPulseEnable(highNibble);
  lcdWriteI2C(lowNibble);
  lcdPulseEnable(lowNibble);
}

bool scanAndInitLCD() {
  const uint8_t candidateAddrs[] = {0x27, 0x3F, 0x20, 0x26, 0x38};
  lcdFound = false;

  for (uint8_t i = 0; i < sizeof(candidateAddrs); i++) {
    Wire.beginTransmission(candidateAddrs[i]);
    if (Wire.endTransmission() == 0) {
      lcdAddr = candidateAddrs[i];
      lcdFound = true;
      break;
    }
  }

  if (!lcdFound) return false;

  delay(50);
  lcdSendByte(0x33, LCD_CMD); // Khởi tạo 4-bit mode
  delay(5);
  lcdSendByte(0x32, LCD_CMD); // Chuyển sang 4-bit mode
  delay(5);
  lcdSendByte(0x28, LCD_CMD); // 2 dòng, font 5x8
  delay(5);
  lcdSendByte(0x0C, LCD_CMD); // Bật màn hình, tắt con trỏ
  delay(5);
  lcdSendByte(0x06, LCD_CMD); // Tự động dịch con trỏ sang phải
  delay(5);
  lcdSendByte(0x01, LCD_CMD); // Xóa màn hình
  delay(5);
  return true;
}

void lcdPrintLine(uint8_t lineCmd, const String &text) {
  if (!lcdFound) return;
  lcdSendByte(lineCmd, LCD_CMD);
  for (uint8_t i = 0; i < 16; i++) {
    char c = (i < text.length()) ? text.charAt(i) : ' ';
    lcdSendByte((uint8_t)c, LCD_CHR);
  }
}

void lcdShow(const String &line1, const String &line2) {
  if (!lcdFound) {
    // Thử quét lại nếu trước đó chưa cắm dây I2C
    if (!scanAndInitLCD()) return;
  }
  lcdPrintLine(LCD_LINE_1, line1);
  lcdPrintLine(LCD_LINE_2, line2);
}

// ─── Các hàm điều khiển 12 đèn LED ─────────────────────────────────────────
void setAllRed() {
  for (uint8_t i = 0; i < 12; i++) {
    // Các vị trí 0, 3, 6, 9 là đèn ĐỎ của 4 hướng (Pin 2, 5, 8, 11)
    bool isRed = (i % 3 == 0);
    digitalWrite(LED_PINS[i], isRed ? HIGH : LOW);
  }
}

void setAllOff() {
  for (uint8_t i = 0; i < 12; i++) {
    digitalWrite(LED_PINS[i], LOW);
  }
}

void applyLedBits(const String &bits) {
  for (uint8_t i = 0; i < 12 && i < bits.length(); i++) {
    char b = bits.charAt(i);
    digitalWrite(LED_PINS[i], (b == '1') ? HIGH : LOW);
  }
}

// ─── Xử lý gói lệnh từ Raspberry Pi 5 gửi xuống qua cổng COM ──────────────
void processCommand(String cmd) {
  cmd.trim();
  if (cmd.length() == 0) return;

  if (cmd.startsWith("LEDS:")) {
    String bits = cmd.substring(5);
    applyLedBits(bits);
    Serial.println("OK:LEDS");
  }
  else if (cmd.startsWith("LCD:")) {
    String content = cmd.substring(4);
    int sepIdx = content.indexOf('|');
    String line1 = "";
    String line2 = "";
    if (sepIdx >= 0) {
      line1 = content.substring(0, sepIdx);
      line2 = content.substring(sepIdx + 1);
    } else {
      line1 = content;
    }
    lcdShow(line1, line2);
    Serial.print("OK:LCD:");
    Serial.println(lcdFound ? "1" : "0");
  }
  else if (cmd == "ALL_RED") {
    setAllRed();
    Serial.println("OK:ALL_RED");
  }
  else if (cmd == "ALL_OFF") {
    setAllOff();
    Serial.println("OK:ALL_OFF");
  }
  else if (cmd == "PING") {
    if (!lcdFound) scanAndInitLCD();
    Serial.print("PONG LCD:");
    Serial.println(lcdFound ? "1" : "0");
  }
}

// ─── Khởi tạo hệ thống ─────────────────────────────────────────────────────
void setup() {
  // 1. Cấu hình 12 chân Digital (Pin 2 -> 13) làm OUTPUT
  for (uint8_t i = 0; i < 12; i++) {
    pinMode(LED_PINS[i], OUTPUT);
    digitalWrite(LED_PINS[i], LOW);
  }
  // Trạng thái khởi động an toàn: 4 hướng đều ĐỎ (Pin 2, 5, 8, 11 = HIGH)
  setAllRed();

  // 2. Khởi tạo cổng Serial kết nối với Raspberry Pi (115200 bps)
  Serial.begin(115200);
  serialBuffer.reserve(64);

  // 3. Khởi tạo Bus I2C (SDA = A4, SCL = A5 trên Arduino Uno R3)
  Wire.begin();
  scanAndInitLCD();
  if (lcdFound) {
    lcdShow("ARDUINO UNO R3  ", "Waiting Pi COM..");
  }

  // Báo hiệu sẵn sàng cho Raspberry Pi
  Serial.print("OK:READY LCD:");
  Serial.println(lcdFound ? "1" : "0");
}

// ─── Vòng lặp chính ────────────────────────────────────────────────────────
void loop() {
  while (Serial.available() > 0) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (serialBuffer.length() > 0) {
        processCommand(serialBuffer);
        serialBuffer = "";
      }
    } else {
      if (serialBuffer.length() < 60) {
        serialBuffer += c;
      }
    }
  }
}

