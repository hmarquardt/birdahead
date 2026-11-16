# Narration remediation and historical exposure

## Decision

The macOS `say`/system-voice narration used in the accepted Phase Five revision
was replaced because Apple's macOS software license Section 2.F restricts
public redistribution of system voice recordings. The replacement is
**Kokoro-82M** (`hexgrad/Kokoro-82M`), delivered as public WAV assets.

## Replacement provenance

| Item | Value |
| --- | --- |
| Model | `hexgrad/Kokoro-82M` |
| Model license | Apache-2.0 |
| Model URL | https://huggingface.co/hexgrad/Kokoro-82M |
| Voice | `af_heart` |
| Voice/model data | Kokoro documents permissive/non-copyrighted and synthetic training audio |
| Inference | Local CPU/MPS, no paid API |
| Output format | PCM WAV, 24 kHz narration; 16 kHz silence |
| Narration version | `kokoro-82m-af_heart-v1` |
| Manifest | `app/public/narration/manifest.json` with bytes/SHA-256 |

The generation utility is `tooling/generate_roadtrip_narration.py`. It uses
`uv` and works on macOS or Linux:

```sh
uv run --with 'kokoro==0.9.4' --with soundfile \
  python tooling/generate_roadtrip_narration.py
```

The first run downloads the Apache-2.0 model/voice from Hugging Face. Install
`espeak-ng` if the platform does not provide Kokoro's English fallback. No paid
inference is used. The manifest records the model, voice, license and
pronunciation-review phonemes for names with explicit overrides (Pileated,
Prothonotary, Bonaparte's, Sharp-shinned, Cooper's, Blue-gray Gnatcatcher,
Dickcissel, Gadwall and Bufflehead).

## Current repository state

The Apple-generated `.m4a` files are deleted from the current working tree and
replaced by the Kokoro `.wav` files. The public smoke check verifies the current
manifest and a current narration asset.

## Historical exposure

The Apple-generated files were added in repository commit `4597eca` and are
therefore present in Git history even though they are removed from the current
tree. Production currently serves the replacement files; old Worker versions
are not a canonical public narration URL. If the repository is public and the
owner wants to remove the historical blobs, use an authorized history rewrite
(for example `git filter-repo --path app/public/narration` followed by a
coordinated force-push) after coordinating with all clones and CI. **No history
rewrite was performed here**, and no remote history was altered.

The current Worker explicitly returns `404` for every `/narration/*.m4a` path so retained immutable static objects cannot be delivered. The Apple files should not be reused, copied into another project or redistributed. The Kokoro replacement is the only current narration source.
