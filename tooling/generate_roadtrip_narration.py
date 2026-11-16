#!/usr/bin/env python3
"""Generate local road-trip narration and silence clips (macOS only).

This tool is intentionally not part of the public runtime. Run it once to
materialize small, licensed-for-this-project narration files under
app/public/narration. Bird recordings are never generated or altered here.
"""
from __future__ import annotations
import argparse, hashlib, json, re, subprocess, tempfile, wave
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RELEASE = ROOT / "experiments/private/local-mvp/release.json"
OUT = ROOT / "app/public/narration"
VOICE = "Samantha"
INSTRUCTIONS = {
    "intro": "Road Trip. Listen to each bird recording. Guess the species during the pause. The answer follows.",
    "listen": "Listen and learn. The species is announced before its recordings.",
    "guess": "Guess now.",
    "answer": "The answer is",
    "next": "The next bird is",
    "another": "Here is another recording.",
    "complete": "Session complete. Pull over safely before using the screen.",
}

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def convert(text: str, target: Path, *, aiff: Path) -> None:
    subprocess.run(["say", "-v", VOICE, "-o", str(aiff), text], check=True)
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "48000", str(aiff), str(target)], check=True)
    aiff.unlink(missing_ok=True)

def silence(seconds: int, target: Path, *, wav: Path) -> None:
    rate = 8000
    with wave.open(str(wav), "wb") as out:
        out.setnchannels(1); out.setsampwidth(2); out.setframerate(rate)
        out.writeframes(b"\x00\x00" * rate * seconds)
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", "-b", "24000", str(wav), str(target)], check=True)
    wav.unlink(missing_ok=True)

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, default=DEFAULT_RELEASE)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    release = json.loads(args.release.read_text())
    args.output.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, dict] = {"schema": "birdahead-narration-v1", "generated_at": datetime.now(timezone.utc).isoformat(), "voice": VOICE, "files": {}}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for key, text in INSTRUCTIONS.items():
            target = args.output / "instructions" / f"{key}.m4a"
            convert(text, target, aiff=tmp / f"{key}.aiff")
            manifest["files"][f"instructions/{key}.m4a"] = {"bytes": target.stat().st_size, "sha256": sha(target), "content_type": "audio/mp4"}
        for seconds in (5, 10, 15, 20, 30, 45, 60):
            target = args.output / "silence" / f"{seconds}.m4a"
            silence(seconds, target, wav=tmp / f"silence-{seconds}.wav")
            manifest["files"][f"silence/{seconds}.m4a"] = {"bytes": target.stat().st_size, "sha256": sha(target), "content_type": "audio/mp4", "duration_seconds": seconds}
        for species in release.get("species", []):
            code = str(species.get("ebird_species_code") or "")
            name = str(species.get("common_name") or "")
            if not re.fullmatch(r"[a-z0-9]+", code) or not name:
                continue
            target = args.output / "names" / f"{code}.m4a"
            convert(name, target, aiff=tmp / f"{code}.aiff")
            manifest["files"][f"names/{code}.m4a"] = {"bytes": target.stat().st_size, "sha256": sha(target), "content_type": "audio/mp4"}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({"files": len(manifest["files"]), "bytes": sum(item["bytes"] for item in manifest["files"].values()), "output": str(args.output)}, indent=2))

if __name__ == "__main__":
    main()
