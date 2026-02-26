# Getting Your Device Credentials

To push a custom voice pack you need two things:
1. **Device ID** — a unique identifier for your vacuum
2. **Local key** — a 16-byte AES key used for Tuya local protocol encryption

---

## Device ID

### From the Eufy app

1. Open the Eufy app → tap your robot vacuum
2. Tap the **gear icon** (top right) → **Device Info**
3. Look for **Device ID** or **Serial Number** — it's a 21-character alphanumeric string

### From the cloud API

If you have an Eufy account token (see `docs/eufy_api.md`), the device ID appears
as a query parameter in the `voicePackage` API URL you'd construct:
```
?device_id=YOUR_DEVICE_ID_HERE
```

---

## Local Key

The local key is generated when the vacuum connects to your Wi-Fi and pairs with
the Eufy/Tuya cloud. It can change if the vacuum is reset or re-paired.

### Method 1: eufy-clean-local-key-grabber (recommended)

[eufy-clean-local-key-grabber](https://github.com/nickthecook/eufy-clean-local-key-grabber)
authenticates with the Eufy cloud using your account credentials and retrieves
the local key directly.

```bash
git clone https://github.com/nickthecook/eufy-clean-local-key-grabber
cd eufy-clean-local-key-grabber
pip install -r requirements.txt
python3 grab.py YOUR_EMAIL YOUR_PASSWORD
```

It will print your device's local key.

### Method 2: tinytuya wizard

[tinytuya](https://github.com/jasonacox/tinytuya) has a built-in wizard that
scans your network and retrieves keys from the Tuya cloud:

```bash
pip install tinytuya
python3 -m tinytuya wizard
```

Follow the prompts — you'll need a Tuya developer account or your Eufy/Tuya
cloud credentials.

### Method 3: Intercept with mitmproxy

If you have the phone's app traffic intercepted (see `docs/network_setup.md`),
the local key appears in the device sync response from the Eufy cloud API.

---

## Important: Local Key Can Change

The local key is tied to the device's cloud pairing session. It will change if:

- The vacuum is **factory reset**
- The vacuum is **removed and re-added** in the Eufy app
- The vacuum connects to a **new Wi-Fi network** and re-pairs

If `tinytuya` gives error 901 (authentication failed) or similar, the key has
likely changed — re-run `eufy-clean-local-key-grabber` to get the new one.

---

## Verifying Your Credentials

Quick test with tinytuya:

```python
import tinytuya

d = tinytuya.Device(
    dev_id='YOUR_DEVICE_ID',
    address='YOUR_VACUUM_IP',
    local_key='YOUR_LOCAL_KEY',
    version='3.3'
)
print(d.status())
```

A successful response looks like:
```python
{'dps': {'151': True, '158': 'Quiet', '161': 1, '163': 100, ...}}
```

An auth failure will raise an exception or return an error dict.
