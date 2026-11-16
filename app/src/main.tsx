import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";
import { Downloads } from "./offline-ui";
import { RoadTrip } from "./roadtrip-ui";
import { syncOfflineAttempts } from "./offline";

type Row = Record<string, any>;
type Tab = "explore" | "guide" | "practice" | "downloads" | "roadtrip" | "progress" | "about";
type Auth = "checking" | "guest" | "in";
declare global { interface Window { cflabAnalytics?: { track?: (name: string, props?: Row) => void } } }
const track = (name: string, props?: Row) => { try { window.cflabAnalytics?.track?.(name, props); } catch { /* optional */ } };
const pct = (n: number | null | undefined) => n === null || n === undefined ? "Unknown" : `${(n * 100).toFixed(1)}%`;
const today = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const guestKey = "birdahead-guest-history-v1";
const readGuest = (): Row[] => { try { return JSON.parse(localStorage.getItem(guestKey) ?? "[]"); } catch { return []; } };
const writeGuest = (rows: Row[]) => localStorage.setItem(guestKey, JSON.stringify(rows.slice(-500)));
const addGuest = (attempt: Row) => writeGuest([...readGuest(), { ...attempt, at: new Date().toISOString() }]);

async function api(path: string, body?: Row) {
  const response = await fetch("/api/" + path, {
    credentials: "same-origin",
    ...(body ? { method: "POST", headers: { "Content-Type": "application/json", "X-BirdAhead-Request": "1" }, body: JSON.stringify(body) } : {}),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== "login") window.dispatchEvent(new Event("birdahead-auth-expired"));
    const error = Error(data.error ?? "Request failed") as Error & { status?: number };
    error.status = response.status;
    throw error;
  }
  return data;
}

function Icon({ type }: { type: "bird" | "photo" | "audio" | "arrow" }) {
  const paths = {
    bird: <><path d="M3 17c6 0 6-7 13-7l3-4 2 4-3 3c1 6-4 9-10 7l-4 2 2-4" /><path d="M9 16c2 0 4-1 5-3" /></>,
    photo: <><rect x="3" y="4" width="18" height="16" rx="3" /><circle cx="9" cy="9" r="1.5" /><path d="m4 17 5-5 4 4 3-3 5 5" /></>,
    audio: <path d="M4 10v4m4-8v12m4-15v18m4-15v12m4-8v4" />,
    arrow: <path d="M4 12h15m-6-6 6 6-6 6" />,
  };
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[type]}</svg>;
}

function Credit({ asset }: { asset: Row }) {
  return <div className="credit"><p>© {asset.creator || "Unknown creator"} · <a href={asset.source_url} target="_blank" rel="noreferrer">Original record ↗</a> · <a href={asset.license_url} target="_blank" rel="noreferrer">{asset.license_code || "License"} ↗</a></p>{asset.attribution && <p>{asset.attribution}</p>}{asset.public_license_notice && <p>{asset.public_license_notice}</p>}<p>{asset.validation || "Accepted source record; not expert verification."}</p></div>;
}

function SeasonStrip({ bins }: { bins: Row[] }) {
  if (!bins.length) return <p className="fine">No historical bins available for this selection.</p>;
  return <div className="season-strip" aria-label="Historical reporting frequency by period">{bins.map((b) => <span key={b.start} title={`${b.start}–${b.end}: ${pct(b.frequency)}`} style={{ height: `${Math.max(3, (b.frequency ?? 0) * 100)}%` }} />)}</div>;
}



function LoginModal({ onClose, onLogin }: { onClose: () => void; onLogin: (profile: string, name: string) => void }) {
  const [profile, setProfile] = useState("hank");
  const [key, setKey] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: React.FormEvent) {
    e.preventDefault(); setBusy(true); setError("");
    try { const data = await api("login", { profile, key }); onLogin(data.profile_id ?? profile, data.name ?? profile); }
    catch (err) { setError((err as Error).message); }
    finally { setBusy(false); }
  }
  return <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="signin-title"><form className="modal-card" onSubmit={submit}><button type="button" className="modal-close" onClick={onClose} aria-label="Close sign in">×</button><span className="eyebrow">OPTIONAL HOUSEHOLD SIGN-IN</span><h2 id="signin-title">Keep progress across devices.</h2><p>Public exploration and guest practice are free. Signing in as Hank or Heather adds private server-backed history and personalization. The access key is never stored in this page or analytics.</p><div className="login-form"><label>Household learner<select value={profile} onChange={(e) => setProfile(e.target.value)}><option value="hank">Hank</option><option value="heather">Heather</option></select></label><label>Access key<input type="password" value={key} onChange={(e) => setKey(e.target.value)} autoComplete="current-password" required minLength={16} /></label>{error && <p className="error">{error}</p>}<button className="primary" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button><button type="button" className="secondary" onClick={onClose}>Continue as guest</button></div><p className="fine">Keys live only in the household password manager and Worker secrets. No public registration or account creation is available.</p></form></div>;
}

function Explore({ boot, ranked, arriving, county, day, setCounty, setDay, openBird, onPractice }: { boot: Row; ranked: Row[]; arriving: Row[]; county: string; day: string; setCounty: (v: string) => void; setDay: (v: string) => void; openBird: (code: string) => void; onPractice: () => void }) {
  const [seasonCode, setSeasonCode] = useState("");
  const [bins, setBins] = useState<Row[]>([]);
  const [seasonName, setSeasonName] = useState("");
  useEffect(() => { const first = ranked.find((r) => (r.current_reporting_frequency ?? 0) > 0)?.species_code ?? ranked[0]?.species_code; if (first) setSeasonCode((x) => x || first); }, [ranked]);
  useEffect(() => { if (!seasonCode) return; api(`public/seasonality?location=${encodeURIComponent(county)}&code=${encodeURIComponent(seasonCode)}`).then((d) => { setBins(d.bins ?? []); setSeasonName(d.name ?? ""); }).catch(() => setBins([])); }, [seasonCode, county]);
  const here = ranked.filter((r) => (r.current_reporting_frequency ?? 0) > 0).slice(0, 12);
  return <>
    <section className="public-hero"><div><span className="eyebrow">SOUTHWESTERN INDIANA · FREE PUBLIC GUIDE</span><h1>Know what’s<br /><em>arriving.</em></h1><p>Explore the birds likely to be around on your next outing, browse real licensed photographs and recordings, and practice identification by sight or sound. No account is needed.</p><div className="public-actions"><button className="primary" onClick={onPractice}>Practice by sight or sound <Icon type="arrow" /></button><a className="secondary" href="/?tab=guide">Open the field guide</a></div><p className="fine">Historical eBird reporting signals, not an encounter forecast. <a href="/sources">Sources and terms</a>.</p></div><aside className="public-hero-card"><span className="eyebrow">THE PUBLIC COLLECTION</span><div><div><b>{boot.public_assets}</b><span>licensed examples</span></div><div><b>{boot.coverage.species}</b><span>regional species</span></div></div><p className="fine">{boot.data_vintage?.start_year}–{boot.data_vintage?.end_year} county histograms · {boot.coverage.public_photo_species} species with public photos · {boot.coverage.public_audio_species} with audio.</p></aside></section>
    <div className="public-controls"><label>County<select value={county} onChange={(e) => setCounty(e.target.value)}>{Object.entries(boot.counties ?? {}).map(([code, name]) => <option key={code} value={code}>{String(name)}</option>)}</select></label><label>Outing date<input type="date" value={day} onChange={(e) => setDay(e.target.value)} /></label><a className="secondary" href={`/regions/${county}`}>Regional page ↗</a></div>
    <div className="public-grid"><section className="public-panel"><span className="eyebrow">HERE NOW</span><h2>Birds worth expecting.</h2><p>Ranked by historical complete-checklist reporting for {boot.counties[county]} County on this date.</p><div className="public-list">{here.map((r, i) => <button className="public-row" key={r.species_code} onClick={() => openBird(r.species_code)} style={{ textAlign: "left", border: 0, background: "transparent" }}><span className="rank">{String(i + 1).padStart(2, "0")}</span><span><strong>{r.name}</strong><small>{pct(r.current_reporting_frequency)} of checklists · {r.public_photos ?? r.photos} photo · {r.public_recordings ?? r.recordings} sound</small></span><span className="mini-bar"><i style={{ width: `${Math.min(100, (r.current_reporting_frequency ?? 0) * 250)}%` }} /></span></button>)}{!here.length && <p className="fine">No positive historical signal for this date. Try another date or check Arriving Soon.</p>}</div></section><section className="public-panel"><span className="eyebrow">ARRIVING SOON</span><h2>The next few weeks.</h2><p>A 14–28 day rise in historical reporting, independently of today’s frequency.</p><div className="public-list">{arriving.slice(0, 8).map((r) => <button className="public-row" key={r.species_code} onClick={() => openBird(r.species_code)} style={{ textAlign: "left", border: 0, background: "transparent" }}><span className="rank">↗</span><span><strong>{r.name}</strong><small>{pct(r.approaching_window_rise)} potential rise · {r.scientific_name}</small></span><span className="mini-bar"><i style={{ width: `${Math.min(100, (r.approaching_window_rise ?? 0) * 300)}%` }} /></span></button>)}{!arriving.length && <p className="fine">No supported rise for this selection. Here Now remains available.</p>}</div></section></div>
    <section className="public-panel"><div className="section-title"><div><span className="eyebrow">HISTORICAL SEASONAL PICTURE</span><h2>{seasonName || "A year in this county"}</h2></div><select value={seasonCode} onChange={(e) => setSeasonCode(e.target.value)} aria-label="Choose a species for the seasonal picture">{ranked.slice(0, 20).map((r) => <option key={r.species_code} value={r.species_code}>{r.name}</option>)}</select></div><SeasonStrip bins={bins} /><p className="fine">Each bar is a native seasonal reporting bin. Sparse samples and observer bias remain; reporting frequency is not abundance or encounter probability.</p></section>
    <section className="public-panel public-note">Public views use media with a recorded public-noncommercial eligibility decision. NC/SA media remain attributed and noncommercial. <a href="/sources">Read the source and license notes</a>.</section>
  </>;
}


function Guide({ boot, county, day, signedIn, profile, focusCode, onPractice }: { boot: Row; county: string; day: string; signedIn: boolean; profile: string; focusCode: string; onPractice: (kind: string) => void }) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("all");
  const [data, setData] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [open, setOpen] = useState(focusCode);
  useEffect(() => { setOpen(focusCode); }, [focusCode]);
  useEffect(() => {
    let active = true; const timer = setTimeout(() => {
      const path = signedIn ? `library?profile=${encodeURIComponent(profile)}&location=${encodeURIComponent(county)}&day=${day}&kind=${kind}&q=${encodeURIComponent(query)}` : `public/library?location=${encodeURIComponent(county)}&day=${day}&kind=${kind}&q=${encodeURIComponent(query)}`;
      api(path).then((d) => { if (active) { setData(d); setError(""); } }).catch((e) => active && setError(e.message));
    }, query ? 220 : 0);
    return () => { active = false; clearTimeout(timer); };
  }, [query, kind, county, day, signedIn, profile]);
  return <section className="library"><span className="eyebrow">PUBLIC FIELD GUIDE</span><h1>Your regional<br /><em>reference shelf.</em></h1><p>Search the accepted collection used for practice. Public visitors see public-noncommercial eligible media; household sign-in can reveal the private collection view without changing public eligibility.</p>
    <div className="library-controls"><label>Search a bird<input type="search" value={query} onChange={(e) => setQuery(e.target.value)} placeholder="Name, scientific name or code" /></label><div className="segmented" aria-label="Media type">{["all", "photo", "audio"].map((v) => <button key={v} className={kind === v ? "selected" : ""} onClick={() => setKind(v)} aria-pressed={kind === v}>{v === "all" ? "Everything" : v === "photo" ? "Photos" : "Sounds"}</button>)}</div></div>
    {error && <p className="error">{error}</p>}{!data && <p className="loading">Opening the field guide…</p>}
    <div className="library-grid">{(data?.species ?? []).map((row: Row) => <article className={`species-card ${open === row.code ? "open" : ""}`} key={row.code}><button className="species-head" onClick={() => setOpen(open === row.code ? "" : row.code)} aria-expanded={open === row.code}><span><strong>{row.name}</strong><i>{row.scientific_name}</i></span><span className="species-badges"><span className={row.photo_practice_ready ? "good" : "gap"}>{row.photos} photo{row.photos === 1 ? "" : "s"}</span><span className={row.audio_practice_ready ? "good" : "gap"}>{row.recordings} sound{row.recordings === 1 ? "" : "s"}</span></span></button><div className="species-meta"><span className="fine">{row.current_reporting_frequency === null ? "Historical frequency unknown for this date" : `${pct(row.current_reporting_frequency)} of complete checklists · ${row.sample_size ?? "—"} checklists`}</span>{row.coverage_gap && <span className="gap-label">More accepted media needed</span>}</div>{open === row.code && <div className="asset-gallery">{!row.assets?.length && <p className="fine">No public example for this filter.</p>}{(row.assets ?? []).map((asset: Row) => <figure key={asset.id}>{asset.kind === "photo" ? <img src={asset.media_url} alt={`${row.name} reference photograph`} loading="lazy" /> : <audio src={asset.media_url} controls preload="none" />}<figcaption><span>© {asset.creator}{asset.vocalization ? ` · ${asset.vocalization}` : ""}{asset.derivative ? " · verified clip" : ""}</span><span><a href={asset.source_url} target="_blank" rel="noreferrer">Source ↗</a>{" "}<a href={asset.license_url} target="_blank" rel="noreferrer">{asset.license_code || "License"} ↗</a></span><Credit asset={asset} /></figcaption></figure>)}</div>}{open === row.code && <div className="public-actions"><button className="primary" onClick={() => onPractice("photo")}><Icon type="photo" /> Practice by sight</button><button className="secondary" onClick={() => onPractice("audio")}><Icon type="audio" /> Practice by sound</button></div>}</article>)}</div>
    <p className="fine">The field guide includes {boot.coverage.species} species. Historical seasonal summaries are derived from owner-supplied county histograms; raw exports are not public. <a href="/sources">eBird terms and media credits</a>.</p>
  </section>;
}


function Practice({ signedIn, profile, county, day, initialKind, initialBird, onProgress }: { signedIn: boolean; profile: string; county: string; day: string; initialKind: string; initialBird: string; onProgress: () => void }) {
  const [kind, setKind] = useState(initialKind === "audio" ? "audio" : "photo");
  const [mode, setMode] = useState("choice");
  const [focus, setFocus] = useState("now");
  const [guest, setGuest] = useState<Row | null>(null);
  const [session, setSession] = useState<Row | null>(null);
  const [index, setIndex] = useState(0);
  const [reveal, setReveal] = useState<Row | null>(null);
  const [answers, setAnswers] = useState<Row[]>([]);
  const [pending, setPending] = useState<Row | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const started = !!(guest || session);
  const questions = guest ? guest.questions ?? [] : [];
  const q = guest ? questions[index] : session?.question;
  const total = guest ? questions.length : session?.total ?? 0;
  const done = guest ? index >= questions.length : !!session?.done;
  useEffect(() => { if (initialKind === "audio" || initialKind === "photo") setKind(initialKind); }, [initialKind]);
  async function run(fn: () => Promise<void>) { if (busy) return; setBusy(true); setError(""); try { await fn(); } catch (e) { setError((e as Error).message); } finally { setBusy(false); } }
  async function start() {
    await run(async () => {
      setReveal(null); setAnswers([]); setPending(null); setIndex(0);
      if (signedIn) {
        const s = await api("sessions", { profile, location: county, day, kind, mode, focus });
        setSession(s); setGuest(null); track("practice_start", { mode, kind, guest: false });
      } else {
        const g = await api(`public/practice?location=${encodeURIComponent(county)}&day=${day}&kind=${kind}&mode=${mode}&focus=${focus}`);
        if (focus === "weak") {
          const weak = new Set(readGuest().filter((a) => a.outcome !== "correct").map((a) => a.species_code));
          g.questions = [...(g.questions ?? [])].sort((a: Row, b: Row) => Number(weak.has(b.species_code)) - Number(weak.has(a.species_code)));
        }
        setGuest(g); setSession(null); track("practice_start", { mode, kind, guest: true });
      }
    });
  }
  function recordGuest(choice: string, current: Row) {
    const outcome = ["unknown", "insufficient"].includes(choice) ? "uncertain" : choice === current.answer_code ? "correct" : "incorrect";
    const attempt = { species_code: current.species_code, name: current.name, asset_id: current.asset_id, kind: current.kind, mode: current.mode, outcome, choice };
    setAnswers((rows) => [...rows, attempt]); addGuest(attempt);
    setReveal({ outcome, answer: { code: current.answer_code, name: current.name }, feedback: outcome === "correct" ? "That matches the source identification. Try another example to test transfer." : outcome === "uncertain" ? "Uncertainty is recorded separately from an incorrect guess." : `The source identification is ${current.name}.` });
    if (answers.length + 1 >= total) track("practice_complete", { mode, kind, guest: true });
  }
  async function answer(choice: string) {
    if (!q) return;
    await run(async () => {
      if (!signedIn) { recordGuest(choice, q); return; }
      const result = await api("answer", { session_id: session!.id, question_id: q.id, choice });
      setReveal(result);
      const next = await api(`sessions/${session!.id}`);
      setPending(next);
      if (next.done) track("practice_complete", { mode, kind, guest: false });
      onProgress();
    });
  }
  async function revealCloud() { if (q) await run(async () => setReveal(await api("reveal", { session_id: session!.id, question_id: q.id }))); }
  function next() { if (guest) { setIndex((i) => i + 1); setReveal(null); } else if (pending) { setSession(pending); setPending(null); setReveal(null); } }
  function reset() { setGuest(null); setSession(null); setReveal(null); setAnswers([]); setPending(null); setIndex(0); }

  if (!started) return <section className="public-panel"><span className="eyebrow">PUBLIC PRACTICE · NO ACCOUNT REQUIRED</span><h1>Build recognition,<br /><em>one example at a time.</em></h1><p>Choose a county, date, modality and focus. Guest attempts stay in this browser. {signedIn ? "Your household progress is saved to the private D1 profile." : "Household sign-in is optional and adds server-backed progress across devices."}</p><div className="public-controls"><label>Modality<select value={kind} onChange={(e) => setKind(e.target.value)}><option value="photo">Photographs</option><option value="audio">Recordings</option></select></label><label>Mode<select value={mode} onChange={(e) => setMode(e.target.value)}><option value="choice">Choose the species</option><option value="recall">Recall and self-rate</option></select></label><label>Focus<select value={focus} onChange={(e) => setFocus(e.target.value)}><option value="now">Here now</option><option value="arriving">Arriving soon</option><option value="weak">Mixed / revisit</option></select></label></div>{error && <p className="error">{error}</p>}<button className="primary" onClick={start} disabled={busy}>{busy ? "Preparing…" : `Start ${kind} practice`} <Icon type="arrow" /></button><p className="fine">Public practice uses only eligible media. Historical ranking is a preparation signal, not a forecast. No access key is needed for this exercise.{initialBird ? ` Selected bird: ${initialBird}.` : ""}</p></section>;
  if (done) {
    const summary = guest ? { recognized: answers.filter((a) => a.outcome === "correct").length, practice: answers.filter((a) => a.outcome === "incorrect").length, uncertain: answers.filter((a) => a.outcome === "uncertain").length, distinct_examples: new Set(answers.map((a) => a.asset_id)).size, missed: answers.filter((a) => a.outcome === "incorrect") } : session!.summary;
    return <section className="practice-shell"><span className="eyebrow">SESSION COMPLETE</span><h1>Take that familiarity<br /><em>into the field.</em></h1><p>{guest ? "This summary is stored only in this browser. Sign in later to use private server-backed progress." : `Saved to ${profile === "heather" ? "Heather" : "Hank"}'s private household profile.`}</p><div className="stats"><div><b>{summary.recognized}</b><span>Recognized</span></div><div><b>{summary.uncertain}</b><span>Uncertain</span></div><div><b>{summary.practice}</b><span>To revisit</span></div><div><b>{summary.distinct_examples}</b><span>Different examples</span></div></div>{summary.missed?.length > 0 && <div className="summary-list"><h2>Worth another look</h2>{summary.missed.map((row: Row, i: number) => <p key={i}><strong>{row.name || row.species_code}</strong>{row.kind ? ` · ${row.kind}` : ""}</p>)}</div>}<p className="fine">Practice results are not a mastery claim. Missing examples stay explicit; unknown media traits remain unknown.</p><div className="public-actions"><button className="primary" onClick={reset}>Start another session <Icon type="arrow" /></button><a className="secondary" href="/sources">Media credits</a></div></section>;
  }
  const currentQuestion = q;
  const answerName = reveal?.answer?.name ?? reveal?.name ?? currentQuestion?.name ?? "the source identification";
  const canAdvance = !!reveal && (mode !== "recall" || !!reveal.outcome);
  return <section className="practice-shell"><div className="session-progress"><span>{kind === "photo" ? "LOOK CLOSELY" : "LISTEN CLOSELY"} · {mode === "recall" ? "RECALL" : "CHOOSE"}</span><span>{guest ? `Guest · ${Math.min(index + 1, total)} of ${total}` : `${profile === "heather" ? "Heather" : "Hank"} · ${(session?.answered ?? 0) + 1} of ${total}`}</span></div>{!currentQuestion ? <p className="loading">Preparing the next example…</p> : <><div className="practice-media">{currentQuestion.kind === "photo" ? <img src={currentQuestion.media_url} alt="Bird identification exercise" /> : <audio src={currentQuestion.media_url} controls preload="metadata" />}</div>{currentQuestion.bbox && <p className="fine">A source annotation is present; it is not a verified field mark.</p>}{currentQuestion.credit && <Credit asset={currentQuestion.credit} />}{!reveal && mode === "recall" && <button className="primary" onClick={() => guest ? setReveal({ answer: { name: currentQuestion.name, code: currentQuestion.answer_code } }) : revealCloud()}>Reveal the source identification</button>}{reveal && <div className="feedback"><h2>{reveal.outcome === "correct" ? "Recognized." : reveal.outcome === "uncertain" ? "Recorded as uncertain." : reveal.outcome === "incorrect" ? "A useful miss." : "Source identification"}</h2><p>{reveal.feedback || `The source identification is ${answerName}.`}</p>{mode === "recall" && !guest && !reveal.outcome && <div className="public-actions"><button className="primary" onClick={() => answer("known")} disabled={busy}>I recalled it</button><button className="secondary" onClick={() => answer("incorrect")} disabled={busy}>Needs practice</button></div>}{mode === "recall" && guest && !reveal.outcome && <div className="public-actions"><button className="primary" onClick={() => { const attempt = { species_code: currentQuestion.species_code, name: currentQuestion.name, asset_id: currentQuestion.asset_id, kind, mode, outcome: "correct", choice: "known" }; setAnswers((rows) => [...rows, attempt]); addGuest(attempt); setReveal({ outcome: "correct", answer: { name: currentQuestion.name } }); }}>I recalled it</button><button className="secondary" onClick={() => { const attempt = { species_code: currentQuestion.species_code, name: currentQuestion.name, asset_id: currentQuestion.asset_id, kind, mode, outcome: "incorrect", choice: "incorrect" }; setAnswers((rows) => [...rows, attempt]); addGuest(attempt); setReveal({ outcome: "incorrect", answer: { name: currentQuestion.name } }); }}>Needs practice</button></div>}{canAdvance && <button className="primary" onClick={next}>Next example <Icon type="arrow" /></button>}</div>}{!reveal && mode === "choice" && <div className="choice-grid">{(currentQuestion.options ?? []).map((option: Row) => <button key={option.code} onClick={() => answer(option.code)} disabled={busy}>{option.name}</button>)}</div>}{!reveal && mode === "choice" && <div className="public-actions"><button className="secondary" onClick={() => answer("unknown")} disabled={busy}>Not sure yet</button><button className="secondary" onClick={() => answer("insufficient")} disabled={busy}>Media is insufficient</button></div>}{error && <p className="error">{error}</p>}</>}</section>;
}

function ProgressView({ signedIn, progress, profile }: { signedIn: boolean; progress: Row | null; profile: string }) {
  const [guest, setGuest] = useState<Row[]>([]);
  useEffect(() => { setGuest(readGuest()); }, [signedIn]);
  if (!signedIn) {
    const recognized = guest.filter((a) => a.outcome === "correct").length; const distinct = new Set(guest.map((a) => a.asset_id)).size;
    const bySpecies = new Map<string, Row[]>(); for (const a of guest) { const key = a.name ?? a.species_code; bySpecies.set(key, [...(bySpecies.get(key) ?? []), a]); }
    return <section className="progress"><span className="eyebrow">GUEST NOTEBOOK · THIS BROWSER ONLY</span><h1>A little familiarity,<br /><em>kept locally.</em></h1><p>Guest practice history lives in this browser’s localStorage. It is not sent to BirdAhead. Sign in as a household learner to keep progress on the server across devices.</p><div className="guest-history"><div><b>{guest.length}</b><span>practice answers</span></div><div><b>{recognized}</b><span>recognized</span></div><div><b>{distinct}</b><span>different examples</span></div></div>{guest.length ? <><h2>Bird by bird</h2><div className="bird-list">{[...bySpecies.entries()].map(([name, rows]) => <div className="bird-row" key={name}><div><strong>{name}</strong><small>{rows.length} attempt{rows.length === 1 ? "" : "s"} · {rows.filter((r) => r.outcome === "correct").length} recognized</small></div><div>{rows[rows.length - 1]?.kind === "photo" ? "By sight" : "By sound"}</div></div>)}</div></> : <div className="empty small"><h2>Your public notebook is empty.</h2><p>Start a photo or audio exercise without signing in. Clearing site data removes this local history.</p></div>}<p className="fine">Guest results are not a mastery claim and never enter the household D1 history unless you choose to sign in.</p></section>;
  }
  return <section className="progress"><span className="eyebrow">PRIVATE HOUSEHOLD NOTEBOOK</span><h1>A growing sense<br /><em>of recognition.</em></h1><p>Progress belongs to {profile === "heather" ? "Heather" : "Hank"}. Sight and sound are tracked separately. Public practice never writes to this private history.</p><div className="stats"><div><b>{progress?.attempts ?? 0}</b><span>Practice answers</span></div><div><b>{progress?.distinct_examples ?? 0}</b><span>Different examples</span></div><div><b>{progress?.flags?.length ?? 0}</b><span>Examples flagged</span></div></div>{progress?.by_species?.length ? <><h2>Bird by bird</h2><div className="bird-list">{progress.by_species.map((s: Row) => <div className="bird-row" key={s.code + s.kind}><div><strong>{s.name}</strong><small>{s.kind === "photo" ? "By sight" : "By sound"} · {s.label}</small></div><div>{s.recognized} / {s.attempts} recognized<small>{s.distinct_examples} different examples</small></div></div>)}</div></> : <div className="empty small"><h2>A clean page in your field notebook.</h2><p>Start a private practice session while signed in.</p></div>}<p className="fine">Recall is self-rated. Repeated examples do not prove mastery. Flagged examples are excluded from progress for both household learners.</p></section>;
}

function About() {
  return <section className="page public-panel" style={{ maxWidth: 900 }}><span className="eyebrow">ABOUT BIRDAHEAD</span><h1>A free field companion,<br /><em>not a certification.</em></h1><p>BirdAhead is a personally motivated, noncommercial birding resource for southwestern Indiana. Public seasonal exploration, the field guide, licensed media and guest practice are free. Household sign-in is optional and only protects private progress and administration.</p><h2>What the numbers mean</h2><p>Historical seasonal ranks use owner-supplied 2016–2025 eBird county histograms. They describe the fraction of complete checklists reporting a species in a period, not abundance, encounter probability or a forecast. Arriving Soon is a 14–28 day rise signal, not a promise.</p><h2>Media and data</h2><p>Public photographs and recordings are accepted source records under CC0, CC BY, CC BY-SA, CC BY-NC or CC BY-NC-SA licenses. Creator, source URL, exact license and attribution travel with every object. NonCommercial and ShareAlike obligations remain. We do not publish raw eBird exports, exact observation coordinates or restricted media.</p><div className="public-actions"><a className="secondary" href="/sources">Sources, rights and limits</a><a className="secondary" href="/privacy">Privacy notice</a><a className="secondary" href="/robots.txt">Robots</a><a className="secondary" href="/sitemap.xml">Sitemap</a></div><h2>Administration</h2><p>Publishing, release activation, household identities and private learning histories are authenticated or operator-only. There is no public account registration, advertising or monetization.</p></section>;
}


function App() {
  const initial = useMemo(() => new URLSearchParams(window.location.search), []);
  const initialTab = (initial.get("tab") ?? "explore") as Tab;
  const [tab, setTab] = useState<Tab>(["explore", "guide", "practice", "downloads", "roadtrip", "progress", "about"].includes(initialTab) ? initialTab : "explore");
  const [auth, setAuth] = useState<Auth>("checking");
  const [profile, setProfile] = useState("hank");
  const [authName, setAuthName] = useState("");
  const [boot, setBoot] = useState<Row | null>(null);
  const [ranked, setRanked] = useState<Row[]>([]);
  const [arriving, setArriving] = useState<Row[]>([]);
  const [progress, setProgress] = useState<Row | null>(null);
  const [county, setCounty] = useState(initial.get("county") ?? localStorage.getItem("birdahead-county") ?? "");
  const [day, setDay] = useState(today());
  const [focusCode, setFocusCode] = useState(initial.get("bird") ?? "");
  const [practiceKind, setPracticeKind] = useState(initial.get("kind") ?? "photo");
  const [loginOpen, setLoginOpen] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    fetch("/api/public/bootstrap", { credentials: "same-origin" }).then(async (r) => { if (!r.ok) throw Error((await r.json().catch(() => ({}))).error ?? "Public catalog unavailable"); return r.json(); })
      .then((d) => { setBoot(d); localStorage.setItem("birdahead-boot-v1", JSON.stringify(d)); setCounty((current) => current && d.counties?.[current] ? current : Object.keys(d.counties ?? {})[0] ?? ""); })
      .catch((e) => { try { const cached = localStorage.getItem("birdahead-boot-v1"); if (cached) { const d = JSON.parse(cached); setBoot(d); setCounty((current) => current && d.counties?.[current] ? current : Object.keys(d.counties ?? {})[0] ?? ""); return; } } catch { /* use the network error below */ } setError(e.message); });
  }, []);
  useEffect(() => {
    fetch("/api/session", { credentials: "same-origin" }).then(async (r) => { if (!r.ok) { setAuth("guest"); return; } const d = await r.json(); setAuth("in"); setProfile(d.profile_id ?? "hank"); setAuthName(d.name ?? d.profile_id ?? "Learner"); }).catch(() => setAuth("guest"));
    const expired = () => { setAuth("guest"); setAuthName(""); setProfile("hank"); };
    window.addEventListener("birdahead-auth-expired", expired);
    return () => window.removeEventListener("birdahead-auth-expired", expired);
  }, []);
  useEffect(() => {
    if (auth !== "in") return;
    const sync = () => {
      if (!navigator.onLine) return;
      syncOfflineAttempts(profile).catch((error) => {
        if ((error as { status?: number }).status === 401) window.dispatchEvent(new Event("birdahead-auth-expired"));
      });
    };
    sync();
    window.addEventListener("online", sync);
    return () => window.removeEventListener("online", sync);
  }, [auth, profile]);
  useEffect(() => {
    if (!county) return;
    const path = auth === "in" ? `curriculum?profile=${encodeURIComponent(profile)}&location=${encodeURIComponent(county)}&day=${day}` : `public/curriculum?location=${encodeURIComponent(county)}&day=${day}`;
    api(path).then((d) => { setRanked(d.priorities ?? []); setArriving(d.arriving_soon ?? (d.priorities ?? []).filter((r: Row) => (r.approaching_window_rise ?? 0) > 0).sort((a: Row, b: Row) => (b.approaching_window_rise ?? 0) - (a.approaching_window_rise ?? 0)).slice(0, 25)); localStorage.setItem("birdahead-county", county); localStorage.setItem(`birdahead-curriculum-v1:${county}:${day}:${auth === "in" ? profile : "guest"}`, JSON.stringify(d)); }).catch((e) => { try { const cached = localStorage.getItem(`birdahead-curriculum-v1:${county}:${day}:${auth === "in" ? profile : "guest"}`); if (cached) { const d = JSON.parse(cached); setRanked(d.priorities ?? []); setArriving(d.arriving_soon ?? []); return; } } catch { /* show the network error */ } setError(e.message); });
  }, [county, day, auth, profile]);
  useEffect(() => { if (auth !== "in") { setProgress(null); return; } api(`progress?profile=${encodeURIComponent(profile)}`).then(setProgress).catch(() => setProgress(null)); }, [auth, profile, county, day]);
  useEffect(() => { const params = new URLSearchParams(); params.set("tab", tab); if (county) params.set("county", county); if (focusCode) params.set("bird", focusCode); window.history.replaceState(null, "", "/?" + params.toString()); }, [tab, county, focusCode]);
  function signOut() { api("logout", {}).catch(() => undefined).finally(() => { setAuth("guest"); setAuthName(""); setProfile("hank"); setProgress(null); setTab("explore"); }); }
  function openBird(code: string) { setFocusCode(code); setTab("guide"); track("species_view", { code }); }
  function startFromGuide(kind: string) { setPracticeKind(kind); setTab("practice"); }
  if (!boot) return <main className="login-shell"><p className="loading">{error || "Opening the public field guide…"}</p>{error && <a className="secondary" href="/">Retry</a>}</main>;

  return <>
    <header className="topbar"><a className="brand" href="/" onClick={(e) => { e.preventDefault(); setTab("explore"); }}><span className="brandmark"><Icon type="bird" /></span><span>BirdAhead<small>LEARN WHAT’S NEXT</small></span></a><div className="profile"><span className="profile-guest">{auth === "in" ? `${authName || profile} · household` : "Public visitor"}</span>{auth === "in" ? <button className="text-button sign-out" onClick={signOut}>Sign out</button> : <button className="signin-trigger" onClick={() => setLoginOpen(true)}>Household sign in</button>}</div></header>
    <main><nav className="tabs" aria-label="Main navigation">{[["explore", "Explore"], ["guide", "Field guide"], ["practice", "Practice"], ["downloads", "Downloads"], ["roadtrip", "Road trip"], ["progress", "Progress"], ["about", "About"]].map(([value, label]) => <button key={value} className={tab === value ? "active" : ""} onClick={() => setTab(value as Tab)}>{label}</button>)}</nav>
      {error && <p className="error">{error}</p>}
      {tab === "explore" && <Explore boot={boot} ranked={ranked} arriving={arriving} county={county} day={day} setCounty={setCounty} setDay={setDay} openBird={openBird} onPractice={() => setTab("practice")} />}
      {tab === "guide" && <Guide boot={boot} county={county} day={day} signedIn={auth === "in"} profile={profile} focusCode={focusCode} onPractice={startFromGuide} />}
      {tab === "practice" && <Practice signedIn={auth === "in"} profile={profile} county={county} day={day} initialKind={practiceKind} initialBird={focusCode} onProgress={() => { if (auth === "in") api(`progress?profile=${encodeURIComponent(profile)}`).then(setProgress).catch(() => undefined); }} />}
      {tab === "downloads" && <Downloads boot={boot} county={county} day={day} signedIn={auth === "in"} profile={profile} />}
      {tab === "roadtrip" && <RoadTrip boot={boot} county={county} day={day} signedIn={auth === "in"} profile={profile} progress={progress} setCounty={setCounty} setDay={setDay} />}
      {tab === "progress" && <ProgressView signedIn={auth === "in"} progress={progress} profile={profile} />}
      {tab === "about" && <About />}
      <footer><div className="brand"><Icon type="bird" />BirdAhead</div><p>Learn the birds you're about to meet.</p><span>Public noncommercial educational project · eBird-derived seasonal summaries and licensed media<br />Household sign-in optional · <a href="/sources">Sources</a> · <a href="/privacy">Privacy</a> · <a href="/robots.txt">Robots</a></span></footer>
    </main>
    {loginOpen && <LoginModal onClose={() => setLoginOpen(false)} onLogin={(id, name) => { setProfile(id); setAuthName(name); setAuth("in"); setLoginOpen(false); setTab("explore"); }} />}
  </>;
}
createRoot(document.getElementById("root")!).render(<App />);
if ("serviceWorker" in navigator) window.addEventListener("load", () => { navigator.serviceWorker.register("/sw.js").catch(() => undefined); });
