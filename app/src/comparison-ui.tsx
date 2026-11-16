import React, { useEffect, useMemo, useState } from "react";
import {
  comparativeQuestion, recommendedPairs, seasonalOverlap, assetGaps,
  type ComparisonAsset, type ComparisonCatalog, type ComparisonPair, type ComparativeQuestion,
} from "./comparisons";
import { listComparativeAttempts, listPacks, recordComparativeAttempt, type ComparativeAttempt } from "./offline";

type Row = Record<string, any>;
const DIMENSIONS: Record<string, string> = {
  relative_size: "Relative size", shape: "Shape", plumage: "Plumage", behavior: "Behavior",
  habitat: "Habitat", vocalization: "Calls and vocalizations",
};
function assetsFor(library: Row | null, code: string): ComparisonAsset[] {
  return (library?.species ?? []).find((row: Row) => row.code === code)?.assets ?? [];
}
function displayAssets(assets: ComparisonAsset[], kind: "photo" | "audio"): ComparisonAsset[] {
  return assets.filter((asset) => asset.kind === kind).slice(0, 2);
}
function AudioCard({ asset, name }: { asset: ComparisonAsset; name: string }) {
  return <div className="compare-audio"><audio controls preload="metadata" src={asset.media_url} aria-label={`${name} recording`} /><small>© {asset.creator || "Unknown creator"} · <a href={asset.source_url ?? undefined} target="_blank" rel="noreferrer">source</a> · <a href={asset.license_url ?? undefined} target="_blank" rel="noreferrer">{asset.license_code || "license"}</a></small>{asset.public_license_notice && <small>{asset.public_license_notice}</small>}</div>;
}
function CompareColumn({ code, name, assets, side }: { code: string; name: string; assets: ComparisonAsset[]; side: "left" | "right" }) {
  const photos = displayAssets(assets, "photo"); const audio = displayAssets(assets, "audio");
  return <section className={`compare-column ${side}`} aria-labelledby={`compare-${side}`}><h2 id={`compare-${side}`}>{name}<small>{code}</small></h2>{photos.length ? <div className="compare-photos">{photos.map((asset) => <figure key={asset.id}><img src={asset.media_url} alt={`${name} accepted reference`} loading="lazy" /><figcaption>© {asset.creator || "Unknown creator"} · <a href={asset.source_url ?? undefined} target="_blank" rel="noreferrer">source</a> · <a href={asset.license_url ?? undefined} target="_blank" rel="noreferrer">{asset.license_code || "license"}</a></figcaption></figure>)}</div> : <p className="gap-label">No accepted public photograph. Coverage gap; acceptance was not weakened.</p>}{audio.length ? <div className="compare-audios">{audio.map((asset) => <AudioCard key={asset.id} asset={asset} name={name} />)}</div> : <p className="gap-label">No accepted public recording. Coverage gap; acceptance was not weakened.</p>}</section>;
}
export function Compare({ boot, county, day, signedIn, profile, progress, attempts = [], initialA = "", initialB = "" }: {
  boot: Row; county: string; day: string; signedIn: boolean; profile: string; progress: Row | null; attempts?: Array<{ species_code: string; outcome?: string }>; initialA?: string; initialB?: string;
}) {
  const [catalog, setCatalog] = useState<ComparisonCatalog | null>(null);
  const [library, setLibrary] = useState<Row | null>(null);
  const [selected, setSelected] = useState("");
  const [leftBins, setLeftBins] = useState<Row[]>([]);
  const [rightBins, setRightBins] = useState<Row[]>([]);
  const [seasonalError, setSeasonalError] = useState(false);
  const [error, setError] = useState("");
  const [kind, setKind] = useState<"photo" | "audio">("photo");
  const [question, setQuestion] = useState<ComparativeQuestion | null>(null);
  const [reveal, setReveal] = useState<ComparativeAttempt | null>(null);
  const [history, setHistory] = useState<ComparativeAttempt[]>([]);
  const [practiceMessage, setPracticeMessage] = useState("");
  useEffect(() => {
    fetch("/comparisons.json", { credentials: "same-origin" }).then((response) => response.ok ? response.json() : Promise.reject(new Error("Comparison catalog unavailable."))).then(setCatalog).catch((reason) => setError(reason.message));
    fetch(`/api/public/library?location=${encodeURIComponent(county)}&day=${encodeURIComponent(day)}`, { credentials: "same-origin" }).then((response) => response.ok ? response.json() : Promise.reject(new Error("Public media catalog unavailable."))).then(setLibrary).catch(async () => { const packs = await listPacks().catch(() => []); const rows = new Map<string, Row>(); for (const pack of packs) for (const asset of pack.assets) { if (!asset.media_url.startsWith("/media/public/")) continue; const row = rows.get(asset.species_code) ?? { code: asset.species_code, name: pack.species.find((s) => s.code === asset.species_code)?.name ?? asset.species_code, assets: [] }; row.assets.push(asset); rows.set(asset.species_code, row); } setLibrary({ species: [...rows.values()] }); setError("Comparison media catalog is using downloaded packs offline."); });
    listComparativeAttempts(signedIn ? profile : null).then(setHistory).catch(() => undefined);
  }, [county, day, signedIn, profile]);
  const pair = catalog?.pairs.find((row) => row.id === selected) ?? catalog?.pairs.find((row) => (row.left.code === initialA && row.right.code === initialB) || (row.left.code === initialB && row.right.code === initialA)) ?? null;
  const pairId = pair?.id ?? selected;
  useEffect(() => {
    if (!pair) return;
    setSeasonalError(false);
    Promise.all([
      fetch(`/api/public/seasonality?location=${encodeURIComponent(county)}&code=${encodeURIComponent(pair.left.code)}`, { credentials: "same-origin" }).then((response) => response.ok ? response.json() : { bins: [] }),
      fetch(`/api/public/seasonality?location=${encodeURIComponent(county)}&code=${encodeURIComponent(pair.right.code)}`, { credentials: "same-origin" }).then((response) => response.ok ? response.json() : { bins: [] }),
    ]).then(([left, right]) => { setLeftBins(left.bins ?? []); setRightBins(right.bins ?? []); }).catch(() => { setSeasonalError(true); setLeftBins([]); setRightBins([]); });
  }, [pairId, county]);
  const leftAssets = pair ? assetsFor(library, pair.left.code) : [];
  const rightAssets = pair ? assetsFor(library, pair.right.code) : [];
  const overlap = useMemo(() => seasonalOverlap(leftBins as any, rightBins as any), [leftBins, rightBins]);
  const pairs = catalog ? recommendedPairs(catalog, progress, [...history, ...attempts]) : [];
  const gaps = pair ? assetGaps(pair, leftAssets, rightAssets) : [];
  const currentFreq = (code: string) => (library?.species ?? []).find((row: Row) => row.code === code)?.current_reporting_frequency ?? null;
  function practice() {
    if (!pair) return;
    const next = comparativeQuestion(pair, leftAssets, rightAssets, kind, history);
    if (!next) { setQuestion(null); setReveal(null); setPracticeMessage(`No unused accepted public ${kind} example remains for this pair; the comparison remains a coverage gap rather than repeating one example.`); return; }
    setQuestion(next); setReveal(null); setPracticeMessage("");
  }
  async function answer(code: string) {
    if (!question) return;
    try {
      const row = await recordComparativeAttempt({ profile_id: signedIn ? profile : null, pair_id: question.pair_id, question: { asset_id: question.asset.id, species_code: question.species_code, kind: question.asset.kind }, choice: code });
      setReveal(row); setHistory((rows) => [...rows, row]);
    } catch (reason) { setPracticeMessage((reason as Error).message); }
  }

  if (error && !catalog) return <section className="compare-page"><p className="error">{error}</p></section>;
  return <section className="compare-page"><span className="eyebrow">COMPARATIVE LEARNING · PROVISIONAL CATALOG</span><h1>Look closer.<br /><em>Learn the difference.</em></h1><p>Compare accepted media side by side, listen to independent recordings and use cited reference summaries without treating unverified labels as field marks. Sparse evidence stays a visible gap.</p>
    <div className="compare-controls"><label>Reviewed pair<select value={pairId} onChange={(event) => setSelected(event.target.value)}><option value="">Choose a pair</option>{pairs.map((row) => <option key={row.id} value={row.id}>{row.left.name} / {row.right.name}</option>)}</select></label><label>County<select value={county} onChange={() => undefined} disabled><option>{String(boot.counties?.[county] ?? county)}</option></select></label></div>
    {catalog && <p className="fine">Catalog {catalog.version} · {catalog.review_status} · sources are cited below. {catalog.review_note}</p>}
    {!pair && <div className="compare-recommendations"><h2>Suggested comparisons</h2><p>Recommendations use existing household confusion history and local comparative practice; they are not a mastery claim.</p><div className="compare-pair-list">{pairs.map((row) => <button key={row.id} className="secondary" onClick={() => { setSelected(row.id); setQuestion(null); setReveal(null); }}><strong>{row.left.name}</strong> ↔ <strong>{row.right.name}</strong></button>)}</div></div>}
    {pair && <><div className="compare-pair-head"><h2>{pair.left.name} <span>vs</span> {pair.right.name}</h2><a className="secondary" href={`/?tab=guide&bird=${encodeURIComponent(pair.left.code)}`}>Open field guide</a></div><div className="compare-columns"><CompareColumn code={pair.left.code} name={pair.left.name} assets={leftAssets} side="left" /><CompareColumn code={pair.right.code} name={pair.right.name} assets={rightAssets} side="right" /></div>
      <h2>Seasonal overlap in {String(boot.counties?.[county] ?? county)}</h2><div className="compare-season">{seasonalError ? <p className="gap-label">Seasonal history is unavailable offline. Comparison media and cited traits remain usable; no overlap estimate is asserted.</p> : <p><strong>{overlap.common_bins}</strong> of {overlap.total_bins} seasonal bins have both species reported in the historical profiles. Current reporting frequency: {pair.left.name} {currentFreq(pair.left.code) === null ? "unknown" : `${(currentFreq(pair.left.code)! * 100).toFixed(1)}%`}; {pair.right.name} {currentFreq(pair.right.code) === null ? "unknown" : `${(currentFreq(pair.right.code)! * 100).toFixed(1)}%`}.</p>}<p className="fine">Historical complete-checklist reporting frequency, not encounter probability. County and date: {county} · {day}.</p></div>

      <h2>Evidence-supported differences</h2><div className="compare-traits">{pair.traits.map((trait) => <div className="compare-trait" key={trait.dimension}><h3>{DIMENSIONS[trait.dimension] ?? trait.dimension}</h3><div><p><strong>{pair.left.name}</strong> {trait.left}</p><p><strong>{pair.right.name}</strong> {trait.right}</p></div><p className="fine">Sources: {trait.source_ids.map((id) => <a key={id} href={catalog?.sources[id]?.url} target="_blank" rel="noreferrer">{catalog?.sources[id]?.title ?? id}</a>)}</p></div>)}</div>
      {pair.gaps.length > 0 && <div className="compare-gaps"><h2>Evidence gaps</h2>{pair.gaps.map((gap) => <p key={gap}>{gap}</p>)}{gaps.map((gap) => <p key={gap}>{gap}</p>)}<p className="fine">No unverified age, sex or plumage label is promoted to a fact. No acceptance threshold was lowered to fill a gap.</p></div>}
      <h2>Comparative practice</h2><p>This is separate from scored identification and passive listening. It uses a different accepted example where available and records a local comparative event, never a mastery score.</p><div className="public-actions"><button className={kind === "photo" ? "primary" : "secondary"} onClick={() => setKind("photo")}>Photo comparison</button><button className={kind === "audio" ? "primary" : "secondary"} onClick={() => setKind("audio")}>Audio comparison</button><button className="secondary" onClick={practice}>Practice this pair</button></div>{question && <div className="compare-practice"><div className="practice-media">{question.asset.kind === "photo" ? <img src={question.asset.media_url} alt="Comparative identification exercise" /> : <audio controls src={question.asset.media_url} />}</div><p className="fine">Which species is this accepted example? The two choices are the reviewed pair. No hidden score is awarded.</p>{!reveal && <div className="choice-grid">{question.choices.map((choice) => <button key={choice.code} onClick={() => answer(choice.code)}>{choice.name}</button>)}</div>}{reveal && <div className="feedback"><h3>{reveal.outcome === "correct" ? "Recognized." : "Keep comparing."}</h3><p>The source identification is {reveal.species_code === pair.left.code ? pair.left.name : pair.right.name}. This comparative event is separate from progress.</p><button className="primary" onClick={practice}>Try another accepted example</button></div>}</div>}{practiceMessage && <p className="fine">{practiceMessage}</p>}
    </>}
  </section>;
}
