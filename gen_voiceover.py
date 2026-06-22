#!/usr/bin/env python3
"""
gen_voiceover.py — generate ElevenLabs voiceover for the ItoMarkets brand film.
"""
import json, os, urllib.request

BUILD = os.path.dirname(os.path.abspath(__file__))


def load_env():
    env = {}
    with open(os.path.join(BUILD, ".env.hermes")) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            env[k] = v
    return env


def main():
    env = load_env()
    key = env.get("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("ELEVENLABS_API_KEY not found")

    script_path = os.path.join(BUILD, "script.md")
    with open(script_path) as f:
        text = f.read()

    # Extract only the quoted lines (the actual voiceover)
    lines = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("> "):
            lines.append(line[2:].strip())
    voiceover = "\n".join(lines)

    out_path = os.path.join(BUILD, "assets", "gen", "voiceover.mp3")
    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # Voice: Daniel - Steady Broadcaster (measured, institutional male, low-mid register)
    voice_id = "onwK4e9ZLuTAKqWW03F9"
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"

    data = json.dumps({
        "text": voiceover,
        "model_id": "eleven_monolingual_v1",
        "voice_settings": {
            "stability": 0.5,
            "similarity_boost": 0.75,
            "style": 0.0,
            "use_speaker_boost": True,
        }
    }).encode()

    req = urllib.request.Request(
        url,
        data=data,
        headers={
            "Accept": "audio/mpeg",
            "xi-api-key": key,
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        with open(out_path, "wb") as f:
            f.write(r.read())
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
