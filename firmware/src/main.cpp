#include <Arduino.h>
#include <WiFi.h>
#include <cstring>

#include "SwitchProDriver.h"
#include "BridgeDisplay.h"

struct WifiNetwork {
    const char *ssid;
    const char *pass;
};

#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#else
#define WIFI_NETWORK_LIST { {"YOUR_SSID", "YOUR_PASS"} }
#endif

static const WifiNetwork WIFI_NETWORKS[] = WIFI_NETWORK_LIST;
static constexpr size_t WIFI_NETWORK_COUNT = sizeof(WIFI_NETWORKS) / sizeof(WIFI_NETWORKS[0]);

// Mac -> ESP32：AA 55 + cmd + payload + XOR
// cmd=0x00，payload=45 字节（3 按键 + 3 左摇杆 + 3 右摇杆 + 36 IMU）
static constexpr uint16_t TCP_PORT = 8765;
static constexpr size_t REPORT_LEN = 45;
static constexpr size_t PACKET_LEN = 2 + 1 + REPORT_LEN + 1; // 49

static WiFiServer server(TCP_PORT);
static SwitchProDriver *driver = nullptr;
static SwitchProSerialInput input;
static BridgeDisplay display;
static unsigned long lastPacketMs = 0;
static bool neutralSent = true;
static bool wifiWasConnected = false;
static size_t wifiIndex = 0;
static unsigned long lastWifiAttemptMs = 0;

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
    display.showInput(input);
    return true;
}

static void releaseAll(BridgeReleaseReason reason) {
    input = SwitchProSerialInput();
    driver->updateInputReport(&input, true);
    neutralSent = true;
    display.showReleased(reason);
}

static bool connectAnyWiFi(uint32_t perNetworkMs = 12000) {
    for (size_t n = 0; n < WIFI_NETWORK_COUNT; ++n) {
        const size_t idx = (wifiIndex + n) % WIFI_NETWORK_COUNT;
        const WifiNetwork &net = WIFI_NETWORKS[idx];
        display.showWiFiConnecting(idx + 1, WIFI_NETWORK_COUNT);
        Serial.printf("WiFi try %u/%u\n", static_cast<unsigned>(idx + 1),
                      static_cast<unsigned>(WIFI_NETWORK_COUNT));
        WiFi.disconnect();
        WiFi.begin(net.ssid, net.pass);
        const unsigned long start = millis();
        while (WiFi.status() != WL_CONNECTED && millis() - start < perNetworkMs) {
            delay(250);
            display.loop();
        }
        if (WiFi.status() == WL_CONNECTED) {
            wifiIndex = idx;
            wifiWasConnected = true;
            lastWifiAttemptMs = millis();
            Serial.printf("WiFi OK, IP=%s, TCP=%u\n",
                          WiFi.localIP().toString().c_str(), TCP_PORT);
            display.showReady(WiFi.localIP().toString());
            return true;
        }
        Serial.println("WiFi try failed");
    }
    display.showWiFiDropped(neutralSent);
    return false;
}

void setup() {
    Serial.begin(115200);
    delay(300);
    Serial.println("\nStickS3 switch bridge");
    display.begin();

    // USB HID 必须在 setup 里初始化；worker 线程会处理握手与上报
    driver = &SwitchProDriver::getInstance();
    Serial.println("SwitchProDriver initialized");

    WiFi.mode(WIFI_STA);
    WiFi.setSleep(false);
    connectAnyWiFi(12000);
    server.begin();
    lastPacketMs = millis();
    lastWifiAttemptMs = millis();
    display.loop();
}

void loop() {
    if (WiFi.status() != WL_CONNECTED) {
        if (wifiWasConnected) {
            wifiWasConnected = false;
            display.showWiFiDropped(neutralSent);
        }
        // Safety: if Wi-Fi drops while a button is held, don't leave it stuck.
        if (!neutralSent && millis() - lastPacketMs > 2000) {
            releaseAll(BridgeReleaseReason::WiFiLost);
        }
        display.loop();
        if (millis() - lastWifiAttemptMs > 10000) {
            lastWifiAttemptMs = millis();
            connectAnyWiFi(8000);
        }
        delay(50);
        return;
    }

    if (!wifiWasConnected) {
        wifiWasConnected = true;
        display.showReady(WiFi.localIP().toString());
    }

    WiFiClient client = server.available();
    if (!client) {
        if (!neutralSent && millis() - lastPacketMs > 2000) {
            releaseAll(BridgeReleaseReason::IdleTimeout);
        }
        display.loop();
        delay(1);
        return;
    }

    client.setNoDelay(true);
    const String clientAddress = client.remoteIP().toString();
    Serial.printf("client connected: %s\n", clientAddress.c_str());
    display.showClient(clientAddress);
    display.loop();
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
            releaseAll(BridgeReleaseReason::IdleTimeout);
        }
        display.loop();
        delay(1);
    }

    Serial.println("client disconnected");
    releaseAll(BridgeReleaseReason::ClientDisconnected);
    display.loop();
}
