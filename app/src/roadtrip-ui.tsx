import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  deletePack, downloadPack, formatBytes, listOfflineAttempts, listPacks,
  recordListening, removeLegacyNarrationCache, type OfflineAttempt, type OfflinePackDefinition, type OfflineProgress,
  type StoredPack, type NarrationManifest, type RoadTripConfig, type RoadTripFocus,
  type RoadTripInterval, type RoadTripMinutes, type RoadTripMode, type RoadTripOrder,
  type RoadTripSegment,
} from "./offline";
import { planRoadTrip } from "./roadtrip";

type Row = Record<string, any>;
const FOCUS_LABELS: Record<RoadTripFocus, string> = {
  common: "Common birds", here: "Here Now", arriving: "Arriving Soon", mixed: "Mixed seasonal curriculum", weak: "My weak areas",
};
function catalogFrom(library: Row, county: string, day: string) {
  return { release_id: String(library.release_id ?? ""), county, day,
    species: (library.species ?? []).map((row: Row) => ({
      code: String(row.code), name: String(row.name), scientific_name: row.scientific_name, confusion_pair: row.confusion_pair ?? null,
      priority_rank: row.priority_rank ?? null, current_reporting_frequency: row.current_reporting_frequency ?? null,
      approaching_window_rise: row.approaching_window_rise ?? null,
      assets: (row.assets ?? []).filter((asset: Row) => asset.kind === "audio" && Number(asset.bytes) > 0 && typeof asset.sha256 === "string" && asset.media_url?.startsWith("/media/public/")),
    })) };
}
function weakCodesFrom(progress: Row | null, attempts: OfflineAttempt[]): string[] {
  const codes = new Set<string>();
  for (const row of progress?.by_species ?? []) if (Number(row.recognized) < Number(row.attempts)) codes.add(String(row.code));
  for (const row of attempts) if (row.outcome !== "correct") codes.add(row.species_code);
  return [...codes];
}
export function RoadTrip({ boot, county, day, signedIn, profile, progress, setCounty, setDay }: {
  boot: Row; county: string; day: string; signedIn: boolean; profile: string; progress: Row | null;
  setCounty: (value: string) => void; setDay: (value: string) => void;
}) {
  const [library, setLibrary] = useState<Row | null>(null);
  const [manifest, setManifest] = useState<NarrationManifest | null>(null);
  const [stored, setStored] = useState<StoredPack[]>([]);
  const [minutes, setMinutes] = useState<RoadTripMinutes>(20);
  const [focus, setFocus] = useState<RoadTripFocus>("mixed");
  const [intervalSeconds, setIntervalSeconds] = useState<RoadTripInterval>(10);
  const [order, setOrder] = useState<RoadTripOrder>("sequential");
  const [mode, setMode] = useState<RoadTripMode>("quiz");
  const [weak, setWeak] = useState<string[]>([]);
  const [progressState, setProgressState] = useState<OfflineProgress | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [active, setActive] = useState<StoredPack | null>(null);
  const [resumeInfo, setResumeInfo] = useState<{ pack_id: string; segment_index: number } | null>(null);
  const [segmentIndex, setSegmentIndex] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [finished, setFinished] = useState(false);
  const [error, setError] = useState("");
  const audio = useRef<HTMLAudioElement | null>(null);

  const startedAt = useRef<number>(0);
  const fallbackSpeaking = useRef(false);
  async function refresh() { setStored(await listPacks()); }
  useEffect(() => {
    Promise.all([
      fetch(`/api/public/library?location=${encodeURIComponent(county)}&day=${encodeURIComponent(day)}`, { credentials: "same-origin" }).then((r) => r.ok ? r.json() : Promise.reject(new Error("Public audio catalog unavailable."))),
      fetch("/narration/manifest.json", { credentials: "same-origin" }).then((r) => r.ok ? r.json() : Promise.reject(new Error("Narration manifest unavailable."))),
    ]).then(([lib, man]) => {
      setLibrary(lib); setManifest(man);
      localStorage.setItem("birdahead-narration-manifest-v1", JSON.stringify(man));
      localStorage.setItem("birdahead-roadtrip-library-v1", JSON.stringify({ county, day, library: lib }));
    }).catch((reason) => {
      try {
        const saved = JSON.parse(localStorage.getItem("birdahead-roadtrip-library-v1") ?? "null");
        if (saved?.library) setLibrary(saved.library);
        const narration = localStorage.getItem("birdahead-narration-manifest-v1");
        if (narration) { const parsed = JSON.parse(narration); if (parsed?.schema === "birdahead-narration-v2" && parsed?.narration_version) setManifest(parsed); }
      } catch { /* use the error below */ }
      setMessage(reason.message);
    });
  }, [county, day]);
  useEffect(() => { removeLegacyNarrationCache().catch(() => undefined); refresh().catch((reason) => setMessage(reason.message)); }, []);
  useEffect(() => { listOfflineAttempts(signedIn ? profile : null).then((rows) => setWeak(weakCodesFrom(progress, rows))).catch(() => undefined); }, [signedIn, profile, progress]);
  useEffect(() => {
    try { const saved = JSON.parse(localStorage.getItem("birdahead-roadtrip-active-v1") ?? "null"); if (saved?.pack_id) setResumeInfo(saved); } catch { /* optional */ }
  }, []);
  const config: RoadTripConfig = { minutes, county, day, focus, interval_seconds: intervalSeconds, order, mode };
  const planResult = useMemo(() => {
    if (!library || !manifest) return { plan: null as OfflinePackDefinition | null, error: "" };
    try { return { plan: planRoadTrip(catalogFrom(library, county, day), manifest, config, weak), error: "" }; }
    catch (reason) { return { plan: null as OfflinePackDefinition | null, error: (reason as Error).message }; }
  }, [library, manifest, county, day, minutes, focus, intervalSeconds, order, mode, weak.join("|")]);
  const plan = planResult.plan; const planError = planResult.error;
  const downloaded = stored.filter((row) => row.roadTrip);
  const narrationVersion = manifest?.narration_version ?? "";
  const versionCurrent = (version?: string) => !narrationVersion || version === narrationVersion;
  const selectedStored = plan ? stored.find((row) => row.id === plan.id && row.status === "complete" && versionCurrent(row.roadTrip?.narration_version)) : undefined;
  const segments = active?.roadTrip?.segments ?? [];
  const currentSegment = segments[segmentIndex] ?? null;
  async function startDownload() {
    if (!plan) return; setBusy(true); setMessage(""); setProgressState(null);
    try {
      await downloadPack(plan, (row) => setProgressState(row));
      await refresh(); setMessage(`${plan.title} downloaded. Configure once, then start hands-free playback.`);
    } catch (reason) { setMessage((reason as Error).message); }
    finally { setBusy(false); }
  }
  function startSession(pack: StoredPack, segment = 0) {
    if (!pack.roadTrip) return;
    if (!pack.roadTrip.narration_version || (narrationVersion && pack.roadTrip.narration_version !== narrationVersion)) { setMessage("This road-trip pack uses an obsolete narration version. Remove it and download a new session."); return; }
    setActive(pack); setSegmentIndex(segment); setFinished(false); setPlaying(false); setError(""); startedAt.current = Date.now();
    localStorage.setItem("birdahead-roadtrip-active-v1", JSON.stringify({ pack_id: pack.id, segment_index: segment }));
  }
  function stopSession() {
    audio.current?.pause(); setPlaying(false); setActive(null); setFinished(false);
    localStorage.removeItem("birdahead-roadtrip-active-v1"); setResumeInfo(null);
  }
  async function finishSession() {
    if (!active?.roadTrip) return;
    setFinished(true); setPlaying(false); localStorage.removeItem("birdahead-roadtrip-active-v1"); setResumeInfo(null);
    await recordListening({ profile_id: signedIn ? profile : null, pack_id: active.id, release_id: active.release_id,
      minutes: active.roadTrip.config.minutes, exercises_completed: active.roadTrip.exercises.length, focus: active.roadTrip.config.focus }).catch(() => undefined);
  }
  function advance() {
    if (!active?.roadTrip) return;
    if (segmentIndex + 1 < segments.length) setSegmentIndex((index) => index + 1);
    else void finishSession();
  }
  function replay() {
    if (!audio.current) return; audio.current.currentTime = 0; void audio.current.play().catch(() => undefined);
  }
  function skip() {
    if (!active?.roadTrip || !currentSegment) return;
    const next = segments.findIndex((segment, index) => index > segmentIndex && segment.exercise > currentSegment.exercise);
    if (next >= 0) setSegmentIndex(next); else void finishSession();
  }
  function fallbackNarration(segment: RoadTripSegment | null) {
    const text = segment?.text;
    if (!text || typeof speechSynthesis === "undefined") {
      setError("Narration is unavailable offline. This session needs its narration pack or browser speech synthesis.");
      setPlaying(false); return;
    }
    fallbackSpeaking.current = true;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.92; utterance.onend = () => { fallbackSpeaking.current = false; advance(); };
    utterance.onerror = () => { fallbackSpeaking.current = false; setError("Narration playback failed."); setPlaying(false); };
    speechSynthesis.cancel(); speechSynthesis.speak(utterance); setPlaying(true);
  }
  function handleAudioError() {
    audio.current?.pause(); setPlaying(false);
    if (currentSegment?.kind === "narration") fallbackNarration(currentSegment);
    else setError("This recording could not be played. Check the downloaded pack and try skipping or reconnecting.");
  }
  useEffect(() => {
    if (!active || !currentSegment || finished || fallbackSpeaking.current) return;
    const element = audio.current; if (!element) return;
    element.src = currentSegment.url; element.load();
    void element.play().then(() => setPlaying(true)).catch((reason) => {
      if ((reason as Error).name === "NotAllowedError") setError("Tap Play once to begin; the rest of the session advances automatically.");
      else setError("Audio playback could not start.");
    });
    localStorage.setItem("birdahead-roadtrip-active-v1", JSON.stringify({ pack_id: active.id, segment_index: segmentIndex }));
  }, [active, currentSegment, segmentIndex, finished]);
  useEffect(() => {
    if (!("mediaSession" in navigator) || !active) return;
    const session = navigator.mediaSession;
    session.metadata = new MediaMetadata({ title: `BirdAhead Road Trip · ${active.roadTrip?.config.minutes ?? ""} min`, artist: "BirdAhead", album: "Road trip learning", artwork: [{ src: "/icon-512.png", sizes: "512x512", type: "image/png" }] });
    const handlers: Array<[MediaSessionAction, MediaSessionActionHandler]> = [
      ["play", () => { void audio.current?.play(); }], ["pause", () => audio.current?.pause()],
      ["nexttrack", skip], ["previoustrack", replay], ["seekforward", skip], ["seekbackward", replay],
      ["stop", () => stopSession()],
    ];
    for (const [action, handler] of handlers) { try { session.setActionHandler(action, handler); } catch { /* unsupported action */ } }
    session.playbackState = playing ? "playing" : "paused";
    return () => { for (const [action] of handlers) { try { session.setActionHandler(action, null); } catch { /* unsupported */ } } };
  }, [active, playing, segmentIndex, currentSegment]);
  const resumePack = resumeInfo ? stored.find((row) => row.id === resumeInfo.pack_id && row.roadTrip?.segments?.length && versionCurrent(row.roadTrip?.narration_version)) : null;
  async function removeRoadTrip(id: string) { setBusy(true); try { await deletePack(id); await refresh(); } catch (reason) { setMessage((reason as Error).message); } finally { setBusy(false); } }


  if (active?.roadTrip) {
    const road = active.roadTrip; const exercise = road.exercises[Math.min(currentSegment?.exercise ?? 0, road.exercises.length - 1)];
    const label = finished ? "Session complete" : currentSegment?.kind === "silence" ? "Guess the species" : currentSegment?.kind === "narration" ? (currentSegment.text ?? "Narration") : "Listen to the recording";
    return <section className="roadtrip-driving"><div className="roadtrip-driving-head"><span className="eyebrow">HANDS-FREE ROAD TRIP · {road.config.minutes} MIN</span><button className="secondary" onClick={stopSession}>End session</button></div>
      {finished ? <><h1>Session complete.</h1><p>Listening activity was recorded separately from identification attempts. No mastery was awarded for listening.</p><div className="public-actions"><button className="primary" onClick={() => startSession(active, 0)}>Play again</button><button className="secondary" onClick={() => setActive(null)}>Back to setup</button></div></> : <>
        <div className="roadtrip-status"><span>{label}</span><span>{Math.min((currentSegment?.exercise ?? 0) + 1, road.exercises.length)} of {road.exercises.length}</span></div>
        <div className="roadtrip-big-audio" aria-live="polite">{exercise ? <strong>{currentSegment?.kind === "narration" && road.config.mode === "listen" ? exercise.name : currentSegment?.kind === "narration" && currentSegment.text === "The answer is" ? "The answer follows" : "Listen"}</strong> : null}</div>
        <audio ref={audio} controls preload="auto" onEnded={advance} onPlay={() => setPlaying(true)} onPause={() => setPlaying(false)} onError={handleAudioError} onTimeUpdate={() => { if (audio.current && Number.isFinite(audio.current.duration) && "mediaSession" in navigator) { try { navigator.mediaSession.setPositionState({ duration: audio.current.duration, position: Math.min(audio.current.currentTime, audio.current.duration), playbackRate: audio.current.playbackRate }); } catch { /* ignore */ } } }} />
        <div className="public-actions"><button className="primary" onClick={() => playing ? audio.current?.pause() : audio.current?.play()}>{playing ? "Pause" : "Resume"}</button><button className="secondary" onClick={replay}>Replay</button><button className="secondary" onClick={skip}>Skip</button></div>
        <p className="fine">Playback advances through the downloaded audio chain. You do not need to touch the screen again. Phone calls, navigation prompts and Bluetooth interruptions may pause the audio; use Resume or the native media controls. This mode never listens to or grades your voice.</p>
      </>}{error && <p className="error">{error}</p>}</section>;
  }
  return <section className="roadtrip-page"><span className="eyebrow">ROAD TRIP MODE · CONFIGURE BEFORE DRIVING</span><h1>Learn by ear.<br /><em>Keep your eyes ahead.</em></h1><p>Download one compact session before you leave. Playback runs through the browser's media element, advances automatically, and exposes native Bluetooth/lock-screen controls. It never requires microphone access or speech recognition while driving.</p>
    <div className="roadtrip-config"><label>County<select value={county} onChange={(event) => setCounty(event.target.value)}>{Object.entries(boot.counties ?? {}).map(([code, name]) => <option key={code} value={code}>{String(name)}</option>)}</select></label><label>Outing date<input type="date" value={day} onChange={(event) => setDay(event.target.value)} /></label><label>Session length<select value={minutes} onChange={(event) => setMinutes(Number(event.target.value) as RoadTripMinutes)}>{[10, 20, 30, 60].map((value) => <option key={value} value={value}>{value} minutes</option>)}</select></label><label>Curriculum<select value={focus} onChange={(event) => setFocus(event.target.value as RoadTripFocus)}>{Object.entries(FOCUS_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select></label><label>Guessing interval<select value={intervalSeconds} onChange={(event) => setIntervalSeconds(Number(event.target.value) as RoadTripInterval)}>{[5, 10, 15, 20, 30, 45, 60].map((value) => <option key={value} value={value}>{value} seconds</option>)}</select></label><label>Order<select value={order} onChange={(event) => setOrder(event.target.value as RoadTripOrder)}><option value="sequential">Sequential</option><option value="shuffled">Shuffled</option></select></label><label>Mode<select value={mode} onChange={(event) => setMode(event.target.value as RoadTripMode)}><option value="quiz">Guess, pause, then reveal</option><option value="listen">Listen and learn</option></select></label></div>
    {planError && <p className="error">{planError}</p>}{!library && !planError && <p className="loading">Preparing the road-trip catalog…</p>}
    {plan && <div className="roadtrip-summary"><div><b>{plan.roadTrip?.exercises.length ?? 0}</b><span>exercises</span></div><div><b>{plan.assets.length}</b><span>audio files</span></div><div><b>{formatBytes(plan.bytes)}</b><span>download</span></div><div><b>{plan.release_id.slice(0, 10)}…</b><span>release</span></div></div>}
    {progressState && <div className="download-progress"><div style={{ width: `${Math.min(100, (progressState.completed / Math.max(1, progressState.total)) * 100)}%` }} /><span>{progressState.completed} of {progressState.total}</span></div>}
    <div className="public-actions">{plan && (selectedStored ? <button className="primary" onClick={() => startSession(selectedStored)}>Start downloaded session</button> : <button className="primary" disabled={busy} onClick={startDownload}>{busy ? "Downloading…" : "Download session for offline"}</button>)}{resumePack && resumeInfo && <button className="secondary" onClick={() => startSession(resumePack, resumeInfo.segment_index)}>Resume saved session</button>}</div>
    {message && <p className="fine">{message}</p>}
    <h2>Downloaded road trips</h2>
    {downloaded.length ? <div className="roadtrip-list">{downloaded.map((row) => <article key={row.id}><div><strong>{row.title}</strong><small>{row.roadTrip?.exercises.length} exercises · {formatBytes(row.bytes)} · release {row.release_id.slice(0, 10)}…{!versionCurrent(row.roadTrip?.narration_version) ? " · narration update required" : ""}</small></div><div className="public-actions"><button className="primary" disabled={!row.roadTrip?.narration_version || !versionCurrent(row.roadTrip.narration_version)} onClick={() => startSession(row)}>Start</button><button className="secondary" onClick={() => removeRoadTrip(row.id)}>Remove</button></div></article>)}</div> : <p className="fine">No road-trip session is downloaded yet.</p>}
    <p className="fine">Quiz mode plays a recording, a silent guess interval, spoken species name and a second recording where available. Listening activity is stored separately and never marked correct. Bird recordings carry their original creator, source and license notices.</p>
  </section>;
}
