#!/usr/bin/env python3
"""Switch Pro 有线手柄的高层 API + 传输层。

- TcpLink：Mac → WiFi → StickS3（当前主用）
- SerialLink：Mac → USB-TTL → ESP32 UART（备选）
- Controller：按键/摇杆/组合/长按/序列/自检

协议：AA 55 + cmd(0x00) + 45 字节报告 + XOR
"""
from __future__ import annotations

import socket
import time

BAUD = 3_000_000
DEFAULT_PORT = 8765

# (byte, bit) —— SwitchProReport 的 3 字节按键位
BUTTONS = {
    "Y": (0, 0), "X": (0, 1), "B": (0, 2), "A": (0, 3),
    "SR": (0, 4), "SL": (0, 5), "R": (0, 6), "ZR": (0, 7),
    "MINUS": (1, 0), "PLUS": (1, 1), "THUMB_R": (1, 2), "THUMB_L": (1, 3),
    "HOME": (1, 4), "CAPTURE": (1, 5),
    "DOWN": (2, 0), "UP": (2, 1), "RIGHT": (2, 2), "LEFT": (2, 3),
    "LEFT_SL": (2, 4), "LEFT_SR": (2, 5), "L": (2, 6), "ZL": (2, 7),
}

# 3 个 IMU 采样：accY=4096（重力），其余 0；每个采样 12 字节
IMU_SAMPLE = bytes([0x00, 0x00, 0x00, 0x10, 0x00, 0x00,
                    0x00, 0x00, 0x00, 0x00, 0x00, 0x00])
IMU = IMU_SAMPLE * 3
WAKE = b"\xAA\x55\x04\x00\x04"


def pack_stick(x: int, y: int) -> bytes:
    x = max(0, min(4095, int(x)))
    y = max(0, min(4095, int(y)))
    return bytes([
        x & 0xFF,
        ((x >> 8) & 0x0F) | ((y & 0x0F) << 4),
        (y >> 4) & 0xFF,
    ])


def build_report(pressed, lx=2048, ly=2048, rx=2048, ry=2048, imu: bytes | None = None) -> bytes:
    b = [0, 0, 0]
    for name in pressed:
        key = str(name).upper()
        if key not in BUTTONS:
            raise ValueError(f"未知按键：{name}（可用：{', '.join(sorted(BUTTONS))}）")
        byte, bit = BUTTONS[key]
        b[byte] |= 1 << bit
    b[1] |= 1 << 7              # chargingGrip
    b[2] |= (1 << 4) | (1 << 5)  # LeftSL / LeftSR，跟参考库 resetAll 一致
    report = bytes(b) + pack_stick(lx, ly) + pack_stick(rx, ry) + (imu or IMU)
    assert len(report) == 45, len(report)
    return report


def packet(report: bytes) -> bytes:
    chk = 0
    for v in report:
        chk ^= v
    return b"\xAA\x55\x00" + report + bytes([chk])


def normalize(names) -> list[str]:
    if isinstance(names, str):
        names = [names]
    out = []
    for item in names:
        for n in str(item).replace(",", " ").split():
            n = n.strip().upper()
            if n:
                out.append(n)
    return out


class TcpLink:
    def __init__(self, host: str, port: int = DEFAULT_PORT, timeout: float = 3.0):
        self.addr = (host, int(port))
        self.sock = socket.create_connection(self.addr, timeout=timeout)
        self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

    def send(self, data: bytes):
        self.sock.sendall(data)

    def close(self):
        try:
            self.sock.close()
        except OSError:
            pass


class SerialLink:
    def __init__(self, port: str, baud: int = BAUD):
        import serial  # 延迟导入，TCP 模式不需要 pyserial
        self.ser = serial.Serial(port, baud, timeout=0.1, write_timeout=0.5)
        time.sleep(0.2)

    def send(self, data: bytes):
        self.ser.write(data)
        self.ser.flush()

    def close(self):
        try:
            self.ser.close()
        except Exception:
            pass


class Controller:
    def __init__(self, link, imu: bytes | None = None):
        self.link = link
        self.pressed: set[str] = set()
        self.left = (2048, 2048)
        self.right = (2048, 2048)
        self.imu = imu or IMU

    def flush(self):
        self.link.send(packet(build_report(self.pressed, *self.left, *self.right, self.imu)))

    def press(self, names):
        for n in normalize(names):
            if n not in BUTTONS:
                raise ValueError(f"未知按键：{n}")
            self.pressed.add(n)
        self.flush()

    def release(self, names):
        for n in normalize(names):
            self.pressed.discard(n)
        self.flush()

    def tap(self, names, hold: float = 0.08):
        names = normalize(names)
        if not names:
            raise ValueError("tap 需要按键")
        self.press(names)
        time.sleep(max(0.0, hold))
        self.release(names)

    def combo(self, names, hold: float = 0.15):
        self.tap(names, hold)

    def hold(self, name, seconds: float):
        self.press(name)
        time.sleep(max(0.0, seconds))
        self.release(name)

    def stick(self, left=None, right=None):
        if left is not None:
            self.left = (int(left[0]), int(left[1]))
        if right is not None:
            self.right = (int(right[0]), int(right[1]))
        self.flush()

    def reset(self):
        self.pressed.clear()
        self.left = (2048, 2048)
        self.right = (2048, 2048)
        self.flush()

    def set_imu(self, acc=(0, 4096, 0), gyro=(0, 0, 0)):
        sample = b"".join(int(v).to_bytes(2, "little", signed=True) for v in (*acc, *gyro))
        self.imu = sample * 3
        self.flush()

    def test(self, include_home: bool = False, include_capture: bool = False,
             hold: float = 0.12, gap: float = 0.35):
        """逐个按键自检；用户看着 Switch 画面确认。"""
        order = ["A", "B", "X", "Y", "UP", "DOWN", "LEFT", "RIGHT",
                 "L", "R", "ZL", "ZR", "PLUS", "MINUS", "THUMB_L", "THUMB_R"]
        if include_capture:
            order.append("CAPTURE")
        if include_home:
            order.append("HOME")
        for name in order:
            print(f"  tap {name}", flush=True)
            self.tap(name, hold)
            time.sleep(gap)
        print("  stick left: 1024 → 3072", flush=True)
        for x in (1024, 1536, 2048, 2560, 3072, 2048):
            self.stick(left=(x, 2048))
            time.sleep(0.08)
        print("  stick right: 1024 → 3072", flush=True)
        for x in (1024, 1536, 2048, 2560, 3072, 2048):
            self.stick(right=(x, 2048))
            time.sleep(0.08)
        self.reset()
        print("  reset", flush=True)

    def sequence(self, spec: str, default_hold: float = 0.08, gap: float = 0.12):
        """逗号分隔的序列：
        A:0.1      tap A 100ms
        wait:0.3   等待 300ms
        press:ZR   按住
        release:ZR 松开
        A+B:0.15   组合键
        """
        for raw in spec.split(","):
            token = raw.strip()
            if not token:
                continue
            if token.startswith("wait:"):
                time.sleep(float(token.split(":", 1)[1]))
            elif token.startswith("press:"):
                print(f"  press {token.split(':', 1)[1]}", flush=True)
                self.press(token.split(":", 1)[1])
                time.sleep(gap)
            elif token.startswith("release:"):
                print(f"  release {token.split(':', 1)[1]}", flush=True)
                self.release(token.split(":", 1)[1])
                time.sleep(gap)
            else:
                name, _, hold = token.partition(":")
                h = float(hold) if hold else default_hold
                print(f"  tap {name} {h}s", flush=True)
                self.tap(name, h)
                time.sleep(gap)

    def close(self):
        try:
            self.reset()
        finally:
            self.link.close()
