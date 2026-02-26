#!/usr/bin/env python3
"""
send_voice_pack.py — Push a custom voice pack to an Eufy L50 (T2265) vacuum.

Builds and sends the DPS 162 (ecl_set_language) protobuf payload over the
Tuya v3.3 local protocol, instructing the vacuum to download and install
a voice pack ZIP from the given URL.

Usage:
    python3 send_voice_pack.py \\
        --device-id YOUR_DEVICE_ID \\
        --local-key YOUR_LOCAL_KEY \\
        --ip 192.168.1.80 \\
        --url http://192.168.1.100/en_us_male.zip \\
        --md5 c808f5460f6663f467af482bc94dc34f \\
        --size 748473 \\
        --set-id 502 \\
        --version 16

See docs/dps162_protocol.md for the full protocol reference.
See docs/getting_credentials.md for how to obtain device-id and local-key.
"""

import argparse
import base64
import sys
import time

try:
    import tinytuya
except ImportError:
    sys.exit("tinytuya not installed. Run: pip install tinytuya")


# Known current versions for official voice packs.
# Your --version must be higher than these to force a re-download.
KNOWN_VERSIONS = {
    501: 13,  # en_us_female
    502: 15,  # en_us_male
}


# ---------------------------------------------------------------------------
# DPS 162 protobuf encoder
# ---------------------------------------------------------------------------

def _encode_varint(v: int) -> bytes:
    out = []
    while True:
        b = v & 0x7F
        v >>= 7
        out.append(b | 0x80 if v else b)
        if not v:
            break
    return bytes(out)


def _encode_field_varint(field_num: int, value: int) -> bytes:
    return _encode_varint((field_num << 3) | 0) + _encode_varint(value)


def _encode_field_string(field_num: int, value: bytes | str) -> bytes:
    if isinstance(value, str):
        value = value.encode()
    return _encode_varint((field_num << 3) | 2) + _encode_varint(len(value)) + value


def build_dps162(set_id: int, url: str, md5: str, version: int, size: int) -> str:
    """
    Encode the DPS 162 payload as base64-protobuf.

    Args:
        set_id:  Voice pack ID to install (e.g. 502). Must be a known Eufy ID.
        url:     HTTP URL the vacuum will download the ZIP from.
        md5:     Hex MD5 of the ZIP file.
        version: Version number — must be higher than currently installed.
        size:    ZIP file size in bytes.

    Returns:
        Base64-encoded protobuf string suitable for DPS 162.
    """
    inner  = _encode_field_varint(1, set_id)
    inner += _encode_field_string(2, url)
    inner += _encode_field_string(3, md5)
    inner += _encode_field_varint(4, version)
    inner += _encode_field_varint(5, size)
    outer  = _encode_field_string(1, inner)
    outer += _encode_field_string(2, b'')
    return base64.b64encode(_encode_varint(len(outer)) + outer).decode()


# ---------------------------------------------------------------------------
# DPS 162 response decoder
# ---------------------------------------------------------------------------

def _read_varint(data: bytes, pos: int) -> tuple[int, int]:
    result, shift = 0, 0
    while True:
        b = data[pos]; pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            break
        shift += 7
    return result, pos


def decode_dps162_response(b64_value: str) -> dict:
    """Decode a DPS 162 response payload from the vacuum."""
    data = base64.b64decode(b64_value)
    length, pos = _read_varint(data, 0)
    inner = data[pos:]
    fields = {}
    pos2 = 0
    while pos2 < len(inner):
        tag, pos2 = _read_varint(inner, pos2)
        fn, wt = tag >> 3, tag & 7
        if wt == 0:
            v, pos2 = _read_varint(inner, pos2)
            fields[fn] = v
        elif wt == 2:
            l, pos2 = _read_varint(inner, pos2)
            fields[fn] = inner[pos2:pos2+l]
            pos2 += l
    return fields


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Push a custom voice pack to an Eufy L50 vacuum via DPS 162.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--device-id',  required=True, help='Tuya device ID')
    parser.add_argument('--local-key',  required=True, help='Tuya local key (16 bytes)')
    parser.add_argument('--ip',         required=True, help='Vacuum IP address')
    parser.add_argument('--url',        required=True, help='HTTP URL to download the ZIP from')
    parser.add_argument('--md5',        required=True, help='Hex MD5 of the ZIP file')
    parser.add_argument('--size',       required=True, type=int, help='ZIP file size in bytes')
    parser.add_argument('--set-id',     required=True, type=int, help='Voice pack ID (e.g. 502 for male)')
    parser.add_argument('--version',    required=True, type=int, help='Version number (must exceed current)')
    parser.add_argument('--port',       default=6668,  type=int, help='Tuya local port (default: 6668)')
    args = parser.parse_args()

    # Warn if version is not high enough
    if args.set_id in KNOWN_VERSIONS and args.version <= KNOWN_VERSIONS[args.set_id]:
        print(f"WARNING: --version {args.version} is not higher than known current version "
              f"{KNOWN_VERSIONS[args.set_id]} for pack ID {args.set_id}. "
              f"The vacuum may ignore this command.", file=sys.stderr)

    payload = build_dps162(args.set_id, args.url, args.md5, args.version, args.size)

    print(f"DPS 162 payload : {payload}")
    print(f"  set_id        : {args.set_id}")
    print(f"  url           : {args.url}")
    print(f"  md5           : {args.md5}")
    print(f"  version       : {args.version}")
    print(f"  size          : {args.size}")
    print(f"\nConnecting to {args.ip}:{args.port} ...")

    d = tinytuya.Device(args.device_id, args.ip, args.local_key, version='3.3')
    d.set_socketPersistent(False)

    print("Sending DPS 162 ...")
    result = d.set_value(162, payload, nowait=False)
    print(f"Raw result      : {result}")

    if result and 'dps' in result and '162' in result['dps']:
        fields = decode_dps162_response(result['dps']['162'])
        state = fields.get(5)
        installed_id = fields.get(2)
        installed_ver = fields.get(3)
        target_id = fields.get(4)

        print(f"\nVacuum response:")
        print(f"  installed_id      : {installed_id}")
        print(f"  installed_version : {installed_ver}")
        print(f"  target_id         : {target_id}")
        print(f"  state             : {state}  {'(SUCCESS)' if state == 2 else '(FAILED — unknown pack ID?)' if state == 3 else ''}")

        if state == 2:
            print("\nSuccess! The vacuum has downloaded and installed the voice pack.")
            print("Press Start/Pause on the vacuum to hear the new voice.")
        elif state == 3:
            print("\nFailed. The vacuum rejected the pack ID.", file=sys.stderr)
            print("Ensure --set-id is a known Eufy voice pack ID (501=female, 502=male).", file=sys.stderr)
    else:
        print("\nNo DPS 162 response received.")
        print("The vacuum may still be downloading — check network traffic if needed.")

    # Brief pause then read status to confirm volume change
    time.sleep(1)
    status = d.status()
    if status and 'dps' in status:
        dps158 = status['dps'].get('158')
        if dps158:
            print(f"\nVolume (DPS 158) is now: {dps158}")


if __name__ == '__main__':
    main()
