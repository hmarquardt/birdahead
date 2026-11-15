import React, { useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

type Row = Record<string, any>;
async function api(path: string, body?: Row) {
  const response = await fetch(
    "/api/" + path,
    body
      ? {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        }
      : undefined,
  );
  const data = await response.json();
  if (!response.ok) throw Error(data.error ?? "Request failed");
  return data;
}
const pct = (n: number | null) =>
  n === null ? "Unknown" : `${(n * 100).toFixed(1)}%`;
const points = (n: number | null) =>
  n === null ? "Unknown" : `${(n * 100).toFixed(1)} percentage points`;
const period = (r: Row) => {
  if (!r.bin_start || !r.bin_end) return "Period unavailable";
  const format = (d: Date) =>
    d.toLocaleDateString("en-US", {
      month: "short",
      day: "numeric",
      timeZone: "UTC",
    });
  return `${format(new Date(r.bin_start + "T00:00:00Z"))}–${format(new Date(Date.parse(r.bin_end + "T00:00:00Z") - 86400000))}`;
};
const today = () => {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};
function Icon({ type }: { type: "bird" | "photo" | "audio" | "arrow" }) {
  const paths = {
    bird: (
      <>
        <path d="M3 17c6 0 6-7 13-7l3-4 2 4-3 3c1 6-4 9-10 7l-4 2 2-4" />
        <path d="M9 16c2 0 4-1 5-3" />
      </>
    ),
    photo: (
      <>
        <rect x="3" y="4" width="18" height="16" rx="3" />
        <circle cx="9" cy="9" r="1.5" />
        <path d="m4 17 5-5 4 4 3-3 5 5" />
      </>
    ),
    audio: (
      <>
        <path d="M4 10v4m4-8v12m4-15v18m4-15v12m4-8v4" />
      </>
    ),
    arrow: (
      <>
        <path d="M4 12h15m-6-6 6 6-6 6" />
      </>
    ),
  };
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {paths[type]}
    </svg>
  );
}
function Credit({ data }: { data: Row }) {
  return (
    <div className="credit">
      <p>
        © {data.creator} ·{" "}
        <a href={data.source_url} target="_blank" rel="noreferrer">
          Original record ↗
        </a>{" "}
        ·{" "}
        <a href={data.license_url} target="_blank" rel="noreferrer">
          License ↗
        </a>
      </p>
      {data.attribution && <p>{data.attribution}</p>}
      <p>{data.validation}</p>
    </div>
  );
}

function App() {
  const [boot, setBoot] = useState<Row | null>(null),
    [error, setError] = useState(""),
    [tab, setTab] = useState("prepare");
  const [profile, setProfile] = useState(
    localStorage.getItem("birdahead-profile") ?? "birder-1",
  );
  const [location, setLocation] = useState(
    localStorage.getItem("birdahead-county") ?? "US-IN-051",
  );
  const [day, setDay] = useState(today()),
    [kind, setKind] = useState("photo"),
    [mode, setMode] = useState("choice"),
    [focus, setFocus] = useState("now");
  const [ranking, setRanking] = useState<Row[]>([]),
    [progress, setProgress] = useState<Row | null>(null),
    [session, setSession] = useState<Row | null>(null);
  const [reveal, setReveal] = useState<Row | null>(null),
    [recall, setRecall] = useState<Row | null>(null),
    [busy, setBusy] = useState(false),
    [seconds, setSeconds] = useState(0);
  const [flagging, setFlagging] = useState(false),
    [flagReason, setFlagReason] = useState(""),
    [flagStatus, setFlagStatus] = useState("");
  const [showTarget, setShowTarget] = useState(true),
    [natural, setNatural] = useState<[number, number]>([1, 1]);
  const [showAll, setShowAll] = useState(false);
  async function run(fn: () => Promise<void>) {
    if (busy) return;
    setBusy(true);
    setError("");
    try {
      await fn();
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setBusy(false);
    }
  }
  async function refresh() {
    const [b, r, p] = await Promise.all([
      api("bootstrap"),
      api(`curriculum?profile=${profile}&location=${location}&day=${day}`),
      api(`progress?profile=${profile}`),
    ]);
    setBoot(b);
    setRanking(r.priorities);
    setProgress(p);
  }
  useEffect(() => {
    let active = true;
    Promise.all([
      api("bootstrap"),
      api(`curriculum?profile=${profile}&location=${location}&day=${day}`),
      api(`progress?profile=${profile}`),
    ])
      .then(([b, r, p]) => {
        if (active) {
          setBoot(b);
          setRanking(r.priorities);
          setProgress(p);
        }
      })
      .catch((e) => active && setError(e.message));
    localStorage.setItem("birdahead-profile", profile);
    localStorage.setItem("birdahead-county", location);
    return () => {
      active = false;
    };
  }, [profile, location, day]);
  useEffect(() => {
    const id = localStorage.getItem(`birdahead-session-${profile}`);
    if (id)
      api(`sessions/${id}`)
        .then((s) => {
          setSession(s);
          setTab(s.done ? "prepare" : "practice");
          setSeconds(s.elapsed_seconds);
        })
        .catch(() => localStorage.removeItem(`birdahead-session-${profile}`));
    else setSession(null);
    setReveal(null);
    setRecall(null);
  }, [profile]);
  useEffect(() => {
    if (!session || session.done) return;
    const timer = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(timer);
  }, [session?.id, session?.done]);
  useEffect(() => {
    if (seconds >= 300 && session && !session.done)
      api(`sessions/${session.id}`)
        .then((s) => {
          setSession(s);
          if (s.done) localStorage.removeItem(`birdahead-session-${profile}`);
        })
        .catch((e) => setError(e.message));
  }, [seconds >= 300, session?.id]);
  const ordered = [...ranking].sort((a, b) =>
    focus === "arriving"
      ? (b.approaching_window_rise ?? -1) - (a.approaching_window_rise ?? -1)
      : focus === "weak"
        ? b.needs_practice - a.needs_practice
        : 0,
  );
  const available = ordered.filter(
    (r) =>
      r[kind === "photo" ? "photo" : "audio"] &&
      (focus === "weak" ||
        (focus === "arriving"
          ? (r.approaching_window_rise ?? 0) > 0
          : (r.current_reporting_frequency ?? 0) > 0)),
  );
  async function start() {
    await run(async () => {
      const s = await api("sessions", {
        profile,
        location,
        day,
        kind,
        mode,
        focus,
      });
      setSession(s);
      setSeconds(0);
      setReveal(null);
      setRecall(null);
      setFlagStatus("");
      setTab("practice");
      localStorage.setItem(`birdahead-session-${profile}`, s.id);
    });
  }
  async function answer(choice: string) {
    await run(async () => {
      const result = await api("answer", {
        session_id: session!.id,
        question_id: session!.question.id,
        choice,
      });
      setReveal(result);
      await refresh();
    });
  }
  async function next() {
    await run(async () => {
      const s = await api(`sessions/${session!.id}`);
      setSession(s);
      setSeconds(s.elapsed_seconds);
      setReveal(null);
      setRecall(null);
      setFlagStatus("");
      setFlagging(false);
      if (s.done) {
        localStorage.removeItem(`birdahead-session-${profile}`);
        await refresh();
      }
    });
  }
  async function flag() {
    await run(async () => {
      const result = await api("flag", {
        profile,
        asset_id: session!.question.asset_id,
        session_id: session!.id,
        reason: flagReason,
      });
      setFlagStatus(result.status);
      setFlagging(false);
      setFlagReason("");
      await refresh();
    });
  }
  const q = session?.question,
    shown = reveal ?? recall;
  const ready = boot !== null;
  return (
    <>
      <header className="topbar">
        <a
          className="brand"
          href="#"
          onClick={(e) => {
            e.preventDefault();
            setTab("prepare");
          }}
        >
          <span className="brandmark">
            <Icon type="bird" />
          </span>
          <span>
            BirdAhead<small>LEARN WHAT’S NEXT</small>
          </span>
        </a>
        <div className="profile">
          <span className="avatar">{profile === "birder-1" ? "01" : "02"}</span>
          <label className="sr-only" htmlFor="learner">
            Learner
          </label>
          <select
            id="learner"
            value={profile}
            onChange={(e) => setProfile(e.target.value)}
          >
            {(
              boot?.profiles ?? [
                { id: "birder-1", name: "Birder 1" },
                { id: "birder-2", name: "Birder 2" },
              ]
            ).map((p: Row) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
      </header>
      <main>
        <nav className="tabs" aria-label="Main navigation">
          {[
            ["prepare", "Your next outing"],
            ["practice", "Practice"],
            ["progress", "Your progress"],
          ].map(([id, label]) => (
            <button
              key={id}
              className={tab === id ? "active" : ""}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
        {error && (
          <div className="error" role="alert">
            {error}
            <button onClick={() => setError("")} aria-label="Dismiss error">
              ×
            </button>
          </div>
        )}
        {!ready ? (
          <p className="loading">Finding your birds…</p>
        ) : (
          <>
            {tab === "prepare" && (
              <>
                <section className="intro">
                  <div className="eyebrow">
                    A LITTLE PRACTICE. A BETTER DAY OUT.
                  </div>
                  <h1>
                    Meet the birds
                    <br />
                    <em>before you go.</em>
                  </h1>
                  <p>
                    Build your eye. Tune your ear. Get ready for what’s around
                    the bend.
                  </p>
                </section>
                <section className="outing" aria-label="Plan an outing">
                  <label>
                    WHERE YOU’RE HEADED
                    <select
                      id="county"
                      value={location}
                      onChange={(e) => setLocation(e.target.value)}
                    >
                      {Object.entries(boot.counties).map(([code, name]) => (
                        <option key={code} value={code}>
                          {String(name)} County, Indiana
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    WHEN YOU’RE GOING
                    <input
                      id="outing-day"
                      type="date"
                      value={day}
                      onChange={(e) => setDay(e.target.value)}
                    />
                  </label>
                  <span className="place-note">
                    Seven counties.
                    <br />A whole year of birds.
                  </span>
                </section>
                <div className="section-title">
                  <div>
                    <span className="eyebrow">YOUR FIELD NOTES</span>
                    <h2>Ahead of your outing</h2>
                  </div>
                  <span className="subtle">
                    Based on 2016–2025 eBird checklists
                  </span>
                </div>
                <div className="focus-grid">
                  {[
                    [
                      "now",
                      "01",
                      "Here now",
                      "Build familiarity with birds reported around your outing date.",
                    ],
                    [
                      "arriving",
                      "02",
                      "Arriving soon",
                      "Look two to four weeks ahead, even before birds are reported now.",
                    ],
                    [
                      "weak",
                      "03",
                      "A little reinforcement",
                      "Revisit the birds and sounds you’ve found tricky.",
                    ],
                  ].map(([id, num, title, desc]) => (
                    <button
                      key={id}
                      className={`focus-card ${focus === id ? "selected" : ""}`}
                      onClick={() => setFocus(id)}
                      aria-pressed={focus === id}
                    >
                      <span>{num}</span>
                      <h3>{title}</h3>
                      <p>{desc}</p>
                      <i>
                        Explore <Icon type="arrow" />
                      </i>
                    </button>
                  ))}
                </div>
                <section className="learning">
                  <div>
                    <span className="eyebrow">MAKE FIVE MINUTES COUNT</span>
                    <h2>
                      {focus === "arriving"
                        ? "Get a little ahead."
                        : focus === "weak"
                          ? "Turn hesitation into recognition."
                          : "A few birds closer to familiar."}
                    </h2>
                    <p>
                      Practice with different examples. Leave room for “I’m not
                      sure.”
                    </p>
                    <div
                      className="segmented"
                      aria-label="Identification modality"
                    >
                      <button
                        className={kind === "photo" ? "selected" : ""}
                        onClick={() => setKind("photo")}
                      >
                        <Icon type="photo" />
                        By sight <small>{boot.coverage.photo} species</small>
                      </button>
                      <button
                        className={kind === "audio" ? "selected" : ""}
                        onClick={() => setKind("audio")}
                      >
                        <Icon type="audio" />
                        By sound <small>{boot.coverage.audio} species</small>
                      </button>
                    </div>
                    <label className="practice-mode">
                      Practice style{" "}
                      <select
                        value={mode}
                        onChange={(e) => setMode(e.target.value)}
                      >
                        <option value="choice">Choose an answer</option>
                        <option value="recall">Recall, then reveal</option>
                      </select>
                    </label>
                    <button
                      className="primary"
                      onClick={start}
                      disabled={busy || available.length < 1}
                    >
                      Start a five-minute session <Icon type="arrow" />
                    </button>
                    <p className="fine">
                      Up to 10 examples · Your own progress · Media already on
                      this computer
                    </p>
                  </div>
                  <div className="deck-peek">
                    <span className="eyebrow">IN YOUR PRACTICE MIX</span>
                    {available.slice(0, 5).map((r, i) => (
                      <div key={r.species_code}>
                        <span className="deck-number">
                          {String(i + 1).padStart(2, "0")}
                        </span>
                        <span>
                          {r.name}
                          <small>
                            {focus === "arriving"
                              ? `Reporting rise ${points(r.approaching_window_rise)} over 2–4 weeks`
                              : `${pct(r.current_reporting_frequency)} of complete checklists`}
                          </small>
                        </span>
                      </div>
                    ))}
                    {available.length === 0 && (
                      <p>
                        No accepted multi-example coverage for these settings.
                      </p>
                    )}
                  </div>
                </section>
                <section className="seasonal">
                  <div className="section-title">
                    <h2>The seasonal picture</h2>
                    <span className="pill">
                      {boot.counties[location]} County
                    </span>
                  </div>
                  <p>
                    All 25 pilot species remain visible here. Practice includes
                    species with at least two accepted examples in the selected
                    modality.
                  </p>
                  <div className="bird-list">
                    {ordered.slice(0, showAll ? 25 : 10).map((r) => (
                      <div className="bird-row" key={r.species_code}>
                        <div>
                          <strong>{r.name}</strong>
                          <small>
                            {r[kind === "photo" ? "photo" : "audio"]
                              ? "In this practice collection"
                              : "More media needed"}
                          </small>
                        </div>
                        <div className="frequency">
                          <span>{pct(r.current_reporting_frequency)}</span>
                          <div className="bar">
                            <i
                              style={{
                                width: `${(r.current_reporting_frequency ?? 0) * 100}%`,
                              }}
                            />
                          </div>
                        </div>
                        <div className="support">
                          <span>{r.sample_size ?? "—"} checklists</span>
                          <small>{period(r)} · reporting period</small>
                        </div>
                        {r.approaching_window_rise > 0.05 && (
                          <span className="arrival">↗ Ahead</span>
                        )}
                      </div>
                    ))}
                  </div>
                  <button
                    className="text-button"
                    onClick={() => setShowAll((v) => !v)}
                  >
                    {showAll
                      ? "Show fewer birds"
                      : "Show all 25 pilot species →"}
                  </button>
                  <p className="fine">
                    {boot.limitations} Unknown values stay unknown. A reporting
                    rise is a preparation signal, not a forecast of a particular
                    outing.
                  </p>
                </section>
              </>
            )}
            {tab === "practice" && (
              <section className="practice">
                {!session ? (
                  <div className="empty">
                    <Icon type="bird" />
                    <h1>Your next familiar bird starts here.</h1>
                    <p>Choose a place, a date and a way to practice.</p>
                    <button
                      className="primary"
                      onClick={() => setTab("prepare")}
                    >
                      Prepare a session <Icon type="arrow" />
                    </button>
                  </div>
                ) : session.done ? (
                  <div className="session-end">
                    <span className="eyebrow">A FEW MINUTES WELL SPENT</span>
                    <h1>
                      Take that familiarity
                      <br />
                      <em>into the field.</em>
                    </h1>
                    <div className="stats">
                      <div>
                        <b>{session.summary.recognized}</b>
                        <span>
                          {session.mode === "recall"
                            ? "Self-recalled"
                            : "Recognized"}
                        </span>
                      </div>
                      <div>
                        <b>{session.summary.uncertain}</b>
                        <span>Left uncertain</span>
                      </div>
                      <div>
                        <b>{session.summary.practice}</b>
                        <span>To revisit</span>
                      </div>
                    </div>
                    <p>
                      These are practice results, not a mastery claim. Different
                      examples help build a transferable skill.
                    </p>
                    <button
                      className="primary"
                      onClick={() => setTab("prepare")}
                    >
                      Plan your next session <Icon type="arrow" />
                    </button>
                  </div>
                ) : (
                  q && (
                    <>
                      <div className="practice-heading">
                        <div>
                          <span className="eyebrow">
                            {session.kind === "photo"
                              ? "LOOK CLOSELY"
                              : "LISTEN CLOSELY"}
                          </span>
                          <h1>Who’s this?</h1>
                        </div>
                        <div>
                          <span className="pill">
                            {session.answered + 1} / {session.total}
                          </span>
                          <p className="fine">
                            {Math.floor(Math.max(0, 300 - seconds) / 60)}:
                            {String(
                              Math.floor(Math.max(0, 300 - seconds) % 60),
                            ).padStart(2, "0")}{" "}
                            left
                          </p>
                        </div>
                      </div>
                      <div className="quiz-layout">
                        <div className="example">
                          {q.kind === "photo" ? (
                            <>
                              <div className="photo-wrap">
                                <img
                                  key={q.asset_id}
                                  src={q.media_url}
                                  alt="Bird identification practice example"
                                  onLoad={(e) =>
                                    setNatural([
                                      e.currentTarget.naturalWidth,
                                      e.currentTarget.naturalHeight,
                                    ])
                                  }
                                />
                                {q.bbox && showTarget && (
                                  <div
                                    className="target-box"
                                    style={{
                                      left: `${(q.bbox[0] / natural[0]) * 100}%`,
                                      top: `${(q.bbox[1] / natural[1]) * 100}%`,
                                      width: `${((q.bbox[2] - q.bbox[0]) / natural[0]) * 100}%`,
                                      height: `${((q.bbox[3] - q.bbox[1]) / natural[1]) * 100}%`,
                                    }}
                                  />
                                )}
                              </div>
                              {q.bbox && (
                                <label className="target-toggle">
                                  <input
                                    type="checkbox"
                                    checked={showTarget}
                                    onChange={(e) =>
                                      setShowTarget(e.target.checked)
                                    }
                                  />{" "}
                                  Show target bird outline
                                </label>
                              )}
                            </>
                          ) : (
                            <div className="audio-example">
                              <Icon type="audio" />
                              <h2>A voice from the field</h2>
                              <p>Listen as often as you like.</p>
                              <audio
                                key={q.asset_id}
                                src={q.media_url}
                                controls
                                preload="metadata"
                              />
                            </div>
                          )}
                          <p className="fine">
                            Original licensed media. No generated birds or
                            sounds.
                          </p>
                          <details className="credit">
                            <summary>Source, attribution & license</summary>
                            <Credit data={q.credit} />
                          </details>
                        </div>
                        <div className="answers">
                          {!shown && session.mode === "choice" && (
                            <>
                              <span className="eyebrow">
                                WHAT DO YOU RECOGNIZE?
                              </span>
                              {q.options.map((o: Row) => (
                                <button
                                  disabled={busy}
                                  className="answer-option"
                                  key={o.code}
                                  onClick={() => answer(o.code)}
                                >
                                  {o.name}
                                  <span>↗</span>
                                </button>
                              ))}
                              <div className="uncertain">
                                <button
                                  disabled={busy}
                                  onClick={() => answer("unknown")}
                                >
                                  I’m not sure
                                </button>
                                <button
                                  disabled={busy}
                                  onClick={() => answer("insufficient")}
                                >
                                  Not enough information
                                </button>
                              </div>
                            </>
                          )}
                          {!shown && session.mode === "recall" && (
                            <>
                              <h2>Say the name to yourself.</h2>
                              <p>
                                Look or listen for a moment, then reveal the
                                source identification.
                              </p>
                              <button
                                className="primary"
                                disabled={busy}
                                onClick={() =>
                                  run(async () =>
                                    setRecall(
                                      await api("reveal", {
                                        session_id: session.id,
                                        question_id: q.id,
                                      }),
                                    ),
                                  )
                                }
                              >
                                Reveal identification
                              </button>
                            </>
                          )}
                          {shown && (
                            <div className="reveal" aria-live="polite">
                              <span className="eyebrow">
                                {reveal
                                  ? reveal.outcome === "correct"
                                    ? "A LITTLE MORE FAMILIAR"
                                    : reveal.outcome === "uncertain"
                                      ? "ROOM TO BE UNSURE"
                                      : "ONE TO REVISIT"
                                  : "SOURCE IDENTIFICATION"}
                              </span>
                              <h2>{shown.answer.name}</h2>
                              <i>{shown.answer.scientific_name}</i>
                              {shown.credit.vocalization && (
                                <p>{shown.credit.vocalization}</p>
                              )}
                              <Credit data={shown.credit} />
                              {shown.note && <p>{shown.note}</p>}
                              {recall && !reveal ? (
                                <>
                                  <p>How did your recall go?</p>
                                  <div className="recall-rating">
                                    <button
                                      className="primary"
                                      onClick={() => answer("known")}
                                      disabled={busy}
                                    >
                                      I recalled it
                                    </button>
                                    <button
                                      onClick={() => answer("unknown")}
                                      disabled={busy}
                                    >
                                      I wasn’t sure
                                    </button>
                                    <button
                                      onClick={() => answer("insufficient")}
                                      disabled={busy}
                                    >
                                      Not enough information
                                    </button>
                                  </div>
                                </>
                              ) : (
                                <button
                                  className="primary"
                                  disabled={busy}
                                  onClick={next}
                                >
                                  Next example <Icon type="arrow" />
                                </button>
                              )}
                            </div>
                          )}
                          <button
                            className="flag-link"
                            onClick={() => setFlagging((v) => !v)}
                          >
                            ⚑ Flag a possible identification or media issue
                          </button>
                          {flagging && (
                            <form
                              className="flag-form"
                              onSubmit={(e) => {
                                e.preventDefault();
                                flag();
                              }}
                            >
                              <label>
                                What seems wrong?
                                <textarea
                                  required
                                  maxLength={2000}
                                  value={flagReason}
                                  onChange={(e) =>
                                    setFlagReason(e.target.value)
                                  }
                                  placeholder="Identification, more than one bird, unclear sound…"
                                />
                              </label>
                              <button disabled={busy} type="submit">
                                Flag and hide this example
                              </button>
                            </form>
                          )}
                          {flagStatus && (
                            <div role="status" className="flag-status">
                              {flagStatus}
                              <button onClick={next}>
                                Continue practice →
                              </button>
                            </div>
                          )}
                        </div>
                      </div>
                      <button
                        className="text-button"
                        onClick={() => setTab("prepare")}
                      >
                        ← Back to outing preparation
                      </button>
                    </>
                  )
                )}
              </section>
            )}
            {tab === "progress" && (
              <section className="progress">
                <span className="eyebrow">YOUR OWN PACE</span>
                <h1>
                  A growing sense
                  <br />
                  <em>of recognition.</em>
                </h1>
                <p>
                  Progress belongs to{" "}
                  {boot.profiles.find((p: Row) => p.id === profile)?.name}.
                  Sight and sound are tracked separately.
                </p>
                <div className="stats">
                  <div>
                    <b>{progress?.attempts ?? 0}</b>
                    <span>Practice answers</span>
                  </div>
                  <div>
                    <b>{progress?.distinct_examples ?? 0}</b>
                    <span>Different examples</span>
                  </div>
                  <div>
                    <b>{progress?.flags.length ?? 0}</b>
                    <span>Examples flagged</span>
                  </div>
                </div>
                {progress?.by_species.length ? (
                  <>
                    <h2>Bird by bird</h2>
                    <div className="bird-list">
                      {progress.by_species.map((s: Row) => (
                        <div className="bird-row" key={s.code + s.kind}>
                          <div>
                            <strong>{s.name}</strong>
                            <small>
                              {s.kind === "photo" ? "By sight" : "By sound"} ·{" "}
                              {s.label}
                            </small>
                          </div>
                          <div>
                            {s.recognized} / {s.attempts} recognized
                            <small>
                              {s.distinct_examples} different examples
                            </small>
                          </div>
                        </div>
                      ))}
                    </div>
                    <h2>Easy to mix up</h2>
                    {progress.confusion.length ? (
                      progress.confusion.map((c: Row) => (
                        <p key={c.species_code + c.choice + c.kind}>
                          {c.from} → {c.to}{" "}
                          <span className="pill">
                            {c.count} {c.count === 1 ? "time" : "times"} ·{" "}
                            {c.kind}
                          </span>
                        </p>
                      ))
                    ) : (
                      <p>No recorded confusion pairs yet.</p>
                    )}
                  </>
                ) : (
                  <div className="empty small">
                    <h2>A clean page in your field notebook.</h2>
                    <p>Your practice will appear here, one bird at a time.</p>
                    <button
                      className="primary"
                      onClick={() => setTab("prepare")}
                    >
                      Find your first session <Icon type="arrow" />
                    </button>
                  </div>
                )}
                <p className="fine">
                  Recall is self-rated. Repeated examples do not prove mastery.
                  Flagged examples are excluded from these results for both
                  learners.
                </p>
              </section>
            )}
          </>
        )}
        <footer>
          <div className="brand">
            <Icon type="bird" />
            BirdAhead
          </div>
          <p>Learn the birds you’re about to meet.</p>
          <span>
            Local recreational pilot · eBird / Cornell Lab of Ornithology
            <br />
            Personal noncommercial collection · No cloud sync
          </span>
        </footer>
      </main>
    </>
  );
}
createRoot(document.getElementById("root")!).render(<App />);
