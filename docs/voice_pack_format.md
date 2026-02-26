# Voice Pack Format

This document describes the exact format of an Eufy L50 voice pack ZIP file,
reverse-engineered from the official packs downloaded via the Eufy cloud API.

---

## ZIP Structure

```
en_us_male/
├── config.yaml
└── main/
    ├── A0000.mp3
    ├── A0001.mp3
    ├── A0002.mp3
    ... (86 files total)
    └── A7052.mp3
```

The top-level folder name must match the voice "type":
- `en_us_female/` for voice ID 501
- `en_us_male/`   for voice ID 502

The vacuum appears to read the folder name as part of pack identification.
Using a mismatched or arbitrary folder name may cause install failures.

---

## config.yaml

Located at `<voice_name>/config.yaml`. Exact format:

```yaml
id: 502
version: 16
```

- `id` must be a **known voice pack ID** (see Known Voice Packs below).
  The vacuum validates this against its internal list — unknown IDs result in `state=3` (failure).
- `version` must be **higher than the currently installed version** for the vacuum to re-download.
  If the version is the same or lower, the vacuum ignores the command.

---

## MP3 File Specifications

All audio files must be:

| Parameter  | Value      |
|------------|------------|
| Format     | MP3        |
| Sample rate | 16,000 Hz |
| Channels   | Mono (1)   |
| Bit rate   | 16 kbps CBR |

Convert with ffmpeg:
```bash
ffmpeg -i input.wav -ar 16000 -ac 1 -b:a 16k output.mp3
```

---

## File List (all 86 files)

Five files are **chimes** (non-speech tones). Keep these from a stock pack if you want
the original sounds, or replace them with your own audio.

| File     | Type   | Description |
|----------|--------|-------------|
| A0000.mp3 | CHIME | Power on / startup tone |
| A0001.mp3 | CHIME | Power off tone |
| A0002.mp3 | CHIME | Error / alert tone |
| A0003.mp3 | CHIME | Notification tone |
| A0010.mp3 | SPEECH | Firmware update started |
| A0011.mp3 | SPEECH | Firmware update complete |
| A0012.mp3 | SPEECH | Update downloading |
| A0013.mp3 | SPEECH | Voice pack updated |
| A0014.mp3 | CHIME | Confirmation tone |
| A0020.mp3 | SPEECH | Wi-Fi disconnected |
| A0021.mp3 | SPEECH | Connecting to Wi-Fi |
| A0022.mp3 | SPEECH | Wi-Fi connected |
| A0023.mp3 | SPEECH | Wi-Fi not found |
| A0024.mp3 | SPEECH | Wrong Wi-Fi password |
| A0025.mp3 | SPEECH | Wi-Fi connected, no internet |
| A0030.mp3 | SPEECH | Searching for location (mapping) |
| A0031.mp3 | SPEECH | Location found |
| A0032.mp3 | SPEECH | Start auto cleaning |
| A0033.mp3 | SPEECH | Start spot cleaning |
| A0034.mp3 | SPEECH | Start room cleaning |
| A0040.mp3 | SPEECH | Cleaning complete, returning to dock |
| A0041.mp3 | SPEECH | Emptying dustbin (auto-empty) |
| A0044.mp3 | SPEECH | Charging |
| A0045.mp3 | SPEECH | Cleaning complete |
| A0070.mp3 | SPEECH | Paused |
| A0071.mp3 | SPEECH | Resuming |
| A0073.mp3 | SPEECH | Remote control started |
| A0074.mp3 | SPEECH | Remote control ended |
| A0075.mp3 | SPEECH | Returning to dock |
| A0076.mp3 | SPEECH | Too close to dock, move away and try again |
| A0077.mp3 | SPEECH | Move away from dock first |
| A0078.mp3 | SPEECH | Low battery, returning to charge |
| A0079.mp3 | SPEECH | Low battery, going to dock |
| A0080.mp3 | SPEECH | Power off (low battery) |
| A0081.mp3 | SPEECH | Child lock activated |
| A0082.mp3 | SPEECH | Child lock deactivated |
| A0084.mp3 | SPEECH | Charging complete, resuming |
| A0085.mp3 | SPEECH | Starting scheduled cleaning |
| A0086.mp3 | SPEECH | Starting new map |
| A0087.mp3 | SPEECH | Map not ready, try later |
| A0088.mp3 | SPEECH | Child lock active — use charger or app |
| A0091.mp3 | SPEECH | Auto-empty in progress |
| A1010.mp3 | SPEECH | Wheel module error |
| A1013.mp3 | SPEECH | Wheel stuck |
| A2010.mp3 | SPEECH | Suction fan error |
| A2013.mp3 | SPEECH | Suction port blocked |
| A2110.mp3 | SPEECH | Roller brush error |
| A2112.mp3 | SPEECH | Roller brush stuck |
| A2210.mp3 | SPEECH | Side brush error |
| A2213.mp3 | SPEECH | Side brush stuck |
| A2300.mp3 | SPEECH | Dustbin removed |
| A2301.mp3 | SPEECH | Dustbin re-installed |
| A2310.mp3 | SPEECH | Dustbin missing or not installed |
| A2311.mp3 | SPEECH | Dustbin full |
| A3010.mp3 | SPEECH | Water pump error |
| A3013.mp3 | SPEECH | Water tank empty |
| A3100.mp3 | SPEECH | Mop pad removed, entering vacuum-only mode |
| A3101.mp3 | SPEECH | Mop pad installed |
| A4010.mp3 | SPEECH | LiDAR sensor error |
| A4011.mp3 | SPEECH | LiDAR sensor blocked |
| A4012.mp3 | SPEECH | LiDAR sensor stuck |
| A4111.mp3 | SPEECH | Bumper stuck |
| A4130.mp3 | SPEECH | LiDAR cover stuck, please check |
| A5014.mp3 | SPEECH | Power off (critical battery) |
| A5015.mp3 | SPEECH | Too low battery for scheduled clean |
| A5110.mp3 | SPEECH | Wi-Fi/Bluetooth error |
| A5112.mp3 | SPEECH | Dock communication error |
| A6113.mp3 | SPEECH | No dust bag in auto-empty station |
| A6114.mp3 | SPEECH | Auto-empty station fan cooling down |
| A6300.mp3 | SPEECH | Auto-empty cutting hair and emptying |
| A6301.mp3 | SPEECH | Not enough power for auto-empty |
| A6310.mp3 | SPEECH | Auto-empty interrupted |
| A6311.mp3 | SPEECH | Auto-empty internal blockage |
| A7000.mp3 | SPEECH | Obstacle detected |
| A7001.mp3 | SPEECH | Robot stuck |
| A7002.mp3 | SPEECH | Robot lifted off ground |
| A7010.mp3 | SPEECH | Entered no-go zone |
| A7020.mp3 | SPEECH | Lost, starting new map |
| A7021.mp3 | SPEECH | Lost, returning to dock |
| A7031.mp3 | SPEECH | Dock not found, clear dock area |
| A7032.mp3 | SPEECH | Dock not found, going back to start |
| A7033.mp3 | SPEECH | Failed to dock |
| A7034.mp3 | SPEECH | Lost start point, stopping |
| A7050.mp3 | SPEECH | Some areas skipped (inaccessible) |
| A7051.mp3 | SPEECH | Cleaning in progress, can't start scheduled clean |
| A7052.mp3 | SPEECH | Path blocked, can't reach destination |

---

## Known Voice Packs (from voicePackage API)

As of early 2025, the official voice packs for the T2265 are:

| ID  | Folder name    | Description     | Version | Notes |
|-----|----------------|-----------------|---------|-------|
| 501 | en_us_female   | US English, female | 13   | Default |
| 502 | en_us_male     | US English, male   | 15   | |
| *(others)* | | Other languages/regions | | Retrieved from API — see `docs/eufy_api.md` |

To install a custom pack as the "male" voice, use `id: 502` and `version: 16` (or higher).
To install as "female", use `id: 501` and `version: 14` (or higher).

> **Note:** After installing a custom pack under ID 502, the Eufy app may show
> "Male Voice" as selected. The audio content will be your custom files.
> Switching back to Female in the app will restore the official female pack
> (re-downloaded from Eufy's servers).
