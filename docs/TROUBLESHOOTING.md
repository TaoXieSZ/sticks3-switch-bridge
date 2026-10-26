# Troubleshooting

## Upload

### `Failed to connect ... No serial data received`

StickS3 没进下载模式。

1. 按住侧面 reset 键，直到绿灯闪烁；
2. 再 `pio run -e sticks3 -t upload`；
3. 上传完成后短按开关机/复位启动应用。

### `Could not open port / device busy`

关掉串口监视器、OBS 的串口占用、其他 `pio device monitor`。

### `ARDUINO_USB_MODE redefined`

板级 JSON 默认 `-DARDUINO_USB_MODE=1`，`build_flags` 又设 `=0`。警告无害；
只要最终枚举为 `057E:2009` 就正常。

## USB HID

### Mac 看到 `Espressif USB JTAG_serial debug unit`

应用没启动，或 TinyUSB 没接管。

- 短按复位/拔插 USB；
- 确认 `ARDUINO_USB_MODE=0`；
- 看串口有没有 `StickS3 switch bridge` / `SwitchProDriver initialized`；
- 如果一直进下载模式，松开 reset 后短按一次电源键。

### Switch 不认手柄

- Switch 2：设置 → 手柄与外设 → **Pro 手柄有线通讯** → 开；
- 用**数据线**，不是纯充电线；
- 插底座 USB-A，不要插到不供电的 Hub；
- 确认 Mac 上枚举为 `Switch Pro Controller` / `057E:2009`；
- 换一根线/换一个底座口再试。

## Wi-Fi / TCP

### `WiFi failed; will retry in loop`

- 只支持 2.4GHz；
- SSID/密码是否写进 `wifi_secrets.h`；
- 路由器是否开了客户端隔离；
- 串口看是否拿到 IP。

### 连接超时 / `No route to host`

- IP 变了：串口重新看 IP；
- Mac 和 StickS3 是否同一网段；
- 防火墙是否拦了 8765；
- `ping <IP>` 先确认。

### 按键卡住

- 固件 2 秒无包会松键；Wi-Fi 断线也会松键（安全补丁后）；
- 确认用的是最新固件；
- 发一包全 0 报告/重新连接即可。

## Host

### `ModuleNotFoundError: serial`

只有串口模式需要：

```bash
python3 -m pip install pyserial
```

TCP 模式不需要。

### `--discover` 找不到

默认没有硬编码 MAC。用 `--tcp <IP>:8765`，或设置：

```bash
export STICKS3_MAC_PREFIX=14:c1:9f
```

## Build

### PlatformIO 下载平台很慢/失败

首次构建要下 pioarduino 55.03.37 + 工具链，约 20–30 分钟。
网络不稳时重试，或使用已有 PlatformIO Core 缓存。

### 内存/分区不足

StickS3 用 `default_8MB.csv`；换板子时同步改 `board_build.partitions` 和
`board_upload.flash_size`。
