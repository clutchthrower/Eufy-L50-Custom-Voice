# DPS 162 Protocol — Reverse Engineering Notes

`ecl_set_language` (DPS 162) is the Tuya datapoint used by the Eufy L50 (T2265) to receive
voice pack update instructions. When the Eufy app changes the robot's voice, it sends this
DPS with a protobuf payload that tells the vacuum what to download and install.

## How We Captured It

1. Connected the vacuum to a DD-WRT "rogue router" whose WAN port was bridged through a
   Linux PC running `tcpdump`.
2. Used the Eufy app on a phone (connected to the rogue router) to trigger a voice change.
3. Captured raw TCP traffic on the DD-WRT LAN bridge (`tcpdump -i br0`).
4. Decrypted the Tuya v3.3 AES-ECB packets using the device's local key (obtained via
   [eufy-clean-local-key-grabber](https://github.com/martinber/eufy-clean-local-key-grabber)).
5. Decoded the protobuf payload manually.

See `docs/network_setup.md` for the full capture methodology.

---

## Tuya v3.3 Packet Structure

The DPS 162 value is transmitted inside a standard Tuya v3.3 local protocol frame:

```
Offset  Size  Field
------  ----  -----
0       4     Magic: 0x000055AA
4       4     Sequence number (big-endian uint32)
8       4     Command (big-endian uint32)
               0x07 = CONTROL (set DPS)
               0x0A = CONTROL_NEW
12      4     Payload length (includes CRC + suffix)
16      N     AES-ECB encrypted payload (with optional "3.3" 15-byte prefix)
-8      4     CRC32
-4      4     Suffix: 0x0000AA55
```

The payload, once decrypted, is a JSON string like:
```json
{"devId":"YOUR_DEVICE_ID","uid":"YOUR_DEVICE_ID","t":1234567890,"dps":{"162":"BASE64_HERE"}}
```

---

## DPS 162 Value Format

The DPS 162 value is a **base64-encoded protobuf binary**:

```
base64( varint(len(outer_message)) + outer_message )
```

### Outer message fields

| Field | Type | Name | Description |
|-------|------|------|-------------|
| 1 | length-delimited (nested message) | `voice_info` | The inner message |
| 2 | length-delimited (empty bytes) | *(padding)* | Always empty `\x00` length field |

### Inner message fields (field 1 of outer)

| Field | Type | Name | Description |
|-------|------|------|-------------|
| 1 | varint | `set_id` | Voice pack ID to install (e.g. `502`) |
| 2 | string | `url` | HTTP/HTTPS URL to download the ZIP from |
| 3 | string | `md5` | Hex MD5 of the ZIP file |
| 4 | varint | `version` | Version number — must be higher than currently installed |
| 5 | varint | `size` | ZIP file size in bytes |

> **Critical:** The vacuum validates `set_id` against its list of known voice packs.
> Using an unknown ID (e.g. a custom number outside the official range) results in
> `state=3` (failure) in the response. Use a real ID like `501` or `502`.

---

## Python Encoder

```python
import base64

def encode_varint(v):
    out = []
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b | 0x80 if v else b)
        if not v:
            break
    return bytes(out)

def encode_field_varint(field_num, value):
    return encode_varint((field_num << 3) | 0) + encode_varint(value)

def encode_field_string(field_num, value):
    if isinstance(value, str):
        value = value.encode()
    return encode_varint((field_num << 3) | 2) + encode_varint(len(value)) + value

def build_dps162(set_id, url, md5, version, size):
    inner  = encode_field_varint(1, set_id)
    inner += encode_field_string(2, url)
    inner += encode_field_string(3, md5)
    inner += encode_field_varint(4, version)
    inner += encode_field_varint(5, size)
    outer  = encode_field_string(1, inner)
    outer += encode_field_string(2, b'')
    return base64.b64encode(encode_varint(len(outer)) + outer).decode()
```

---

## Captured Examples

### Example 1 — Switch to female voice (ID 501, v13)

Captured from the Eufy app switching to `en_us_female`:

```
Base64: UApKCPUDEkBodHRwczovL2QzcGtiZ2swMW9vdWhsLmNsb3VkZnJvbnQubmV0L3VwbG9hZF9maWxlL3Byb2QvNTAxXzEzLnppcBogeHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHgYDSCZjzcSAA==
```

Decoded inner message:
```
field 1 (set_id)  = 501
field 2 (url)     = https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/501_13.zip
field 3 (md5)     = <hex md5 of the official female pack>
field 4 (version) = 13
field 5 (size)    = <size in bytes>
```

### Example 2 — Switch to male voice (ID 502, v15)

```
Base64: UApMCPYDEkBodHRwczovL2QzcGtiZ2swMW9vdWhsLmNsb3VkZnJvbnQubmV0L3VwbG9hZF9maWxlL3Byb2QvNTAyXzE1LnppcBogeXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXl5eXkYDyC4kz0SAA==
```

Decoded inner message:
```
field 1 (set_id)  = 502
field 2 (url)     = https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/502_15.zip
field 3 (md5)     = <hex md5 of the official male pack>
field 4 (version) = 15
field 5 (size)    = <size in bytes>
```

> Note: The official packs are served over HTTPS from CloudFront. However, the vacuum
> also accepts plain HTTP from any server — HTTPS is not required for custom packs.

---

## Response Format

After receiving DPS 162, the vacuum responds with its own DPS 162 status update.
The response uses the **same base64-protobuf encoding**, but with different semantics:

| Field | Type | Name | Description |
|-------|------|------|-------------|
| 1 | varint | `status` | 2 = OK |
| 2 | varint | `installed_id` | Currently installed voice pack ID |
| 3 | varint | `installed_version` | Currently installed version |
| 4 | varint | `target_id` | ID that was requested |
| 5 | varint | `state` | `2` = success/installed, `3` = failed (unknown ID) |

### Example: successful custom pack install

After sending our custom pack with `set_id=502, version=16`:
```
Raw:    0c080210f603181020f6032802
Base64: DAgCEPYDGBAg9gMoAg==

field 1 (status)            = 2
field 2 (installed_id)      = 502
field 3 (installed_version) = 16
field 4 (target_id)         = 502
field 5 (state)             = 2  ← SUCCESS
```

### Example: failed (unknown ID)

When we first tried with `set_id=599` (a made-up ID):
```
Raw:    0c080210f603180120d7042803
Base64: DAgCEPYDGAEg1wQoAw==

field 1 (status)            = 2
field 2 (installed_id)      = 502  (previous pack)
field 3 (installed_version) = 1
field 4 (target_id)         = 599  ← our made-up ID
field 5 (state)             = 3    ← FAILED (unknown ID)
```

---

## Python Decoder

```python
import base64

def decode_dps162(b64_value):
    data = base64.b64decode(b64_value)

    def read_varint(data, pos):
        result, shift = 0, 0
        while True:
            b = data[pos]; pos += 1
            result |= (b & 0x7F) << shift
            if not (b & 0x80):
                break
            shift += 7
        return result, pos

    length, pos = read_varint(data, 0)
    inner = data[pos:]
    fields = {}
    pos2 = 0
    while pos2 < len(inner):
        tag, pos2 = read_varint(inner, pos2)
        fn, wt = tag >> 3, tag & 7
        if wt == 0:
            v, pos2 = read_varint(inner, pos2)
            fields[fn] = v
        elif wt == 2:
            l, pos2 = read_varint(inner, pos2)
            fields[fn] = inner[pos2:pos2+l]
            pos2 += l
    return fields
```
