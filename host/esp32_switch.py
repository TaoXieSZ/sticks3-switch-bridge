#!/usr/bin/env python3
"""Switch Pro 有线手柄 CLI（StickS3 / WiFi TCP）。

常用：
  python3 esp32_switch.py --tcp 192.168.x.x:8765 tap A
  python3 esp32_switch.py --tcp 192.168.x.x:8765 tap A,B
  python3 esp32_switch.py --tcp 192.168.x.x:8765 hold ZR 1.5
  python3 esp32_switch.py --tcp 192.168.x.x:8765 test
  python3 esp32_switch.py --tcp 192.168.x.x:8765 shell

自动找 IP：
  python3 esp32_switch.py --discover
  python3 esp32_switch.py tap A          # 没给 --tcp 时自动 ARP 找
"""
from __future__ import annotations

import argparse
import os
import re
import shlex
import socket
import subprocess
import sys
import time
from pathlib import Path

from gamepad import (
    BUTTONS, DEFAULT_PORT, WAKE, Controller, SerialLink, TcpLink,
)

ESP_MAC_PREFIX = os.environ.get("STICKS3_MAC_PREFIX", "")  # optional, e.g. 14:c1:9f
LAST_IP = Path(__file__).with_name(".last_ip")


def save_ip(ip: str):
    try:
        LAST_IP.write_text(ip.strip() + "\n", encoding="utf-8")
    except OSError:
        pass


def load_ip() -> str | None:
    try:
        ip = LAST_IP.read_text(encoding="utf-8").strip()
        return ip or None
    except OSError:
        return None


def reachable(ip: str, port: int = DEFAULT_PORT, timeout: float = 0.6) -> bool:
    try:
        with socket.create_connection((ip, int(port)), timeout=timeout):
            return True
    except OSError:
        return False


def discover_ip(mac_prefix: str = ESP_MAC_PREFIX) -> str | None:
    ip = load_ip()
    if ip and reachable(ip):
        return ip
    if not mac_prefix:
        return None
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True, timeout=3).stdout
    except Exception:
        return None
    for line in out.splitlines():
        if mac_prefix in line.lower():
            m = re.search(r"\((\d+\.\d+\.\d+\.\d+)\)", line)
            if m:
                return m.group(1)
    return None


class DryLink:
    def send(self, data: bytes):
        print("TX", data.hex(" "))

    def close(self):
        pass


def parse_host_port(value: str) -> tuple[str, int]:
    host, _, port = value.rpartition(":")
    if host and port.isdigit():
        return host, int(port)
    return value, DEFAULT_PORT


def make_link(args):
    if args.dry_run:
        return DryLink()
    if args.tcp:
        host, port = parse_host_port(args.tcp)
        link = TcpLink(host, port)
        save_ip(host)
        return link
    if args.port:
        return SerialLink(args.port, args.baud)
    ip = discover_ip()
    if ip:
        print(f"[discover] {ip}:{DEFAULT_PORT}", file=sys.stderr)
        return TcpLink(ip, DEFAULT_PORT)
    sys.exit("找不到手柄：用 --tcp IP:8765，或 --port /dev/cu.usbserial-XXXX，或 --discover")


def cmd_shell(ctrl: Controller):
    print("命令：tap A / tap A,B / press ZR / release ZR / hold ZR 1.5")
    print("      stick left 1024 2048 / stick 1024 2048 / reset / test / imu 0 4096 0 0 0 0 / quit")
    while True:
        try:
            line = input("switch> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not line:
            continue
        try:
            parts = shlex.split(line)
        except ValueError as e:
            print("解析失败：", e)
            continue
        cmd, rest = parts[0].lower(), parts[1:]
        try:
            if cmd in ("quit", "exit", "q"):
                break
            elif cmd == "tap":
                ctrl.tap(rest, 0.08)
            elif cmd == "combo":
                ctrl.combo(rest, 0.15)
            elif cmd == "press":
                ctrl.press(rest)
            elif cmd == "release":
                ctrl.release(rest)
            elif cmd == "hold":
                if len(rest) < 1:
                    print("hold ZR [秒]")
                    continue
                ctrl.hold(rest[0], float(rest[1]) if len(rest) > 1 else 1.0)
            elif cmd == "stick":
                if rest and rest[0].lower() in ("left", "right"):
                    side, nums = rest[0].lower(), [int(x) for x in rest[1:]]
                    if len(nums) != 2:
                        print("stick left x y")
                        continue
                    ctrl.stick(**{side: (nums[0], nums[1])})
                else:
                    nums = [int(x) for x in rest]
                    if len(nums) == 2:
                        ctrl.stick(left=(nums[0], nums[1]), right=(nums[0], nums[1]))
                    elif len(nums) == 4:
                        ctrl.stick(left=(nums[0], nums[1]), right=(nums[2], nums[3]))
                    else:
                        print("stick [left|right] x y  或  lx ly rx ry")
            elif cmd == "reset":
                ctrl.reset()
            elif cmd == "test":
                ctrl.test(include_home="--home" in rest)
            elif cmd == "imu":
                nums = [int(x) for x in rest]
                if len(nums) == 6:
                    ctrl.set_imu(tuple(nums[:3]), tuple(nums[3:]))
                else:
                    print("imu accX accY accZ gyroX gyroY gyroZ")
            elif cmd == "help":
                print("tap/press/release/hold/stick/reset/test/imu/quit")
            else:
                print("未知命令：", cmd)
        except Exception as e:
            print("错误：", e)


def main():
    ap = argparse.ArgumentParser(description="Switch Pro 有线手柄 CLI")
    ap.add_argument("--tcp", help="WiFi TCP，例如 192.168.x.x:8765")
    ap.add_argument("--port", help="串口，例如 /dev/cu.usbserial-XXXX")
    ap.add_argument("--baud", type=int, default=3_000_000)
    ap.add_argument("--dry-run", action="store_true", help="只打印包，不连设备")
    ap.add_argument("--discover", action="store_true", help="用 ARP 找 StickS3 的 IP")
    ap.add_argument("--list", action="store_true", help="列出串口 + ARP IP")
    ap.add_argument("--hold", type=float, default=0.08, help="tap 按住秒数")
    ap.add_argument("--gap", type=float, default=0.12, help="序列/自检的间隔")
    ap.add_argument("--seconds", type=float, default=1.0, help="hold 动作的秒数")
    ap.add_argument("--include-home", action="store_true", help="test 时包含 HOME（会回主菜单）")
    ap.add_argument("--include-capture", action="store_true", help="test 时包含 CAPTURE")
    ap.add_argument("action", nargs="?", default="",
                    help="tap/press/release/combo/hold/stick/reset/test/sequence/shell/wake/imu/buttons")
    ap.add_argument("args", nargs="*", default=[])
    args = ap.parse_args()

    if args.list:
        try:
            from serial.tools import list_ports
            for p in list_ports.comports():
                print(f"{p.device}\t{p.description}")
        except ImportError:
            print("缺 pyserial：python3 -m pip install pyserial", file=sys.stderr)
        ip = discover_ip()
        print(f"ARP IP: {ip or '未找到'}")
        return

    if args.discover:
        ip = discover_ip()
        print(ip or "未找到（先确认 StickS3 已连 WiFi）")
        return

    if not args.action:
        ap.print_help()
        return

    action = args.action.lower()
    if action == "buttons":
        print(" ".join(sorted(BUTTONS)))
        return
    ctrl = Controller(make_link(args))

    try:
        if action == "tap":
            ctrl.tap(args.args, args.hold)
        elif action == "combo":
            ctrl.combo(args.args, max(args.hold, 0.15))
        elif action == "press":
            if not args.args:
                sys.exit("press 需要按键，例如 press ZR")
            ctrl.press(args.args)
            print(f"按住 {args.seconds}s ...")
            time.sleep(max(0.0, args.seconds))
            ctrl.release(args.args)
        elif action == "release":
            ctrl.release(args.args)
        elif action == "hold":
            if not args.args:
                sys.exit("hold 需要按键，例如 hold ZR 1.5")
            ctrl.hold(args.args[0], args.seconds)
        elif action == "stick":
            if args.args and args.args[0].lower() in ("left", "right"):
                side, nums = args.args[0].lower(), [int(x) for x in args.args[1:]]
                if len(nums) != 2:
                    sys.exit("stick left x y")
                ctrl.stick(**{side: (nums[0], nums[1])})
            else:
                nums = [int(x) for x in args.args]
                if len(nums) == 2:
                    ctrl.stick(left=(nums[0], nums[1]), right=(nums[0], nums[1]))
                elif len(nums) == 4:
                    ctrl.stick(left=(nums[0], nums[1]), right=(nums[2], nums[3]))
                else:
                    sys.exit("stick [left|right] x y  或  lx ly rx ry")
        elif action == "reset":
            ctrl.reset()
        elif action == "test":
            ctrl.test(args.include_home, args.include_capture, args.hold, args.gap)
        elif action == "sequence":
            spec = " ".join(args.args)
            if not spec:
                sys.exit("sequence 需要序列，例如 \"A:0.1,wait:0.3,DOWN:0.1\"")
            ctrl.sequence(spec, args.hold, args.gap)
        elif action == "imu":
            nums = [int(x) for x in args.args]
            if len(nums) != 6:
                sys.exit("imu accX accY accZ gyroX gyroY gyroZ")
            ctrl.set_imu(tuple(nums[:3]), tuple(nums[3:]))
        elif action == "wake":
            ctrl.link.send(WAKE)
            print("wake 已发送（当前固件未处理 0x04，可能无效果）")
        elif action == "shell":
            cmd_shell(ctrl)
        else:
            ap.print_help()
    finally:
        ctrl.close()


if __name__ == "__main__":
    main()
