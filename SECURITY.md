# Security

This is a local-network tool. The TCP server on port 8765 has **no
authentication** and accepts input packets from anyone who can reach it.

- Use it only on a trusted LAN.
- Do not expose 8765 to the internet.
- Wi-Fi credentials are stored in `firmware/src/wifi_secrets.h`, which is
  gitignored. Never commit that file.
- The HID device can control a console; treat physical/USB access accordingly.

Report security issues privately to the maintainer rather than opening a public
issue with exploit details.
