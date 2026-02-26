# Research Network Setup — Rogue Router Traffic Capture

This document describes the network topology used to capture and decrypt the Tuya
local protocol traffic between the Eufy app and the L50 vacuum. This was how
we reverse-engineered DPS 162.

**You do NOT need this setup to install a custom voice pack.** This is documented
for researchers who want to extend this work or capture traffic for other DPS values.

---

## Why a Rogue Router?

The Eufy L50 communicates with the Eufy app over the Tuya v3.3 local protocol,
which uses AES-ECB encryption. To capture and decrypt this traffic we needed:

1. The vacuum and the phone on the same network (so we could capture their TCP traffic)
2. The device's local key (for AES decryption)
3. A way to capture raw packets without being on the same machine as either endpoint

A DD-WRT router acting as a transparent bridge between the vacuum and the
internet solved all three: the vacuum and phone were on its LAN, and we could
run `tcpdump` on the router's bridge interface.

---

## Topology

```
[Eufy L50 vacuum]
    192.168.1.80
         │
         │ (vacuum's Wi-Fi)
         ▼
[DD-WRT rogue router]
    LAN: 192.168.1.1  (br0)
    WAN: 10.42.0.47   (vlan2/eno1 side)
         │
         │ (Ethernet cable)
         ▼
[Ubuntu PC — eno1]
    10.42.0.1
    (IP forwarding enabled)
         │
         │ (Wi-Fi / USB-Ethernet)
         ▼
[Real router / internet]
    10.0.0.1
```

The phone was connected to the DD-WRT LAN (192.168.1.x) to trigger voice changes
in the Eufy app. The Ubuntu PC routed internet traffic onward.

---

## Ubuntu PC Setup

### Enable IP forwarding

```bash
sudo sysctl -w net.ipv4.ip_forward=1
```

### Add route to vacuum's subnet

```bash
sudo ip route add 192.168.1.0/24 via 10.42.0.47
```

### Masquerade rules (allow vacuum to reach internet via Ubuntu)

```bash
# Vacuum traffic (192.168.1.x) → internet via Wi-Fi/USB-Ethernet adapter
sudo iptables -t nat -A POSTROUTING -s 192.168.1.0/24 -o enx2c30339fce54 -j MASQUERADE

# DD-WRT WAN traffic (10.42.0.x) → internet
sudo iptables -t nat -A POSTROUTING -s 10.42.0.0/24 -o enx2c30339fce54 -j MASQUERADE
```

Replace `enx2c30339fce54` with your outgoing internet interface (check with `ip link`).

---

## DD-WRT Router Setup

### Switch to Router mode (not Gateway)

In the DD-WRT web interface:
- **Setup → Advanced Routing → Operating Mode**: set to **Router** (not Gateway)

This disables DD-WRT's own NAT, allowing the vacuum's source IP to be visible on
the Ubuntu side.

### Add masquerade for internet access

Via telnet (`telnet 192.168.1.1 23`):

```bash
# Allow vacuum → internet (through Ubuntu's eno1 → real router)
iptables -t nat -A POSTROUTING -o vlan2 -j MASQUERADE

# Allow forwarding between LAN (br0) and WAN (vlan2)
iptables -A FORWARD -i br0 -o vlan2 -j ACCEPT
iptables -A FORWARD -i vlan2 -o br0 -m state --state RELATED,ESTABLISHED -j ACCEPT
```

> **Note:** DD-WRT's iptables rules do not persist across reboots by default.
> Add them to **Administration → Commands → Startup** to make them permanent.

---

## Capturing Traffic

Run `tcpdump` on the DD-WRT LAN bridge to capture all traffic between the vacuum
and the phone. Pipe it out via netcat since DD-WRT has no local storage:

**On Ubuntu (listener):**
```bash
nc -l -p 9999 > capture.pcap
```

**On DD-WRT (via telnet):**
```bash
tcpdump -i br0 -w - 'host 192.168.1.80' | nc 10.42.0.1 9999
```

Stop with Ctrl+C on the DD-WRT side, then Ctrl+C on Ubuntu.

---

## Decrypting Tuya v3.3 Packets

With the device's local key (see `docs/getting_credentials.md`), decrypt captured
packets using tinytuya's built-in tools or this script:

```python
from Crypto.Cipher import AES
import struct

LOCAL_KEY = b'YOUR_LOCAL_KEY_HERE'  # 16 bytes

def decrypt_payload(encrypted: bytes) -> bytes:
    """Decrypt a Tuya v3.3 AES-ECB payload."""
    # Strip optional "3.3" 15-byte version prefix
    if encrypted[:3] == b'3.3':
        encrypted = encrypted[15:]
    cipher = AES.new(LOCAL_KEY, AES.MODE_ECB)
    decrypted = cipher.decrypt(encrypted)
    # Remove PKCS7 padding
    pad = decrypted[-1]
    if pad < 16:
        decrypted = decrypted[:-pad]
    return decrypted

def parse_tuya_packet(raw: bytes) -> dict | None:
    """Parse a raw Tuya v3.3 frame."""
    if len(raw) < 20 or raw[:4] != b'\x00\x00\x55\xaa':
        return None
    seq     = struct.unpack('>I', raw[4:8])[0]
    cmd     = struct.unpack('>I', raw[8:12])[0]
    pay_len = struct.unpack('>I', raw[12:16])[0]
    payload = raw[20:20 + pay_len - 8]
    if payload:
        try:
            payload = decrypt_payload(payload)
        except Exception:
            pass
    return {'seq': seq, 'cmd': cmd, 'payload': payload}
```

Or use tinytuya's `--verbose` debug mode which decrypts automatically when the
local key is known.

---

## Alternative: mitmproxy for HTTPS traffic

For the Eufy app's HTTPS calls to the cloud API, we used a separate approach:

1. Set an ADB proxy on the Android phone:
   ```bash
   adb shell settings put global http_proxy 10.0.0.37:8888
   ```
2. Run `mitmproxy` on port 8888 with a trusted CA cert installed on the phone.
3. **To remove the proxy** (important — deleting the setting breaks Android networking):
   ```bash
   adb shell settings put global http_proxy :0
   ```

This is how we captured the `voicePackage` API response and Eufy login endpoints.
