#!/usr/bin/env python3
"""Generate reproducible Road Trip narration with Kokoro-82M (Apache-2.0).

Run from the repository root on macOS or Linux with:
  uv run --with 'kokoro==0.9.4' --with soundfile python tooling/generate_roadtrip_narration.py

The first run downloads the Apache-2.0 Kokoro-82M weights and the selected
voice from Hugging Face. Inference is local; no paid TTS or cloud API is used.
Generated WAV files are public project narration, not bird recordings.
"""
from __future__ import annotations
import argparse, hashlib, json, re, wave
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import soundfile as sf
from kokoro import KPipeline

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = ROOT / "experiments/private/local-mvp/release.json"
OUT = ROOT / "app/public/narration"
MODEL = "hexgrad/Kokoro-82M"
VOICE = "af_heart"
VERSION = "kokoro-82m-af_heart-v1"
SAMPLE_RATE = 24000
INSTRUCTIONS = {
    "intro": "Road Trip. Listen to each bird recording. Guess the species during the pause. The answer follows.",
    "listen": "Listen and learn. The species is announced before its recordings.",
    "guess": "Guess now.", "answer": "The answer is", "next": "The next bird is",
    "another": "Here is another recording.",
    "complete": "Session complete. Pull over safely before using the screen.",
}
# The bracketed sections use Kokoro's misaki phoneme syntax. These are
# pronunciation corrections only, not biological claims.
PRONUNCIATION_OVERRIDES = {
    "Pileated Woodpecker": "[Pileated](/ˈpaɪliˌeɪtɪd/) Woodpecker",
    "Prothonotary Warbler": "[Prothonotary](/prəˈθɒnəˌtɛri/) Warbler",
    "Bonaparte's Gull": "[Bonaparte's](/ˈboʊnəpɑːrts/) Gull",
    "Sharp-shinned Hawk": "[Sharp-shinned](/ˈʃɑːrpˌʃɪnd/) Hawk",
    "Cooper's Hawk": "[Cooper's](/ˈkuːpərz/) Hawk",
    "Blue-gray Gnatcatcher": "Blue-gray [Gnatcatcher](/ˈnætˌkætʃər/)",
    "Dickcissel": "[Dickcissel](/ˈdɪksɪsəl/)",
    "Gadwall": "[Gadwall](/ˈɡædwɔːl/)",
    "Bufflehead": "[Bufflehead](/ˈbʌfəlhɛd/)",
    "Prothonotary": "[Prothonotary](/prəˈθɒnəˌtɛri/)",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_audio(audio, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    sf.write(target, np.asarray(audio, dtype=np.float32), SAMPLE_RATE, subtype="PCM_16")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    release = json.loads(args.release.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    for old in args.output.rglob("*.m4a"):
        old.unlink()
    pipeline = KPipeline(lang_code="a", repo_id=MODEL)
    manifest = {
        "schema": "birdahead-narration-v2", "narration_version": VERSION,
        "model": MODEL, "model_license": "Apache-2.0",
        "model_url": "https://huggingface.co/hexgrad/Kokoro-82M", "model_sha256": "496dba118d1a58f5f3db2efc88dbdc216e0483fc89fe6e47ee1f2c53f18ad1e4", "voice_sha256": "0ab5709b", "tool_versions": {"kokoro": "0.9.4", "soundfile": "0.14.0"},
        "voice": VOICE, "voice_license": "See Kokoro-82M Apache-2.0 model card and voice/training provenance",
        "training_data": "Permissive/non-copyrighted and synthetic audio; see model card",
        "generated_at": datetime.now(timezone.utc).isoformat(), "files": {}, "pronunciation_review": [],
    }
    def speak(text: str, target: Path, label: str | None = None) -> None:
        chunks = []
        phonemes = []
        for _gs, ps, audio in pipeline(text, voice=VOICE):
            phonemes.append(ps); chunks.append(np.asarray(audio, dtype=np.float32))
        if not chunks:
            raise RuntimeError(f"Kokoro produced no audio for {label or text}")
        write_audio(np.concatenate(chunks), target)
        if label:
            manifest["pronunciation_review"].append({"name": label, "text": text, "phonemes": " ".join(phonemes)})
    for key, text in INSTRUCTIONS.items():
        target = args.output / "instructions" / f"{key}.wav"
        speak(text, target)
        manifest["files"][f"instructions/{key}.wav"] = {"bytes": target.stat().st_size, "sha256": sha(target), "content_type": "audio/wav"}
    rate = 16000
    for seconds in (5, 10, 15, 20, 30, 45, 60):
        target = args.output / "silence" / f"{seconds}.wav"
        target.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(target), "wb") as out:
            out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate)
            out.writeframes(b"\x00\x00" * rate * seconds)
        manifest["files"][f"silence/{seconds}.wav"] = {"bytes": target.stat().st_size, "sha256": sha(target), "content_type": "audio/wav", "duration_seconds": seconds}
    for species in release.get("species", []):
        code = str(species.get("ebird_species_code") or "")
        name = str(species.get("common_name") or "")
        if not re.fullmatch(r"[a-z0-9]+", code) or not name:
            continue
        target = args.output / "names" / f"{code}.wav"
        text = PRONUNCIATION_OVERRIDES.get(name, name)
        speak(text, target, name if text != name else None)
        manifest["files"][f"names/{code}.wav"] = {"bytes": target.stat().st_size, "sha256": sha(target), "content_type": "audio/wav"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"version": VERSION, "files": len(manifest["files"]), "bytes": sum(x["bytes"] for x in manifest["files"].values()), "pronunciation_review": len(manifest["pronunciation_review"]), "output": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()
