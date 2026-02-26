# Eufy L50 Custom Voice Pack

Replace your Eufy L50 robot vacuum's voice with any Piper TTS voice — or
Lieutenant Commander Data from Star Trek: The Next Generation.

This repo documents the reverse-engineered protocol for pushing custom voice packs
to the Eufy L50 (model T2265) via its Tuya local control interface.

**Confirmed working on:** Eufy L50 / T2265
**May work on:** Other Eufy robots that use Tuya DPS 162 (`ecl_set_language`)


https://github.com/user-attachments/assets/40e11f35-7583-41a7-9b09-f9201baddec1


> *"I have found that while my internal processors are capable of 60 trillion operations
> per second, my primary purpose at this moment is the eradication of feline dander and
> localized debris. It is... a curious endeavor."*

---

## How It Works

The Eufy app uses the [Tuya local protocol](https://github.com/jasonacox/tinytuya)
to communicate with the vacuum over your local network. When you change the voice
in the app, it sends **DPS 162** — a write-only datapoint containing a
base64-encoded protobuf that tells the vacuum:

1. Which voice pack ID to install
2. A URL to download the ZIP from
3. The MD5 and size of the ZIP for verification

We reverse-engineered this protobuf format by capturing traffic with a rogue router
and a `tcpdump` session, then decrypting the AES-encrypted Tuya packets.

The vacuum accepts plain **HTTP** from any server on your local network.

---

## Demo

> *"I am commencing primary cleaning protocols."*
> *"The assigned task is complete. I am returning to the docking station for maintenance."*
> *"Power levels are critical. Initiating emergency shutdown to protect my positronic brain. Please provide a charge."*

[`examples/prompts/data_star_trek.json`](examples/prompts/data_star_trek.json) contains
all 86 prompts rewritten in Data's speech patterns, ready to synthesize with the
`en_US-data_7024-medium` Piper voice.

---

## Prerequisites

- Python 3.10+
- `ffmpeg` installed (`apt install ffmpeg` or `brew install ffmpeg`)
- Your vacuum on your local network
- Your vacuum's **device ID** and **local key** (see [Getting Credentials](docs/getting_credentials.md))
- A Piper TTS voice model (`.onnx` + `.onnx.json` files)
  — download from [piper-voices releases](https://github.com/rhasspy/piper/releases)
- A stock Eufy voice pack ZIP (for the 5 chime/tone files)
  — download via the [voicePackage API](docs/eufy_api.md)

```bash
pip install -r requirements.txt
```

---

## Quick Start

### 1. Get your device credentials

See [docs/getting_credentials.md](docs/getting_credentials.md).

```
Device ID : ebb88d67eea31712ealsqy  ← yours will be different
Local key : (16 characters)
Vacuum IP : 192.168.1.x  (check your router's DHCP table)
```

### 2. Download a stock voice pack (for chime files)

```bash
# Get your API token first (see docs/eufy_api.md)
curl -s "https://api.eufylife.com/v1/resource/voicePackage?device_id=YOUR_DEVICE_ID" \
  -H "Authorization: YOUR_TOKEN" | python3 -m json.tool

# Download the female pack (ID 501) for its chime files
wget "https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/501_13.zip" -O stock_female.zip
unzip stock_female.zip -d stock_female/
```

### 3. Build the voice pack

```bash
python3 build_voice_pack.py \
    --voice-model /path/to/en_US-data_7024-medium.onnx \
    --prompts examples/prompts/data_star_trek.json \
    --chime-src stock_female/en_us_female/main \
    --out-dir /tmp/my_voice \
    --pack-id 502 \
    --pack-version 16 \
    --server-ip 192.168.1.100
```

This synthesizes all 81 speech prompts with Piper (~5–10 minutes depending on hardware),
copies the 5 chime files, and packages everything into `/tmp/my_voice/en_us_male.zip`.

At the end it prints the exact `send_voice_pack.py` command to run.

### 4. Serve the ZIP over HTTP

The vacuum downloads the ZIP over plain HTTP. Serve it from the same machine
(must be reachable from the vacuum's subnet):

```bash
cd /tmp/my_voice && sudo python3 -m http.server 80
```

> Use port 80 — the vacuum does not connect to non-standard ports.

### 5. Push to the vacuum

```bash
python3 send_voice_pack.py \
    --device-id YOUR_DEVICE_ID \
    --local-key YOUR_LOCAL_KEY \
    --ip 192.168.1.X \
    --url http://192.168.1.100/en_us_male.zip \
    --md5 c808f5460f6663f467af482bc94dc34f \
    --size 748473 \
    --set-id 502 \
    --version 16
```

The vacuum will download the ZIP immediately. Press **Start/Pause** to hear the
new voice.

---

## Updating / Re-installing

The vacuum won't re-download the same version. Each time you resend:

1. Bump `--pack-version` by at least 1
2. Update `config.yaml` in the ZIP with the new version
3. Recalculate MD5 and size

Or just re-run `build_voice_pack.py` with a higher `--pack-version`.

---

## Making Your Own Voice

1. Copy `examples/prompts/data_star_trek.json` to a new file
2. Replace each text string with your own dialog
3. Keep `[CHIME]` on the 5 chime entries (or replace with your own MP3s)
4. Pass your file to `build_voice_pack.py` with `--prompts`

See [examples/prompts/README.md](examples/prompts/README.md) for guidance.

Any [Piper voice](https://huggingface.co/rhasspy/piper-voices) works.

---

## Reverting to the Official Voice

Use the Eufy app to switch voices — it will push an official DPS 162 pointing
back to a CloudFront URL. Or push it manually:

```bash
# Switch back to official female voice (re-downloads from Eufy's servers)
python3 send_voice_pack.py \
    --device-id YOUR_DEVICE_ID \
    --local-key YOUR_LOCAL_KEY \
    --ip 192.168.1.X \
    --url https://d3pkbgk01oouhl.cloudfront.net/upload_file/prod/501_13.zip \
    --md5 <md5 from voicePackage API> \
    --size <size from voicePackage API> \
    --set-id 501 \
    --version 13
```

---

## Docs

| Document | Contents |
|----------|----------|
| [docs/dps162_protocol.md](docs/dps162_protocol.md) | Full DPS 162 protobuf format, encoder, decoder, captured examples |
| [docs/voice_pack_format.md](docs/voice_pack_format.md) | ZIP structure, config.yaml format, all 86 audio files |
| [docs/eufy_api.md](docs/eufy_api.md) | Eufy cloud API: login, voicePackage endpoint, known pack IDs |
| [docs/getting_credentials.md](docs/getting_credentials.md) | How to get device ID and local key |
| [docs/network_setup.md](docs/network_setup.md) | Rogue router capture methodology (research, not required for end users) |

---

## Notes

- Installing a custom pack under ID 502 makes the Eufy app show "Male Voice" as
  selected — the audio content is your custom files. Switching to "Female Voice"
  in the app restores the official female pack from Eufy's servers.

- The vacuum's local key changes if it is factory reset or re-paired. Re-run
  `eufy-clean-local-key-grabber` if you get auth errors.

- The vacuum appears to validate the voice pack ID against a known list. Using
  an ID outside the official range (e.g. 599) results in a silent failure.
  Always use 501 or 502.
