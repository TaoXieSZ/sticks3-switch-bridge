# firmware · ESP32-S3 wired Pro Controller

Target: **M5StickS3** (ESP32‑S3‑PICO‑1‑N8R8, 8MB flash + 8MB PSRAM).
Also builds for Cardputer‑ADV and CoreS3.

The firmware enumerates as a **wired Switch Pro Controller** over native USB and
accepts 49-byte control packets over Wi‑Fi TCP **8765**.

## Build

```bash
cp src/wifi_secrets.h.example src/wifi_secrets.h
# fill 2.4GHz SSID / password

pio run -e sticks3 -t upload
pio device monitor -e sticks3
```

If upload fails with `No serial data received`, put the board in download mode
(hold reset until the green LED blinks), then upload again.

## Boot log

```
StickS3 switch bridge
SwitchProDriver initialized
WiFi OK, IP=192.168.x.x, TCP=8765
```

The USB HID device is `057E:2009` (`Nintendo Co., Ltd` / `Switch Pro Controller`).
If the Mac shows `Espressif USB JTAG_serial debug unit`, the app didn't boot or
TinyUSB didn't take over; reset/power-cycle the board.

## Wi-Fi

- 2.4GHz only.
- `WiFi.setSleep(false)` for latency.
- Credentials live in `src/wifi_secrets.h`; it is gitignored.
- TCP has **no authentication**. Use a trusted LAN; don't port-forward 8765.

## Safety

- 2 seconds without a packet → all buttons released.
- TCP disconnect → all buttons released.
- Wi-Fi disconnect while a button is held → release after 2s (see `loop()`).
- `neutralSent` prevents repeated release reports.

## Build environments

| env | board | notes |
|---|---|---|
| `sticks3` | M5StickS3 | default; 8MB flash + 8MB PSRAM |
| `cardputer` | Cardputer‑ADV | 8MB flash, no PSRAM |
| `cores3` | CoreS3 | 16MB flash + 8MB PSRAM |

The board JSON is `esp32-s3-devkitc-1`; `ARDUINO_USB_MODE=0` selects TinyUSB.
The duplicate `ARDUINO_USB_MODE` warning is harmless.

## HID core

`SwitchProDescriptors.h`, `SwitchProDriver.*`, `driverhelper.h` are derived from
[churunfa/SwitchProControllerEsp32S3](https://github.com/churunfa/SwitchProControllerEsp32S3)
(MIT). See `../THIRD_PARTY_NOTICES.md`.
