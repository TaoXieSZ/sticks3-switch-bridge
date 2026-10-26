#include <Arduino.h>
#include <WiFi.h>
#include <cstring>

#include "SwitchProDriver.h"

#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#else
#define WIFI_SSID "YOUR_SSID"
#define WIFI_PASS "YOUR_PASS"
#endif

// Mac -> ESP32：AA 55 + cmd + payload + XOR
// cmd=0x00，payload=45 字节（3 按键 + 3 左摇杆 + 3 右摇杆 + 36 IMU）
static constexpr uint16_t TCP_PORT = 8765;
static constexpr size_t REPORT_LEN = 45;
static constexpr size_t PACKET_LEN = 2 + 1 + REPORT_LEN + 1; // 49

static WiFiServer server(TCP_PORT);
static SwitchProDriver *driver = nullptr;
static SwitchProSerialInput input;
static unsigned long lastPacketMs = 0;
static bool neutralSent = true;

static_assert(sizeof(SwitchProSerialInput) == REPORT_LEN, "SwitchProSerialInput must be 45 bytes");

static bool handlePacket(const uint8_t *buf) {
    if (buf[0] != 0xAA || buf[1] != 0x55 || buf[2] != 0x00) {
        return false;
    }
    uint8_t chk = 0;
    for (size_t i = 2; i < PACKET_LEN - 1; ++i) {
        chk ^= buf[i];
    }
    if (chk != buf[PACKET_LEN - 1]) {
        Serial.println("bad checksum");
        return false;
    }
    std::memcpy(&input, buf + 3, REPORT_LEN);
    driver->updateInputReport(&input, true);
    neutralSent = false;
    return true;
}

static void releaseAll() {
    input = SwitchProSerialInput();
    driver->updateInputReport(&input, true);
    neutralSent = true;
}

static void connectWiFi() {
    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    WiFi.begin(WIFI_SSID, WIFI_PASS);
    const unsigned long start = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - start < 20000) {
        delay(500);
        Serial.print(".");
    }
    Serial.println();
    if (WiFi.status() == WL_CONNECTED) {
        Serial.printf("WiFi OK, IP=%s, TCP=%u\n", WiFi.localIP().toString().c_str(), TCP_PORT);
    } else {
        Serial.println("WiFi failed; will retry in loop");
    }
}

void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("\nStickS3 switch bridge");

    // USB HID 必须在 setup 里初始化；worker 线程会处理握手与上报
    driver = &SwitchProDriver::getInstance();
    Serial.println("SwitchProDriver initialized");

    connectWiFi();
    server.begin();
    lastPacketMs = millis();
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        // Safety: if Wi-Fi drops while a button is held, don't leave it stuck.
        if (!neutralSent && millis() - lastPacketMs > 2000) {
            releaseAll();
        }
        WiFi.reconnect();
        delay(1000);
        return;
    }

    WiFiClient client = server.available();
    if (!client) {
        if (!neutralSent && millis() - lastPacketMs > 2000) {
            releaseAll();
        }
        delay(1);
        return;
    }

    client.setNoDelay(true);
    Serial.printf("client connected: %s\n", client.remoteIP().toString().c_str());
    uint8_t buf[PACKET_LEN];
    size_t len = 0;
    lastPacketMs = millis();

    while (client.connected()) {
        while (client.available()) {
            buf[len++] = static_cast<uint8_t>(client.read());
            if (len == PACKET_LEN) {
                if (handlePacket(buf)) {
                    lastPacketMs = millis();
                }
                len = 0;
            }
        }
        if (!neutralSent && millis() - lastPacketMs > 2000) {
            releaseAll();
        }
        delay(1);
    }

    Serial.println("client disconnected");
    releaseAll();
}
