#!/usr/bin/env python3
"""
build_voice_pack.py — Build a custom Eufy L50 voice pack ZIP using Piper TTS.

Reads a JSON prompt map (filename → text or "[CHIME]"), synthesizes each text
prompt as a 16kHz mono 16kbps MP3 using Piper, copies chime files from a
stock voice pack, writes config.yaml, and packages everything into a ZIP.

The output ZIP is ready to be served over HTTP and pushed to the vacuum via
send_voice_pack.py.

Usage:
    # Basic (uses defaults)
    python3 build_voice_pack.py --voice-model /path/to/model.onnx

    # Full options
    python3 build_voice_pack.py \\
        --voice-model /path/to/en_US-voice.onnx \\
        --prompts examples/prompts/data_star_trek.json \\
        --chime-src /path/to/stock_pack/en_us_female/main \\
        --out-dir /tmp/my_voice \\
        --pack-id 502 \\
        --pack-version 16

Requirements:
    pip install piper-tts
    apt install ffmpeg  (or brew install ffmpeg)
"""

import argparse
import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import wave
import zipfile

try:
    from piper import PiperVoice
except ImportError:
    sys.exit("piper-tts not installed. Run: pip install piper-tts")


VOICE_PACK_NAMES = {
    501: 'en_us_female',
    502: 'en_us_male',
}


def synthesize_mp3(voice, text: str, out_path: str) -> None:
    """Synthesize text with Piper and save as 16kHz mono 16kbps MP3."""
    chunks = list(voice.synthesize(text))
    if not chunks:
        raise RuntimeError(f"Piper produced no audio for: {text!r}")

    buf = io.BytesIO()
    with wave.open(buf, 'wb') as wf:
        wf.setnchannels(chunks[0].sample_channels)
        wf.setsampwidth(chunks[0].sample_width)
        wf.setframerate(chunks[0].sample_rate)
        for chunk in chunks:
            wf.writeframes(chunk.audio_int16_bytes)

    result = subprocess.run(
        ['ffmpeg', '-y', '-i', 'pipe:0', '-ar', '16000', '-ac', '1', '-b:a', '16k', out_path],
        input=buf.getvalue(),
        capture_output=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f'ffmpeg failed for {out_path}:\n{result.stderr.decode()}')


def main():
    parser = argparse.ArgumentParser(
        description='Build a custom Eufy L50 voice pack ZIP from Piper TTS.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        '--voice-model', required=True,
        help='Path to Piper .onnx model file (e.g. en_US-lessac-medium.onnx)',
    )
    parser.add_argument(
        '--prompts', default='examples/prompts/data_star_trek.json',
        help='Path to JSON prompt map (default: examples/prompts/data_star_trek.json)',
    )
    parser.add_argument(
        '--chime-src', default=None,
        help='Directory containing stock chime MP3s (e.g. en_us_female/main from an official ZIP). '
             'Required if any prompts are marked [CHIME].',
    )
    parser.add_argument(
        '--out-dir', default='/tmp/custom_voice_pack',
        help='Output directory for extracted files and ZIP (default: /tmp/custom_voice_pack)',
    )
    parser.add_argument(
        '--pack-id', type=int, default=502,
        help='Voice pack ID to use (501=female, 502=male). Must match a known Eufy ID. (default: 502)',
    )
    parser.add_argument(
        '--pack-version', type=int, default=16,
        help='Version number. Must be higher than currently installed (502=v15, 501=v13). (default: 16)',
    )
    parser.add_argument(
        '--server-ip', default=None,
        help='Your server IP for the printed URL hint (optional, e.g. 192.168.1.100)',
    )
    args = parser.parse_args()

    # Determine voice/folder name
    voice_name = VOICE_PACK_NAMES.get(args.pack_id, f'custom_{args.pack_id}')

    # Validate chime source
    with open(args.prompts) as f:
        prompts = {k: v for k, v in json.load(f).items() if not k.startswith('_comment')}

    chimes = {k for k, v in prompts.items() if v == '[CHIME]'}
    speech = {k: v for k, v in prompts.items() if v != '[CHIME]'}

    if chimes and not args.chime_src:
        sys.exit(
            f"ERROR: {len(chimes)} prompts are marked [CHIME] but --chime-src was not provided.\n"
            f"Extract an official voice pack ZIP and pass its main/ directory as --chime-src.\n"
            f"Chime files: {', '.join(sorted(chimes))}"
        )

    out_voice_dir = os.path.join(args.out_dir, voice_name)
    os.makedirs(os.path.join(out_voice_dir, 'main'), exist_ok=True)

    # Copy chime files
    if chimes:
        print(f'Copying {len(chimes)} chime files from {args.chime_src}...')
        for code in sorted(chimes):
            src = os.path.join(args.chime_src, f'{code}.mp3')
            dst = os.path.join(out_voice_dir, 'main', f'{code}.mp3')
            if not os.path.exists(src):
                sys.exit(f"ERROR: Chime file not found: {src}")
            shutil.copy2(src, dst)
            print(f'  [CHIME] {code}')

    # Synthesize speech files
    print(f'\nLoading Piper voice model: {args.voice_model}')
    voice = PiperVoice.load(args.voice_model)

    print(f'Generating {len(speech)} speech files...')
    for i, (code, text) in enumerate(sorted(speech.items()), 1):
        dst = os.path.join(out_voice_dir, 'main', f'{code}.mp3')
        print(f'  [{i:2d}/{len(speech)}] {code}: {text[:70]}')
        synthesize_mp3(voice, text, dst)

    # Write config.yaml
    config_path = os.path.join(out_voice_dir, 'config.yaml')
    with open(config_path, 'w') as f:
        f.write(f'id: {args.pack_id}\nversion: {args.pack_version}\n')
    print(f'\nWrote config.yaml  (id={args.pack_id}, version={args.pack_version})')

    # Build ZIP
    zip_path = os.path.join(args.out_dir, f'{voice_name}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
        zf.write(config_path, f'{voice_name}/config.yaml')
        main_dir = os.path.join(out_voice_dir, 'main')
        for fname in sorted(os.listdir(main_dir)):
            zf.write(os.path.join(main_dir, fname), f'{voice_name}/main/{fname}')

    size = os.path.getsize(zip_path)
    md5  = hashlib.md5(open(zip_path, 'rb').read()).hexdigest()

    zip_name = os.path.basename(zip_path)
    url_hint = f'http://{args.server_ip}/{zip_name}' if args.server_ip else f'http://YOUR_SERVER_IP/{zip_name}'

    print(f'\nZIP built: {zip_path}')
    print(f'  Size : {size} bytes')
    print(f'  MD5  : {md5}')
    print(f'\nRun the HTTP server:')
    print(f'  cd {args.out_dir} && python3 -m http.server 80')
    print(f'\nThen push to the vacuum:')
    print(f'  python3 send_voice_pack.py \\')
    print(f'    --device-id YOUR_DEVICE_ID \\')
    print(f'    --local-key YOUR_LOCAL_KEY \\')
    print(f'    --ip YOUR_VACUUM_IP \\')
    print(f'    --url {url_hint} \\')
    print(f'    --md5 {md5} \\')
    print(f'    --size {size} \\')
    print(f'    --set-id {args.pack_id} \\')
    print(f'    --version {args.pack_version}')


if __name__ == '__main__':
    main()
