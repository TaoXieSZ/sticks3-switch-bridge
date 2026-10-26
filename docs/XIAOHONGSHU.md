# 小红书草稿 · M5StickS3 × Switch 2

> 发布前把 https://github.com/TaoXieSZ/sticks3-switch-bridge 换成真实仓库地址；先发“玩法/过程”，再发“开源”第二条，流量更好。

## 标题备选

1. 把 M5StickS3 变成 Switch 2 的 Pro 手柄，真能用
2. M5Stack 新玩法：StickS3 当 Switch 有线手柄
3. 不用树莓派，一块 ESP32-S3 让 Switch 2 认手柄

## 正文

我搜了一圈，没找到现成的 **M5StickS3 → Switch 2 有线 Pro 手柄** 固件，于是自己写了一个。

原理不复杂：Switch 2 支持 **Pro 手柄有线通讯**，而 ESP32-S3 有原生 USB，可以把自己枚举成 `057E:2009` 的有线 Pro 手柄。StickS3 只负责两件事：

1. USB HID 手柄；
2. Wi‑Fi 收 Mac/PC 发来的 49 字节按键包。

```
Mac/PC ──WiFi TCP 8765──> StickS3 ──USB HID──> Switch 2 底座
```

### 能做什么

- 全部按键：A/B/X/Y、L/R/ZL/ZR、十字键、Plus/Minus、Home/Capture、L3/R3
- 左右摇杆 12‑bit
- Python 端：`tap` / `hold` / `combo` / `stick` / `sequence` / `shell` / `test`
- 2 秒无包自动松键；Wi‑Fi 断开也会松键，避免卡键

### 硬件

- M5StickS3（ESP32‑S3‑PICO‑1，8MB Flash + 8MB PSRAM）
- USB‑C 数据线
- Switch 2 底座 USB‑A
- 2.4GHz Wi‑Fi（S3 不支持 5GHz）

### 步骤

1. 编译固件，填 2.4GHz Wi‑Fi；
2. `pio run -e sticks3 -t upload`；
3. 串口看 IP；
4. StickS3 插底座 USB‑A；
5. Switch 2 打开“Pro 手柄有线通讯”；
6. Mac 上 `python3 esp32_switch.py --tcp <IP>:8765 test`。

### 适合谁

- 想把 M5Stack 玩出屏幕/手表之外用途的人；
- 想做桌面宏手柄、无障碍输入、AI 读屏/教练的人；
- 不想为一个小手柄买树莓派的人。

### 注意

- 不是任天堂/M5Stack 官方，自己承担风险；
- TCP 没有鉴权，只在可信局域网用；
- 没有震动，IMU 是固定重力；
- Switch 固件更新可能影响 HID 握手。

代码和接线都整理成单独仓库了：https://github.com/TaoXieSZ/sticks3-switch-bridge
（MIT，含 HID 驱动来源说明；不要提交 Wi‑Fi 密码。）

## 配图建议

1. 封面：StickS3 插在 Switch 底座上的实拍 + 大字“StickS3 → Switch 2 手柄”
2. 架构图：`docs/images/architecture.svg` 导出 PNG
3. 串口 IP / `tap A` 终端截图
4. Switch 2 “Pro 手柄有线通讯”设置页
5. 仓库 README 截图

## 标签

#M5Stack #M5StickS3 #ESP32S3 #Switch2 #任天堂 #开源 #DIY #嵌入式 #手柄 #桌面搭子

## 评论区引导

- “想看固件/接线细节扣 1”
- “下一期：用这块 StickS3 做 AI 读屏/自动菜单”
