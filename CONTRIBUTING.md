# Contributing

1. Fork, create a branch, keep changes focused.
2. Firmware: `cd firmware && pio run -e sticks3`.
3. Host: `cd host && python3 -m unittest discover -s tests`.
4. Don't commit `firmware/src/wifi_secrets.h`, `.pio/`, or prebuilt binaries.
5. If you change the HID descriptor/driver, note the Switch model and firmware
   version you tested.

Bug reports are most useful with:

- board (StickS3 / Cardputer / CoreS3)
- Switch model + firmware
- serial log
- whether HID enumerates as `057E:2009`
