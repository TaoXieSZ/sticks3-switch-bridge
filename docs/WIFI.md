# Wi-Fi 配置与双网络回退

## 目标

StickS3 在家里连家里 Wi‑Fi，出门自动尝试手机热点；两个都连不上就每 10 秒重试。

## 配置格式

`firmware/src/wifi_secrets.h` 被 `.gitignore` 忽略，不要提交。复制示例：

```bash
cd firmware
cp src/wifi_secrets.h.example src/wifi_secrets.h
```

编辑 `WIFI_NETWORK_LIST`，按优先级排列：

```cpp
#pragma once
#define WIFI_NETWORK_LIST { \
    {"home-ssid", "home-pass"}, \
    {"phone-hotspot", "hotspot-pass"} \
}
```

- 最多 4 个网络，按顺序尝试。
- 只支持 **2.4GHz**；ESP32‑S3 不支持 5GHz。
- 手机热点如果是 5GHz-only，ESP32 连不上；请在手机里打开“最大兼容性”/2.4GHz。
- SSID/密码是普通 C 字符串；中文 SSID 按 UTF‑8 保存即可。

## 回退行为

| 场景 | 行为 |
|---|---|
| 开机 | 从第 1 个网络开始，每个等 **12 秒** |
| 运行中掉线 | 从上次成功的网络开始，每个等 **8 秒** |
| 全部失败 | 每 **10 秒**重新尝试 |
| 成功 | 记录该网络，下次优先 |
| 屏幕 | `Network 1/2` → 连上后显示 IP |

日志：

```
WiFi try 1/2
WiFi OK, IP=192.168.x.x, TCP=8765
```

或：

```
WiFi try 1/2
WiFi try failed
WiFi try 2/2
WiFi OK, ...
```

## 构建与烧录

```bash
cd firmware
pio run -e sticks3 -t upload
```

如果 upload 报 `No serial data received`：

1. 按住 StickS3 侧面 reset 键到绿灯闪烁；
2. 再 upload；
3. 完成后短按开关机/复位启动。

> 刷机前核对设备 MAC/序列号，别刷错板子。

## 验证

1. 串口/屏幕出现 IP；
2. Mac 上 `ping <IP>`；
3. `python3 host/esp32_switch.py --tcp <IP>:8765 tap A`；
4. 关掉家里 Wi‑Fi（或走远），重启 StickS3，看是否切到热点。

## 排错

| 现象 | 处理 |
|---|---|
| `WiFi try failed` 两次 | 确认 2.4GHz、密码、SSID 大小写；手机热点开最大兼容性 |
| 连上但 `No route to host` | 手机热点可能开了客户端隔离；换家里 Wi‑Fi |
| 只有 5GHz | ESP32 连不上；开 2.4GHz 或热点兼容模式 |
| 串口一直点点点 | 还在 12 秒等待；等第二轮或看屏幕 `Network 1/2` |
| 连上后频繁掉 | 关路由器省电/漫游；`WiFi.setSleep(false)` 已开 |

## 安全

- `wifi_secrets.h` 是明文密码，已被 gitignore；不要提交、不要截图进公开仓库。
- TCP 8765 **没有鉴权**；只在可信局域网使用，不要端口映射。
- 公开仓库的 `wifi_secrets.h.example` 只有占位符。

## 当前状态（2026-11-07）

- 双网络回退代码已进 `main`，v0.1.1 Release。
- 本机 `wifi_secrets.h` 已配置“家里 + 手机热点”，但**尚未烧录到设备**；设备仍是旧固件。
- 家里网络已恢复，所以暂不急着刷；下次刷机后按“验证”步骤测试两种网络。
