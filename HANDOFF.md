# Handoff · StickS3 Switch Bridge

> 交接时间：2026-10-26
> 当前版本：v0.1.0（本地 tag，已准备推 GitHub）
> 目标仓库：`github.com/TaoXieSZ/sticks3-switch-bridge`（public）

## 1. 这个项目是什么

把 **M5StickS3**（ESP32-S3-PICO-1-N8R8）变成 **Switch / Switch 2 认识的有线 Pro 手柄**，
由 Mac/PC 通过 Wi-Fi TCP 发按键包。

```
Mac/PC ──WiFi TCP 8765──> StickS3 ──USB HID──> Switch 2 dock
```

核心事实：

- Switch 2 支持 **Pro 手柄有线通讯**。
- ESP32-S3 有原生 USB OTG，可枚举成 `057E:2009` 有线 Pro 手柄。
- 不需要树莓派、不需要蓝牙 Classic。
- HID 描述符/驱动/握手来自 `churunfa/SwitchProControllerEsp32S3`（MIT，crf）。

## 2. 当前状态

| 项 | 状态 |
|---|---|
| 固件编译 `pio run -e sticks3` | ✅ SUCCESS（996 KB，Flash 29.8%，RAM 21.2%） |
| StickS3 + Switch 2 实际按键 | ✅ 已验证（在安全补丁之前） |
| Wi-Fi TCP + Python CLI | ✅ 已验证 |
| Host 单元测试 | ✅ 16 passed |
| 安全补丁（Wi-Fi 断线松键） | ✅ 已进源码；**用户手上的旧固件还没重烧** |
| 仓库 | ✅ 本地 git，2 个 commit 以上，tag `v0.1.0` |
| GitHub | ⏳ 待创建/推送（gh 已登录 `TaoXieSZ`） |
| 文档 | README / PROTOCOL / firmware README / 本文 / XIAOHONGSHU |

## 3. 目录

```
firmware/
  platformio.ini          pioarduino 55.03.37；env: sticks3/cardputer/cores3
  src/main.cpp            Wi-Fi + TCP 8765 + 45-byte input report
  src/SwitchPro*.{h,cpp}  HID 描述符/驱动（第三方 MIT）
  src/wifi_secrets.h.example
host/
  esp32_switch.py         CLI（TCP；串口路径留给 UART 固件）
  gamepad.py              packet/Controller API
  tests/test_gamepad.py   16 个纯协议测试
docs/
  PROTOCOL.md             49-byte 包 / 45-byte 报告 / 按键位
  XIAOHONGSHU.md          发布草稿
  images/architecture.svg/png
```

## 4. 复现

```bash
cd firmware
cp src/wifi_secrets.h.example src/wifi_secrets.h
# 填 2.4GHz SSID / 密码（不要提交）

pio run -e sticks3 -t upload
pio device monitor -e sticks3
```

下载模式：按住 StickS3 侧面 reset 到绿灯闪，再 upload；完成后短按开关机/复位启动。

串口应看到：

```
StickS3 switch bridge
SwitchProDriver initialized
WiFi OK, IP=..., TCP=8765
```

## 5. 使用

```bash
cd host
python3 esp32_switch.py --tcp <IP>:8765 tap A
python3 esp32_switch.py --tcp <IP>:8765 test
python3 esp32_switch.py --tcp <IP>:8765 shell
```

Switch 2：设置 → 手柄与外设 → **Pro 手柄有线通讯** → 开。

## 6. 已知问题 / 坑

- **没有震动**：45 字节输入报告不带 rumble。
- **IMU 固定重力**：host 可改包，但没有真实体感。
- **TCP 无鉴权**：只适合可信局域网；不要端口映射。
- **Wi-Fi 2.4GHz only**。
- **`ARDUINO_USB_MODE` 重复定义警告**：板级 JSON 默认 `=1`，build_flags 设 `=0`；警告无害，HID 正常。
- **Cardputer / CoreS3 环境未实测**；只有 StickS3 + Switch 2 验证。
- **没有 CI / 预编译 bin / GitHub Release**；当前只有源码。
- **没有硬件照片/视频**；小红书封面目前用架构图，最好补实拍。
- **安全补丁未烧录**：如果用户继续用旧二进制，Wi-Fi 断线时可能保持按键；重烧即可。
- **仓库作者邮箱**已改为 `txie@users.noreply.github.com`，避免工作邮箱公开。

## 7. 下一步

1. 创建 GitHub public repo 并 push main + tags。
2. 加 GitHub Actions：`pio run -e sticks3`。
3. 发 v0.1.0 Release，附 `firmware.bin` + SHA256（可选）。
4. 补实拍/视频：StickS3 插底座、Switch 识别 Pro 手柄、`test` 按键。
5. 测 Switch 1（如果手头有）。
6. 可选：加 TCP token、mDNS、rumble 协议扩展。
7. 小红书：先发“玩法”，再发“开源”；草稿在 `docs/XIAOHONGSHU.md`。

## 8. 发布命令

```bash
cd /Users/txie/OpenSourceProjects/sticks3-switch-bridge
GH_HOST=github.com gh repo create sticks3-switch-bridge \
  --public --source=. --remote=origin --push
git push origin --tags
```

如果 repo 已存在：

```bash
git remote add origin git@github.com:TaoXieSZ/sticks3-switch-bridge.git
git push -u origin main --tags
```

## 9. 关键约束

- **不要提交** `firmware/src/wifi_secrets.h`、`.last_ip`、`.pio/`、`dist/`。
- 不要把 Nintendo / M5Stack 商标写成官方合作。
- 改动 HID 描述符/驱动时，记录 Switch 型号和固件版本。
- 第三方代码保留 MIT notice。
