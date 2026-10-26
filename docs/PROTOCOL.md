# Control protocol

Wi‑Fi TCP, default port **8765**. One packet = 49 bytes:

```
AA 55 | cmd | payload (45) | XOR
```

- `AA 55`: magic
- `cmd`: `0x00` = input report (only command implemented)
- payload: 45-byte Switch Pro input report
- XOR: XOR of `cmd` + payload (all bytes from offset 2 to 47)

## 45-byte report

| offset | bytes | meaning |
|---:|---:|---|
| 0 | 1 | buttons byte 0 |
| 1 | 1 | buttons byte 1 |
| 2 | 1 | buttons byte 2 |
| 3 | 3 | left stick (12-bit x/y packed) |
| 6 | 3 | right stick (12-bit x/y packed) |
| 9 | 36 | 3 × IMU sample (12 bytes each) |

### Buttons

Byte 0:

| bit | button |
|---:|---|
| 0 | Y |
| 1 | X |
| 2 | B |
| 3 | A |
| 4 | SR |
| 5 | SL |
| 6 | R |
| 7 | ZR |

Byte 1:

| bit | button |
|---:|---|
| 0 | Minus |
| 1 | Plus |
| 2 | ThumbR |
| 3 | ThumbL |
| 4 | Home |
| 5 | Capture |
| 7 | chargingGrip (always 1) |

Byte 2:

| bit | button |
|---:|---|
| 0 | Down |
| 1 | Up |
| 2 | Right |
| 3 | Left |
| 4 | LeftSL (always 1) |
| 5 | LeftSR (always 1) |
| 6 | L |
| 7 | ZL |

### Sticks

12-bit, `0..4095`, center `2048`:

```text
b0 =  x & 0xFF
b1 = ((x >> 8) & 0x0F) | ((y & 0x0F) << 4)
b2 = (y >> 4) & 0xFF
```

### IMU

Three samples, 12 bytes each: 3 × int16 accelerometer + 3 × int16 gyroscope,
little-endian. The host sends fixed gravity by default; the firmware copies the
bytes as-is.

## Python example

```python
import socket

def stick(x, y):
    return bytes([x & 0xFF, ((x >> 8) & 0xF) | ((y & 0xF) << 4), (y >> 4) & 0xFF])

report = bytearray(45)
report[0] = 1 << 3              # A
report[1] = 1 << 7              # chargingGrip
report[2] = (1 << 4) | (1 << 5) # LeftSL / LeftSR
report[3:6] = stick(2048, 2048)
report[6:9] = stick(2048, 2048)
report[9:] = bytes(36)
chk = 0
for b in report:
    chk ^= b
pkt = b"\xAA\x55\x00" + report + bytes([chk])

s = socket.create_connection(("192.168.1.50", 8765))
s.sendall(pkt)
s.close()
```

The firmware releases all inputs 2 seconds after the last packet, so a one-shot
`tap` should send press and release packets (see `host/gamepad.py`).

## Not implemented

- Rumble: the 45-byte UART-style report has no rumble field.
- Real IMU streaming: host can set values, but no motion source.
- Wake command `AA 55 04 00 04`: ignored by this firmware.
