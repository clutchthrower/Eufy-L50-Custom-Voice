# Voice Pack Prompts

This directory contains example prompt maps for building custom Eufy L50 voice packs.

## Format

Each prompt map is a JSON file mapping audio file keys to either:
- A text string to be synthesized with Piper TTS
- `"[CHIME]"` — keep the original chime from a stock voice pack (see below)

```json
{
  "A0000": "[CHIME]",
  "A0032": "Starting auto cleaning.",
  "A0040": "Cleaning complete. Returning to dock."
}
```

The key is the audio filename without `.mp3` (e.g. `A0032` → `A0032.mp3`).
See [`docs/voice_pack_format.md`](../../docs/voice_pack_format.md) for the complete
list of all 86 files and what each one says.

## Available Prompts

| File | Character | Description |
|------|-----------|-------------|
| `data_star_trek.json` | Lt. Cmdr. Data (Star Trek: TNG) | Formal, precise android speech patterns. Generated with `en_US-data_7024-medium` Piper voice. |

## Chime Files

Five audio files are non-speech tones (startup, shutdown, alert, notification, confirm).
These are marked `[CHIME]` in the prompt map. You have two options:

1. **Copy from a stock pack** (recommended): Extract an official voice pack ZIP from the
   Eufy cloud API and copy `en_us_female/main/A0000.mp3` etc. into your pack.

2. **Provide your own**: Drop in any 16kHz mono 16kbps MP3 files with the correct names.

## Creating Your Own Prompt Map

1. Copy `data_star_trek.json` to a new file (e.g. `my_custom_voice.json`)
2. Replace each text string with your own dialog — keep the same tone/intent per line
3. Leave `[CHIME]` on the five chime files unless you're replacing them too
4. Run `build_voice_pack.py` with `--prompts examples/prompts/my_custom_voice.json`

## Tips for Good Results

- Keep phrases **short and natural** — the vacuum has limited speaker volume
- Match the **emotional register** of the original (errors should sound urgent, etc.)
- Test with a few phrases before generating all 86 — Piper voice quality varies by model
- The `en_US-data_7024-medium` model is available from
  [piper-voices](https://github.com/rhasspy/piper/releases) — download both
  the `.onnx` and `.onnx.json` files
