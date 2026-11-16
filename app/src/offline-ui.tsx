import React, { useEffect, useMemo, useRef, useState } from "react";
import {
  deletePack, downloadPack, formatBytes, listOfflineAttempts, listPacks, listQueue,
  newBytesForPack, offlineQuestions, planOfflinePacks, planSelectionPack, recordOfflineAttempt,
  requestPersistentStorage, sharedAssetCount, storageEstimate, syncOfflineAttempts,
  type OfflineAsset, type OfflineAttempt, type OfflinePackDefinition,
  type OfflineProgress, type OfflineQuestion, type StoredPack,
} from "./offline";
import { OfflinePractice } from "./offline-practice";

type Row = Record<string, any>;

async function publicGet(path: string): Promise<Row> {
  const response = await fetch("/api/public/" + path, { credentials: "same-origin" });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error ?? "The public catalog is unavailable.");
  return data;
}
function hasOfflineIdentity(asset: Row): asset is OfflineAsset {
  return typeof asset.id === "string" && (asset.kind === "photo" || asset.kind === "audio")
    && typeof asset.sha256 === "string" && /^[a-f0-9]{64}$/.test(asset.sha256)
    && Number(asset.bytes) > 0 && typeof asset.media_url === "string";
}
function catalogFrom(library: Row, county: string, day: string) {
  return { release_id: String(library.release_id ?? ""), county, day,
    species: (library.species ?? []).map((row: Row) => ({
      code: String(row.code), name: String(row.name), scientific_name: row.scientific_name, confusion_pair: row.confusion_pair ?? null,
      current_reporting_frequency: row.current_reporting_frequency ?? null,
      approaching_window_rise: row.approaching_window_rise ?? null,
      assets: (row.assets ?? []).filter(hasOfflineIdentity),
    })) };
}
export function OfflineCredit({ asset }: { asset: Partial<OfflineAsset> }) {
  return <div className="credit"><p>© {asset.creator || "Unknown creator"} · <a href={asset.source_url ?? undefined} target="_blank" rel="noreferrer">Original record ↗</a> · <a href={asset.license_url ?? undefined} target="_blank" rel="noreferrer">{asset.license_code || "License"} ↗</a></p>{asset.attribution && <p>{asset.attribution}</p>}{asset.public_license_notice && <p>{asset.public_license_notice}</p>}</div>;
}

function PackCard({ pack, stored, existing, progress, onDownload, onDelete, onPause, busy }: {
  pack: OfflinePackDefinition; stored?: StoredPack; existing: OfflinePackDefinition[];
  progress?: OfflineProgress; onDownload: (pack: OfflinePackDefinition) => void;
  onDelete: (id: string) => void; onPause: () => void; busy: boolean;
}) {
  const complete = stored?.status === "complete";
  const downloading = stored?.status === "downloading";
  const incremental = newBytesForPack(pack, existing.filter((row) => row.id !== pack.id));
  const shared = sharedAssetCount(pack, existing.filter((row) => row.id !== pack.id));
  const done = progress?.pack_id === pack.id ? progress : stored ? { completed: stored.completed_assets.length, total: pack.assets.length, bytes_done: 0, bytes_total: pack.bytes } : null;
  return <article className="download-card">
    <div className="download-head"><div><span className="eyebrow">{pack.assets.length} files · {formatBytes(pack.bytes)}</span><h3>{pack.title}</h3></div>{complete && <span className="download-status">Downloaded</span>}</div>
    <p>{pack.description}</p>
    <dl className="download-facts"><div><dt>New data</dt><dd>{formatBytes(incremental)}</dd></div><div><dt>Shared</dt><dd>{shared} file{shared === 1 ? "" : "s"}</dd></div><div><dt>Release</dt><dd>{pack.release_id.slice(0, 12)}…</dd></div></dl>
    {!pack.assets.length && <p className="fine">No eligible media for this pack in the current selection.</p>}
    {done && done.total > 0 && !complete && <div className="download-progress"><div style={{ width: `${Math.min(100, (done.completed / done.total) * 100)}%` }} /><span>{done.completed} of {done.total}</span></div>}
    {complete && <p className="fine">Saved for offline use. Shared files remain until the last pack using them is removed.</p>}
    {stored && stored.release_id && <p className="fine">Content release {stored.release_id.slice(0, 12)}…</p>}
    <div className="public-actions">
      {!complete && <button className="primary" disabled={busy || !pack.assets.length} onClick={() => onDownload(pack)}>{downloading ? "Resume download" : "Download for offline"}</button>}
      {downloading && busy && <button className="secondary" disabled={!busy} onClick={onPause}>Pause download</button>}
      {complete && <button className="secondary" disabled={busy} onClick={() => onDownload(pack)}>Refresh pack</button>}
      {stored && <button className="secondary" disabled={busy} onClick={() => onDelete(pack.id)}>Remove download</button>}
    </div>
  </article>;
}

export function Downloads({ boot, county, day, signedIn, profile, focusCodes = [] }: { boot: Row; county: string; day: string; signedIn: boolean; profile: string; focusCodes?: string[] }) {
  const [library, setLibrary] = useState<Row | null>(null);
  const [packs, setPacks] = useState<OfflinePackDefinition[]>([]);
  const [stored, setStored] = useState<StoredPack[]>([]);
  const [progress, setProgress] = useState<Record<string, OfflineProgress>>({});
  const [estimate, setEstimate] = useState<{ usage: number; quota: number } | null>(null);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [syncMessage, setSyncMessage] = useState("");
  const [online, setOnline] = useState(typeof navigator === "undefined" ? true : navigator.onLine);
  const controller = useRef<AbortController | null>(null);
  async function refresh() { setStored(await listPacks()); setEstimate(await storageEstimate()); }
  function packsFor(data: Row) { const catalog = catalogFrom(data, county, day); const standard = planOfflinePacks(catalog); return focusCodes.length ? [planSelectionPack(catalog, focusCodes), ...standard] : standard; }
  useEffect(() => {
    publicGet(`library?location=${encodeURIComponent(county)}&day=${encodeURIComponent(day)}`)
      .then((data) => { localStorage.setItem("birdahead-offline-library-v1", JSON.stringify({ county, day, data })); setLibrary(data); setPacks(packsFor(data)); })
      .catch((error) => {
        try {
          const cached = JSON.parse(localStorage.getItem("birdahead-offline-library-v1") ?? "null");
          if (cached?.data && cached.county === county && cached.day === day) { setLibrary(cached.data); setPacks(packsFor(cached.data)); return; }
        } catch { /* show the network error below */ }
        setMessage((error as Error).message);
      });
  }, [county, day, focusCodes.join("|")]);
  useEffect(() => { refresh().catch((error) => setMessage((error as Error).message)); }, []);
  useEffect(() => {
    const on = () => setOnline(true); const off = () => setOnline(false);
    window.addEventListener("online", on); window.addEventListener("offline", off);
    return () => { window.removeEventListener("online", on); window.removeEventListener("offline", off); };
  }, []);
  useEffect(() => {
    if (!signedIn || !online) return;
    syncOfflineAttempts(profile).then((result) => {
      if (result.accepted || result.duplicates || result.rejected) setSyncMessage(`${result.accepted} synced${result.duplicates ? `, ${result.duplicates} already present` : ""}${result.rejected ? `, ${result.rejected} no longer available` : ""}.`);
    }).catch((error) => {
      if ((error as { status?: number }).status === 401) window.dispatchEvent(new Event("birdahead-auth-expired"));
      else setSyncMessage((error as Error).message);
    });
  }, [signedIn, online, profile]);
  function pause() { controller.current?.abort(); }
  async function startDownload(pack: OfflinePackDefinition) {
    setBusy(true); setMessage("");
    const controllerForPack = new AbortController(); controller.current = controllerForPack;
    try {
      await requestPersistentStorage();
      const currentEstimate = await storageEstimate(); setEstimate(currentEstimate);
      const needed = newBytesForPack(pack, stored);
      if (currentEstimate?.quota && currentEstimate.quota - currentEstimate.usage < needed * 1.1) throw new Error("There is not enough device storage for this pack. Remove a pack or free space and try again.");
      await downloadPack(pack, (row) => setProgress((rows) => ({ ...rows, [row.pack_id]: row })), controllerForPack.signal);
      setMessage(`${pack.title} is ready offline.`);
    } catch (error) {
      if ((error as Error).name === "AbortError") setMessage("Download paused. It can be resumed from this page.");
      else setMessage((error as Error).message);
    } finally { controller.current = null; setBusy(false); await refresh(); }
  }
  async function remove(id: string) {
    setBusy(true); setMessage("");
    try { await deletePack(id); setMessage("Download removed. Shared files still used by another pack were kept."); }
    catch (error) { setMessage((error as Error).message); }
    finally { setBusy(false); await refresh(); }
  }
  const downloaded = stored.filter((row) => row.status === "complete");
  const stale = downloaded.filter((row) => boot.release_id && row.release_id !== boot.release_id);
  const storageText = estimate ? `${formatBytes(estimate.usage)} used${estimate.quota ? ` of ${formatBytes(estimate.quota)} available` : ""}` : "Storage estimate is not available in this browser.";
  return <section className="downloads-page">
    <span className="eyebrow">OFFLINE LEARNING</span><h1>Take the field guide<br /><em>off the grid.</em></h1>
    <p>Download only what you need for an outing. Shared photographs and recordings are stored once, and a pack can be resumed after an interrupted connection. The app shell and downloaded content have separate versions, so app updates do not erase packs.</p>
    <div className="download-storage"><div><b>{storageText}</b><small>{online ? "Connected" : "Offline — downloaded packs still work"}</small></div>{stored.length > 0 && <div><b>{stored.length}</b><small>downloaded pack{stored.length === 1 ? "" : "s"}</small></div>}</div>
    {message && <p className={message.includes("ready") || message.includes("removed") ? "fine" : "error"}>{message}</p>}
    {syncMessage && <p className="fine">{syncMessage}</p>}
    {stale.length > 0 && <p className="error">A newer content release is live. Downloaded packs still work offline, but refresh them when convenient; withdrawn media remains in old packs until refreshed.</p>}

    {!library && <p className="loading">Reading the public collection…</p>}
    <div className="download-grid">{packs.map((pack) => <PackCard key={pack.id} pack={pack} stored={stored.find((row) => row.id === pack.id)} existing={downloaded} progress={progress[pack.id]} onDownload={startDownload} onDelete={remove} onPause={pause} busy={busy} />)}</div>
    <OfflinePractice stored={downloaded} signedIn={signedIn} profile={profile} onSync={async () => {
      try { const result = await syncOfflineAttempts(profile); setSyncMessage(`${result.accepted} more synced${result.duplicates ? `; ${result.duplicates} duplicate` : ""}.`); }
      catch (error) { if ((error as { status?: number }).status === 401) window.dispatchEvent(new Event("birdahead-auth-expired")); else setSyncMessage((error as Error).message); }
    }} />
    <p className="fine">Downloaded packs carry the release identifier, creator, source and license notices. Clearing site data, browser storage eviction or a changed media digest can require downloading a pack again.</p>
    <p className="fine">This prepares a future hands-free road-trip audio mode, but that mode is not part of this release.</p>
  </section>;
}
