#include "BridgeDisplay.h"

namespace {
constexpr uint16_t BG = 0x0000;
constexpr uint16_t TEXT = 0xFFFF;
constexpr uint16_t MUTED = 0x7BEF;
constexpr uint16_t ACCENT_CYAN = 0x07FF;
constexpr uint16_t ACCENT_GOLD = 0xFFE0;
constexpr uint16_t ACCENT_RED = 0xF800;
constexpr uint16_t LINE = 0x2124;
}

void BridgeDisplay::begin() {
    display.init();
    display.setRotation(0);
    display.setBrightness(128);
    display.fillScreen(BG);
    lastDrawMs = 0;
    dirty = true;
    loop();
}

void BridgeDisplay::setContent(ScreenState state, const String &line1, const String &line2,
                               const String &primary, const String &detail,
                               const String &footer1, const String &footer2) {
    if (screenState == state && titleLine1 == line1 && titleLine2 == line2 &&
        primaryText == primary && detailText == detail &&
        footerLine1 == footer1 && footerLine2 == footer2) {
        return;
    }
    screenState = state;
    titleLine1 = line1;
    titleLine2 = line2;
    primaryText = primary;
    detailText = detail;
    footerLine1 = footer1;
    footerLine2 = footer2;
    dirty = true;
}

void BridgeDisplay::showWiFiConnecting(uint8_t index, uint8_t total) {
    String network = "Network " + String(index) + "/" + String(total);
    setContent(ScreenState::Connecting, "Joining", "Wi-Fi", network, "2.4 GHz",
               "Trying in order", "TCP port 8765");
}

void BridgeDisplay::showReady(const String &address) {
    ipAddress = address;
    clientAddress = "";
    setContent(ScreenState::Ready, "Waiting for", "a client", ipAddress, "TCP port 8765",
               "Wi-Fi connected", "USB HID active");
}

void BridgeDisplay::showClient(const String &address) {
    clientAddress = address;
    setContent(ScreenState::Client, "Client", "connected", clientAddress, "Inputs neutral",
               "TCP connected", "Auto-release in 2s idle");
}

void BridgeDisplay::showInput(const SwitchProSerialInput &input) {
    const auto &buttons = input.inputs;
    String keys;
    uint8_t count = 0;
    auto append = [&](bool pressed, const char *name) {
        if (!pressed) return;
        ++count;
        if (count <= 2) {
            if (keys.length()) keys += " + ";
            keys += name;
        }
    };
    append(buttons.buttonA, "A");
    append(buttons.buttonB, "B");
    append(buttons.buttonX, "X");
    append(buttons.buttonY, "Y");
    append(buttons.buttonL, "L");
    append(buttons.buttonR, "R");
    append(buttons.buttonZL, "ZL");
    append(buttons.buttonZR, "ZR");
    append(buttons.buttonMinus, "MNS");
    append(buttons.buttonPlus, "PLS");
    append(buttons.buttonThumbL, "L3");
    append(buttons.buttonThumbR, "R3");
    append(buttons.dpadUp, "UP");
    append(buttons.dpadDown, "DN");
    append(buttons.dpadLeft, "LF");
    append(buttons.dpadRight, "RT");
    append(buttons.buttonHome, "HM");
    append(buttons.buttonCapture, "CAP");

    const uint16_t lx = input.leftStick.getX();
    const uint16_t ly = input.leftStick.getY();
    const uint16_t rx = input.rightStick.getX();
    const uint16_t ry = input.rightStick.getY();
    const bool leftMoved = lx > 2304 || lx < 1792 || ly > 2304 || ly < 1792;
    const bool rightMoved = rx > 2304 || rx < 1792 || ry > 2304 || ry < 1792;

    if (count) {
        String second = count > 2 ? String("+") + String(count - 2) + " more" : String("pressed");
        setContent(ScreenState::Input, keys, second, clientAddress, "Input received",
                   "TCP connected", "Auto-release in 2s idle");
        return;
    }
    if (leftMoved || rightMoved) {
        String stick = leftMoved && rightMoved ? "L + R" : leftMoved ? "Left" : "Right";
        String values = leftMoved ? String(lx) + "," + String(ly) : String(rx) + "," + String(ry);
        setContent(ScreenState::Input, stick, "stick", values, clientAddress,
                   "TCP connected", "Auto-release in 2s idle");
        return;
    }
    showClient(clientAddress);
}

void BridgeDisplay::showWiFiDropped(bool inputsNeutral) {
    setContent(ScreenState::WiFiLost, "Wi-Fi", "lost", "Retrying...",
               inputsNeutral ? "Inputs neutral" : "Release in 2s",
               "Connection interrupted", "USB HID active");
}

void BridgeDisplay::showReleased(BridgeReleaseReason reason) {
    releaseReason = reason;
    String primary;
    String detail;
    if (reason == BridgeReleaseReason::WiFiLost) {
        primary = "Wi-Fi lost";
        detail = "Retrying connection...";
    } else if (reason == BridgeReleaseReason::ClientDisconnected) {
        primary = clientAddress;
        detail = "Client disconnected";
    } else {
        primary = "2s idle";
        detail = "Timeout protection";
    }
    setContent(ScreenState::Released, "Controls", "released", primary, detail,
               "Inputs neutral", "USB HID active");
}

void BridgeDisplay::loop() {
    const unsigned long now = millis();
    if (!dirty || now - lastDrawMs < 100) return;
    draw();
    dirty = false;
    lastDrawMs = now;
}

void BridgeDisplay::draw() {
    const int width = display.width();
    const int height = display.height();
    int scale = 1;
    if (width / 135 > 1 && height / 240 > 1) {
        scale = width / 135 < height / 240 ? width / 135 : height / 240;
    }
    const int ox = (width - 135 * scale) / 2;
    const int oy = (height - 240 * scale) / 2;
    auto x = [&](int value) { return ox + value * scale; };
    auto y = [&](int value) { return oy + value * scale; };

    uint16_t accent = ACCENT_CYAN;
    const char *kicker = "BOOT / 00";
    if (screenState == ScreenState::Connecting) {
        accent = ACCENT_GOLD;
        kicker = "LINK / 01";
    } else if (screenState == ScreenState::Ready) {
        kicker = "READY / 02";
    } else if (screenState == ScreenState::Client || screenState == ScreenState::Input) {
        kicker = "LIVE / 03";
    } else if (screenState == ScreenState::WiFiLost) {
        accent = ACCENT_RED;
        kicker = "OFFLINE / 04";
    } else if (screenState == ScreenState::Released) {
        accent = releaseReason == BridgeReleaseReason::WiFiLost ? ACCENT_RED : ACCENT_GOLD;
        kicker = "SAFE / 04";
    }

    display.fillScreen(BG);
    display.setTextDatum(top_left);
    display.setFont(&fonts::Font2);
    display.setTextSize(scale * 0.5);
    display.setTextColor(MUTED, BG);
    display.drawString("SWITCH BRIDGE", x(7), y(8));

    if (screenState != ScreenState::WiFiLost && screenState != ScreenState::Released) {
        display.fillRect(x(116), y(13), 2 * scale, 3 * scale, accent);
        display.fillRect(x(121), y(10), 2 * scale, 6 * scale, accent);
        display.fillRect(x(126), y(7), 2 * scale, 9 * scale, accent);
    }

    display.setTextColor(accent, BG);
    display.drawString(kicker, x(7), y(38));
    display.setFont(&fonts::Font4);
    display.setTextSize(scale);
    display.setTextColor(TEXT, BG);
    display.drawString(titleLine1, x(7), y(60));
    display.drawString(titleLine2, x(7), y(88));

    display.setFont(&fonts::Font2);
    display.setTextColor(accent, BG);
    display.drawString(primaryText, x(7), y(130));
    display.setTextSize(scale * 0.5);
    display.setTextColor(MUTED, BG);
    display.drawString(detailText, x(7), y(154));

    display.drawLine(x(7), y(190), x(128), y(190), LINE);
    display.setTextColor(MUTED, BG);
    display.drawString(footerLine1, x(7), y(204));
    display.drawString(footerLine2, x(7), y(220));
}
