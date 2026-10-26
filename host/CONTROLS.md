# 手柄功能 · 全部按键 / 摇杆 / 序列 / 自检

当前链路：

```
Mac ──WiFi TCP 192.168.x.x:8765──> StickS3 ──USB HID──> Switch 2 底座
```

- 按键映射来自 Switch 有线 Pro 手柄的 45 字节报告。
- 默认自动找 IP：先读 `.last_ip`，再查 ARP（`14:c1:9f:d5`）。
- 所有命令都走同一条 TCP；固件 2 秒没收到包会自动松键。

## 全部按键

| 分类 | 名称 | CLI |
|---|---|---|
| 动作 | A / B / X / Y | `tap A`、`tap A,B` |
| 肩键 | L / R / ZL / ZR | `hold ZR 1.5` |
| 十字键 | UP / DOWN / LEFT / RIGHT | `tap DOWN` |
| 菜单 | PLUS / MINUS | `tap PLUS` |
| 系统 | HOME / CAPTURE | `tap HOME`（会回主菜单） |
| 摇杆按下 | THUMB_L / THUMB_R | `tap THUMB_L` |
| Joy-Con 专用 | SL / SR / LEFT_SL / LEFT_SR | 一般不用 |

## 常用命令

```bash
cd sticks3-switch-bridge/host

# 单键 / 组合
python3 esp32_switch.py tap A
python3 esp32_switch.py tap A,B
python3 esp32_switch.py tap DOWN

# 长按
python3 esp32_switch.py hold ZR 1.5
python3 esp32_switch.py press ZR --seconds 1.0   # 按住 1 秒再松
python3 esp32_switch.py release                  # 松所有键

# 摇杆：0–4095，中心 2048
python3 esp32_switch.py stick left 1024 2048
python3 esp32_switch.py stick 2048 2048 3072 2048   # 左/右

# 列出按键 / 找 IP
python3 esp32_switch.py buttons
python3 esp32_switch.py --discover
```

## 自检：逐个按键

在 Switch 主界面或“测试手柄”界面运行：

```bash
python3 esp32_switch.py test
```

它会依次 tap：

```
A B X Y UP DOWN LEFT RIGHT L R ZL ZR PLUS MINUS THUMB_L THUMB_R
```

再扫左右摇杆，最后 reset。默认**不按 HOME/CAPTURE**；要包含：

```bash
python3 esp32_switch.py test --include-home --include-capture
```

> 自检会在菜单里乱走，建议在 Switch 主界面或手柄测试界面看。

## 序列 / 宏

```bash
python3 esp32_switch.py sequence "A:0.1,wait:0.3,DOWN:0.1,A:0.1"
python3 esp32_switch.py sequence "press:ZR,wait:1.5,release:ZR"
python3 esp32_switch.py sequence "A+B:0.2,wait:0.3"
```

语法：

| Token | 含义 |
|---|---|
| `A` | tap A，默认 80ms |
| `A:0.2` | tap A，按住 200ms |
| `A+B:0.2` | 组合键 |
| `wait:0.3` | 等待 300ms |
| `press:ZR` | 按住 |
| `release:ZR` | 松开 |

## 交互 shell

需要真正的“按住 → 过一会儿松开”时用 shell（单条 `press` 命令退出后，固件会在 2 秒内自动松键）：

```bash
python3 esp32_switch.py shell
switch> press ZR
switch> wait 1.5      # 实际用 hold ZR 1.5 更直接
switch> release ZR
switch> tap A
switch> stick left 1024 2048
switch> reset
switch> quit
```

## Python API

```python
from gamepad import TcpLink, Controller

ctrl = Controller(TcpLink("192.168.x.x", 8765))
try:
    ctrl.tap("A")
    ctrl.hold("ZR", 1.5)
    ctrl.stick(left=(1024, 2048))
    ctrl.sequence("A:0.1,wait:0.3,DOWN:0.1")
finally:
    ctrl.close()
```

`Controller` 提供：`press / release / tap / combo / hold / stick / reset / set_imu / test / sequence`。

## 限制

- **没有震动**：45 字节 UART 报告不带 rumble；要支持得扩协议/固件。
- **IMU 默认固定重力**：`set_imu` 可以改，但不是真实体感；大多数游戏不需要。
- **`press`/`release` 跨进程无效**：固件在 TCP 断开/2 秒无包时自动松键；用 `shell`、`sequence` 或 `hold`。
- **`wake` 暂无效果**：固件收到 `AA 55 04 00 04` 会忽略；唤醒请按手柄/主机。
- **IP 是 DHCP**：`.last_ip` 缓存 + ARP 找；换网络后可能要 `--tcp` 手动指定。
- **HOME/CAPTURE** 会改变主机状态；自检默认不按。
