#pragma once

#include <Arduino.h>
#include <M5GFX.h>

#include "SwitchProDriver.h"

enum class BridgeReleaseReason : uint8_t {
    IdleTimeout,
    ClientDisconnected,
    WiFiLost,
};

class BridgeDisplay {
public:
    void begin();
    void showWiFiConnecting(uint8_t index, uint8_t total);
    void showReady(const String &ipAddress);
    void showClient(const String &clientAddress);
    void showInput(const SwitchProSerialInput &input);
    void showWiFiDropped(bool inputsNeutral);
    void showReleased(BridgeReleaseReason reason);
    void loop();

private:
    enum class ScreenState : uint8_t {
        Boot,
        Connecting,
        Ready,
        Client,
        Input,
        WiFiLost,
        Released,
    };

    M5GFX display;
    ScreenState screenState = ScreenState::Boot;
    String ipAddress;
    String clientAddress;
    String titleLine1 = "Switch";
    String titleLine2 = "Bridge";
    String primaryText = "USB HID";
    String detailText = "Starting...";
    String footerLine1 = "Native USB";
    String footerLine2 = "Controller bridge";
    BridgeReleaseReason releaseReason = BridgeReleaseReason::IdleTimeout;
    bool dirty = true;
    unsigned long lastDrawMs = 0;

    void setContent(ScreenState state, const String &line1, const String &line2,
                    const String &primary, const String &detail,
                    const String &footer1, const String &footer2);
    void draw();
};
