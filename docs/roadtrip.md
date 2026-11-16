# Road Trip mode

Road Trip is a hands-free, audio-first learning mode for public guests and authenticated household learners. Configuration happens before driving. During a session the app never requires microphone access, speech recognition or screen interaction.

## Session configuration

- County and outing date
- 10, 20, 30 or 60 minutes
- Common birds, Here Now, Arriving Soon, mixed seasonal curriculum or the signed-in learner's weak areas
- 5–60 second silent guessing interval
- Sequential or shuffled exercises
- Guess-and-reveal or listen-and-learn

Each exercise uses authentic accepted public recordings, with a second distinct recording when the species has one. The quiz sequence is:

1. Authentic recording
2. Silent interval
3. Spoken species name
4. Second recording where available
5. Automatic advance to the next exercise

Listen-and-learn announces the species before the recordings and does not insert a guessing interval. Listening is recorded in a separate IndexedDB `listening` store and never creates a scored attempt or awards mastery. Guest listening stays local; signed-in listening records the profile id locally and does not enter the scored progress history.

## Narration and audio

The narration pack is generated locally with **Kokoro-82M** (`hexgrad/Kokoro-82M`, Apache-2.0) and the `af_heart` voice. Kokoro documents permissive/non-copyrighted and synthetic training audio; no paid TTS, provider API or cloud speech service is used. It contains 100 species-name clips, reusable instruction clips and silent interval clips. Generated files are WAV for macOS/Linux reproducibility. The manifest records the model, voice, version, bytes and SHA-256 for every file. Browser `speechSynthesis` is used only as a fallback when a narration file cannot play; it is not assumed to be available offline. Reproduce with:

```sh
uv run --with 'kokoro==0.9.4' --with soundfile python tooling/generate_roadtrip_narration.py
```

Install `espeak-ng` first if the platform does not provide Kokoro's English fallback (macOS: `brew install espeak-ng`; Linux: the distribution package).

The current narration version is `kokoro-82m-af_heart-v1`. Pre-Kokoro `.m4a` narration is removed from current delivery and old downloaded packs are marked for refresh. See `docs/offline.md` and [narration remediation](narration-remediation.md).

Road-trip packs reuse the Phase Four `birdahead-pack-assets-v1` cache. They include the selected recordings, name/instruction clips and only the silence interval needed by that session. Shared recordings are stored once. The download UI shows the actual size before download and the pack participates in interruption recovery, integrity validation, release-change marking and deletion/reclamation.

Playback is a continuous HTMLMediaElement segment chain driven by `ended` events, not background JavaScript timers. Media Session exposes play, pause, next, previous/replay, seek forward/back and stop to Bluetooth/lock-screen controls. Native media controls are shown in the driving view. Phone calls, navigation prompts and Bluetooth interruptions may pause playback; Resume and the native controls are available, but are not required for normal progression.

## Attribution and boundaries

Bird recordings retain their creator, source URL, license, attribution and public-noncommercial/share-alike notices in the downloaded pack. Narration is project-generated instructional audio, not a bird recording. Nothing in Road Trip caches authenticated `/api/*` or `/media/*` responses. No content is scored from listening or from an unobserved spoken answer.

## Platform limitations

- Background playback and Media Session behavior differ by iOS/Android version, browser, Bluetooth stack and vehicle head unit. A browser can pause or suspend an HTMLMediaElement when the screen locks even when a desktop simulation succeeds.
- Browser speech synthesis voices and availability differ by platform and are an online/device-dependent fallback only.
- The narration model is Apache-2.0 Kokoro-82M; the voice is `af_heart`. Model/voice provenance is recorded in the manifest and [narration remediation](narration-remediation.md). Platform speech synthesis remains only a fallback.
- Simulated headless Chrome tests cannot prove physical Bluetooth routing, lock-screen controls, phone-call interruption behavior or OS storage eviction.

## Physical-device checklist

1. Install the PWA on a real iPhone and Android device.
2. Download a 10-minute session on Wi-Fi, verify the displayed size and cache integrity.
3. Start in quiz mode with a 10-second interval; lock the screen and confirm audio continues.
4. Connect Bluetooth, verify play/pause/next/replay controls and metadata on the vehicle or headphones.
5. Trigger a phone call and a navigation announcement; verify pause and safe resume.
6. Start a listen-and-learn session; verify species announcements precede recordings.
7. Reload the app with the screen off/online/offline and resume the saved session.
8. Remove the pack and confirm only unreferenced media/narration is reclaimed.
9. Verify no scored attempt or mastery is created by listening.
10. Check a content-release refresh and a withdrawn-asset sync/rejection path.
