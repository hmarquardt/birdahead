import React, { useEffect, useMemo, useState } from "react";
import { OfflineCredit } from "./offline-ui";
import {
  listOfflineAttempts, listQueue, offlineQuestions, recordOfflineAttempt,
  type OfflineAttempt, type OfflineQuestion, type StoredPack,
} from "./offline";

export function OfflinePractice({ stored, signedIn, profile, onSync }: {
  stored: StoredPack[]; signedIn: boolean; profile: string; onSync: () => Promise<void>;
}) {
  const [kind, setKind] = useState<"photo" | "audio">("photo");
  const [mode, setMode] = useState<"choice" | "recall">("choice");
  const [questions, setQuestions] = useState<OfflineQuestion[]>([]);
  const [index, setIndex] = useState(0);
  const [reveal, setReveal] = useState<OfflineAttempt | null>(null);
  const [revealed, setRevealed] = useState(false);
  const [answers, setAnswers] = useState<OfflineAttempt[]>([]);
  const [queueCount, setQueueCount] = useState(0);
  const [error, setError] = useState("");
  const [missing, setMissing] = useState<Record<string, boolean>>({});
  const available = useMemo(() => ["photo", "audio"].map((value) => ({
    value: value as "photo" | "audio",
    count: stored.reduce((sum, pack) => sum + pack.assets.filter((asset) => asset.kind === value).length, 0),
  })), [stored]);
  useEffect(() => {
    if (signedIn) listQueue(profile).then((rows) => setQueueCount(rows.length)).catch(() => undefined);
  }, [signedIn, profile]);
  const current = questions[index] ?? null;
  const done = questions.length > 0 && index >= questions.length;
  async function start() {
    setError(""); setReveal(null); setRevealed(false); setAnswers([]); setIndex(0);
    try {
      const prior = await listOfflineAttempts(signedIn ? profile : null);
      const next = offlineQuestions(stored, kind, prior, 10);
      if (!next.length) throw new Error(`No downloaded ${kind === "photo" ? "photographs" : "recordings"} are available. Download a pack first.`);
      setQuestions(next);
    } catch (err) { setError((err as Error).message); }
  }
  async function answer(choice: string) {
    if (!current) return;
    try {
      const attempt = await recordOfflineAttempt({ profile_id: signedIn ? profile : null, release_id: stored[0]?.release_id ?? "unknown", question: current, choice, mode });
      setAnswers((rows) => [...rows, attempt]); setReveal(attempt); setRevealed(true);
      if (signedIn) setQueueCount((await listQueue(profile)).length);
    } catch (err) { setError((err as Error).message); }
  }
  function next() {
    if (index + 1 >= questions.length) { setIndex(questions.length); setReveal(null); setRevealed(false); return; }
    setIndex(index + 1); setReveal(null); setRevealed(false);
  }
  function reset() { setQuestions([]); setAnswers([]); setReveal(null); setRevealed(false); setIndex(0); }
  const recognized = answers.filter((row) => row.outcome === "correct").length;
  const incorrect = answers.filter((row) => row.outcome === "incorrect").length;
  const uncertain = answers.filter((row) => row.outcome === "uncertain").length;
  if (!stored.length) return <section className="offline-practice empty small"><h2>Offline practice unlocks after a download.</h2><p>Choose a photo or audio pack above. The app can then launch without a connection and use only the media you saved.</p></section>;
  if (done) return <section className="offline-practice"><span className="eyebrow">OFFLINE SESSION SUMMARY</span><h2>{recognized} recognized, {incorrect} to revisit.</h2><div className="stats"><div><b>{answers.length}</b><span>Answers</span></div><div><b>{recognized}</b><span>Recognized</span></div><div><b>{uncertain}</b><span>Uncertain</span></div><div><b>{new Set(answers.map((row) => row.asset_id)).size}</b><span>Examples</span></div></div><p>{signedIn ? `These answers are queued for ${profile === "heather" ? "Heather" : "Hank"} and sync only while that profile is signed in.` : "These answers stay in this browser and never enter a household profile."}</p>{signedIn && <button className="primary" onClick={onSync}>Sync offline answers</button>}<div className="public-actions"><button className="primary" onClick={reset}>Start another offline session</button></div><p className="fine">Recall and choice results are practice signals, not a mastery claim. Download packs carry their release identifier; a later content release may withdraw an example.</p></section>;
  if (!current) return <section className="offline-practice"><span className="eyebrow">OFFLINE PRACTICE</span><h2>Practice from your downloaded packs.</h2><p>No account is needed. A signed-in learner can queue answers for private sync when the connection returns.</p><div className="public-actions">{available.map((row) => <button key={row.value} className={kind === row.value ? "primary" : "secondary"} disabled={!row.count} onClick={() => setKind(row.value)}>{row.value === "photo" ? "Photo identification" : "Audio identification"} · {row.count}</button>)}</div><div className="public-actions"><button className={mode === "choice" ? "primary" : "secondary"} onClick={() => setMode("choice")}>Choose an answer</button><button className={mode === "recall" ? "primary" : "secondary"} onClick={() => setMode("recall")}>Recall and reveal</button></div><button className="primary" onClick={start}>Start offline practice</button>{signedIn && queueCount > 0 && <p className="fine">{queueCount} answer{queueCount === 1 ? "" : "s"} waiting to sync.</p>}{error && <p className="error">{error}</p>}</section>;
  return <section className="offline-practice"><div className="session-progress"><span>{kind === "photo" ? "OFFLINE · LOOK CLOSELY" : "OFFLINE · LISTEN CLOSELY"} · {mode === "recall" ? "RECALL" : "CHOOSE"}</span><span>{index + 1} of {questions.length}</span></div><div className="practice-media">{current.kind === "photo" ? <img src={current.media_url} alt="Offline bird identification exercise" onError={() => setMissing((rows) => ({ ...rows, [current.asset_id]: true }))} /> : <audio src={current.media_url} controls preload="metadata" onError={() => setMissing((rows) => ({ ...rows, [current.asset_id]: true }))} />}</div>{missing[current.asset_id] && <p className="error">This downloaded example is missing or was evicted from browser storage. Reconnect and download the pack again.</p>}<OfflineCredit asset={current.credit} />{!revealed && mode === "choice" && <div className="choice-grid">{current.options.map((option) => <button key={option.code} onClick={() => answer(option.code)}>{option.name}</button>)}</div>}{!revealed && mode === "choice" && <div className="public-actions"><button className="secondary" onClick={() => answer("unknown")}>Not sure yet</button><button className="secondary" onClick={() => answer("insufficient")}>Media is insufficient</button></div>}{!revealed && mode === "recall" && <div className="public-actions"><button className="primary" onClick={() => setRevealed(true)}>Reveal the source identification</button></div>}{revealed && <div className="feedback"><h2>{reveal?.outcome === "correct" ? "Recognized." : reveal?.outcome === "uncertain" ? "Recorded as uncertain." : reveal?.outcome === "incorrect" ? "A useful miss." : "Source identification"}</h2><p>{`The source identification is ${current.name}.`}</p>{mode === "recall" && !reveal?.outcome && <div className="public-actions"><button className="primary" onClick={() => answer("known")}>I recalled it</button><button className="secondary" onClick={() => answer("incorrect")}>Needs practice</button></div>}{reveal?.outcome && <button className="primary" onClick={next}>Next offline example</button>}</div>}{error && <p className="error">{error}</p>}</section>;
}
