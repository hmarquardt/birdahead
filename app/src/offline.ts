/** Offline learning storage and sync.
 *
 * Media is stored once in Cache Storage by its public media URL. Pack metadata
 * and queue records live in IndexedDB, so removing one pack only deletes an
 * asset when no other pack still references it.
 */

export type OfflinePackKind = "county-day" | "here-now" | "arriving-soon" | "photos" | "audio" | "complete";

export interface OfflineAsset {
  id: string; kind: "photo" | "audio"; species_code: string; media_url: string;
  bytes: number; sha256: string; content_type: string; duration_seconds?: number | null;
  creator?: string | null; attribution?: string | null; source_url?: string | null;
  license_url?: string | null; license_code?: string | null; source?: string | null;
  vocalization?: string | null; target_bbox_xyxy?: number[] | null;
  public_license_notice?: string | null; public_noncommercial_only?: boolean | null;
  public_share_alike?: boolean | null; validation?: string | null;
}
export interface OfflineSpecies {
  code: string; name: string; scientific_name?: string; priority_rank?: number | null;
  current_reporting_frequency?: number | null; approaching_window_rise?: number | null;
  assets: OfflineAsset[];
}
export interface OfflineCatalog { release_id: string; county: string; day: string; species: OfflineSpecies[]; }
export interface OfflinePackDefinition {
  id: string; title: string; description: string; release_id: string;
  county: string; day: string; created_at: string; assetIds: string[];
  assets: OfflineAsset[]; species: Array<Pick<OfflineSpecies, "code" | "name" | "scientific_name">>;
  bytes: number; roadTrip?: RoadTripPlan;
}
export interface StoredPack extends OfflinePackDefinition {
  status: "downloading" | "complete" | "incomplete";
  completed_assets: string[]; updated_at: string;
}
export interface OfflineQuestion {
  id: string; asset_id: string; species_code: string; name: string;
  kind: "photo" | "audio"; media_url: string;
  options: Array<{ code: string; name: string }>; credit: Partial<OfflineAsset>; bbox: number[] | null;
}
export interface OfflineAttempt {
  event_id: string; profile_id: string | null; release_id: string; session_id: string;
  asset_id: string; species_code: string; kind: "photo" | "audio";
  mode: "choice" | "recall"; choice: string;
  outcome: "correct" | "incorrect" | "uncertain"; at: string;
  synced?: boolean; sync_error?: string | null;
}
export interface OfflineProgress {
  pack_id: string; completed: number; total: number; bytes_done: number; bytes_total: number;
}
export interface OfflineListening {
  event_id: string; profile_id: string | null; pack_id: string; release_id: string;
  at: string; minutes: number; exercises_completed: number; focus: string;
}
export type RoadTripMinutes = 10 | 20 | 30 | 60;
export type RoadTripFocus = "common" | "here" | "arriving" | "mixed" | "weak";
export type RoadTripInterval = 5 | 10 | 15 | 20 | 30 | 45 | 60;
export type RoadTripOrder = "sequential" | "shuffled";
export type RoadTripMode = "quiz" | "listen";
export interface RoadTripConfig {
  minutes: RoadTripMinutes; county: string; day: string; focus: RoadTripFocus;
  interval_seconds: RoadTripInterval; order: RoadTripOrder; mode: RoadTripMode;
}
export interface RoadTripSegment {
  kind: "recording" | "silence" | "narration";
  url: string; text?: string; exercise: number; species_code?: string;
  asset_id?: string; duration_seconds?: number | null;
}
export interface RoadTripExercise {
  id: string; species_code: string; name: string;
  recordings: OfflineAsset[]; name_url: string; name_text: string;
}
export interface RoadTripPlan { config: RoadTripConfig; exercises: RoadTripExercise[]; segments: RoadTripSegment[]; }
export interface NarrationManifest {
  schema: string; voice: string;
  files: Record<string, { bytes: number; sha256: string; content_type: string; duration_seconds?: number }>;
}

const DB_NAME = "birdahead-offline-v1";
const ASSET_CACHE = "birdahead-pack-assets-v1";
const STORE_PACKS = "packs";
const STORE_QUEUE = "queue";
const STORE_ATTEMPTS = "attempts";
const STORE_LISTENING = "listening";
const DB_VERSION = 2;

export const PACK_LABELS: Record<OfflinePackKind, { title: string; description: string }> = {
  "county-day": { title: "County outing", description: "Here Now and Arriving Soon for the selected county and date." },
  "here-now": { title: "Here Now", description: "Birds with historical reporting signal for the selected date." },
  "arriving-soon": { title: "Arriving Soon", description: "Birds with a 14–28 day rise signal." },
  photos: { title: "Photo identification", description: "Every eligible public photograph." },
  audio: { title: "Audio identification", description: "Every eligible public recording." },
  complete: { title: "Complete eligible collection", description: "Every public photograph and recording in this release." },
};

function uniqAssets(species: OfflineSpecies[]): OfflineAsset[] {
  const seen = new Set<string>(); const out: OfflineAsset[] = [];
  for (const row of species) for (const asset of row.assets ?? []) {
    if (seen.has(asset.id)) continue;
    seen.add(asset.id); out.push(asset);
  }
  return out;
}
function assetBytes(assets: OfflineAsset[]): number {
  return assets.reduce((sum, asset) => sum + Math.max(0, Number(asset.bytes) || 0), 0);
}
function speciesFor(species: OfflineSpecies[], assets: OfflineAsset[]) {
  const ids = new Set(assets.map((asset) => asset.id));
  return species.filter((row) => row.assets.some((asset) => ids.has(asset.id)))
    .map((row) => ({ code: row.code, name: row.name, scientific_name: row.scientific_name }));
}
function definition(kind: OfflinePackKind, catalog: OfflineCatalog, species: OfflineSpecies[]): OfflinePackDefinition {
  const assets = uniqAssets(species); const label = PACK_LABELS[kind];
  return {
    id: kind, title: label.title, description: label.description,
    release_id: catalog.release_id, county: catalog.county, day: catalog.day,
    created_at: new Date().toISOString(), assetIds: assets.map((asset) => asset.id),
    assets, species: speciesFor(species, assets), bytes: assetBytes(assets),
  };
}


/** Plan the six reviewed packs from one public catalog snapshot. Shared media
 * is counted once inside each pack and is stored once on the device. */
export function planOfflinePacks(catalog: OfflineCatalog): OfflinePackDefinition[] {
  const all = catalog.species.filter((row) => (row.assets ?? []).length > 0);
  const here = catalog.species.filter((row) => (row.current_reporting_frequency ?? 0) > 0 && (row.assets ?? []).length > 0);
  const arriving = catalog.species.filter((row) => (row.approaching_window_rise ?? 0) > 0 && (row.assets ?? []).length > 0);
  const county = [...new Map([...here, ...arriving].map((row) => [row.code, row])).values()];
  const photos = all.map((row) => ({ ...row, assets: row.assets.filter((asset) => asset.kind === "photo") })).filter((row) => row.assets.length);
  const audio = all.map((row) => ({ ...row, assets: row.assets.filter((asset) => asset.kind === "audio") })).filter((row) => row.assets.length);
  return [
    definition("county-day", catalog, county.length ? county : all),
    definition("here-now", catalog, here),
    definition("arriving-soon", catalog, arriving),
    definition("photos", catalog, photos),
    definition("audio", catalog, audio),
    definition("complete", catalog, all),
  ];
}
export function newBytesForPack(pack: OfflinePackDefinition, existing: OfflinePackDefinition[]): number {
  const owned = new Set(existing.flatMap((row) => row.assetIds));
  return pack.assets.filter((asset) => !owned.has(asset.id)).reduce((sum, asset) => sum + Math.max(0, Number(asset.bytes) || 0), 0);
}
export function sharedAssetCount(pack: OfflinePackDefinition, existing: OfflinePackDefinition[]): number {
  const owned = new Set(existing.flatMap((row) => row.assetIds));
  return pack.assetIds.filter((id) => owned.has(id)).length;
}
export function formatBytes(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes <= 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"]; let value = bytes; let unit = 0;
  while (value >= 1024 && unit < units.length - 1) { value /= 1024; unit += 1; }
  return `${value >= 10 || unit === 0 ? value.toFixed(0) : value.toFixed(1)} ${units[unit]}`;
}
export function cacheKeyForAsset(asset: OfflineAsset): string { return asset.media_url; }
export async function sha256Bytes(bytes: ArrayBuffer): Promise<string> {
  const digest = await crypto.subtle.digest("SHA-256", bytes);
  return [...new Uint8Array(digest)].map((byte) => byte.toString(16).padStart(2, "0")).join("");
}

function idb(): Promise<IDBDatabase> {
  if (typeof indexedDB === "undefined") return Promise.reject(new Error("Offline storage is unavailable in this browser."));
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains(STORE_PACKS)) db.createObjectStore(STORE_PACKS, { keyPath: "id" });
      if (!db.objectStoreNames.contains(STORE_QUEUE)) db.createObjectStore(STORE_QUEUE, { keyPath: "event_id" });
      if (!db.objectStoreNames.contains(STORE_ATTEMPTS)) db.createObjectStore(STORE_ATTEMPTS, { keyPath: "event_id" });
      if (!db.objectStoreNames.contains(STORE_LISTENING)) db.createObjectStore(STORE_LISTENING, { keyPath: "event_id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error ?? new Error("Could not open offline storage."));
  });
}
function requestResult<T>(request: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => { request.onsuccess = () => resolve(request.result); request.onerror = () => reject(request.error); });
}
async function storeGet<T>(store: string, key: string): Promise<T | undefined> {
  const db = await idb();
  return requestResult(db.transaction(store, "readonly").objectStore(store).get(key) as IDBRequest<T | undefined>);
}
async function storeAll<T>(store: string): Promise<T[]> {
  const db = await idb();
  return requestResult(db.transaction(store, "readonly").objectStore(store).getAll() as IDBRequest<T[]>);
}
async function storePut(store: string, value: unknown): Promise<void> {
  const db = await idb(); const tx = db.transaction(store, "readwrite"); tx.objectStore(store).put(value);
  await new Promise<void>((resolve, reject) => { tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); });
}
async function storeDelete(store: string, key: string): Promise<void> {
  const db = await idb(); const tx = db.transaction(store, "readwrite"); tx.objectStore(store).delete(key);
  await new Promise<void>((resolve, reject) => { tx.oncomplete = () => resolve(); tx.onerror = () => reject(tx.error); tx.onabort = () => reject(tx.error); });
}
export async function listPacks(): Promise<StoredPack[]> {
  return (await storeAll<StoredPack>(STORE_PACKS)).sort((a, b) => a.title.localeCompare(b.title));
}
export async function getPack(id: string): Promise<StoredPack | undefined> { return storeGet<StoredPack>(STORE_PACKS, id); }
export async function listQueue(profileId?: string | null): Promise<OfflineAttempt[]> {
  const rows = await storeAll<OfflineAttempt>(STORE_QUEUE);
  return profileId === undefined ? rows : rows.filter((row) => row.profile_id === profileId);
}
export async function listOfflineAttempts(profileId?: string | null): Promise<OfflineAttempt[]> {
  const rows = await storeAll<OfflineAttempt>(STORE_ATTEMPTS);
  return profileId === undefined ? rows : rows.filter((row) => row.profile_id === profileId);
}
export async function listListening(profileId?: string | null): Promise<OfflineListening[]> {
  const rows = await storeAll<OfflineListening>(STORE_LISTENING);
  return profileId === undefined ? rows : rows.filter((row) => row.profile_id === profileId);
}
export async function recordListening(input: {
  profile_id: string | null; pack_id: string; release_id: string; minutes: number; exercises_completed: number; focus: string;
}): Promise<OfflineListening> {
  const event: OfflineListening = {
    event_id: `listening:${crypto.randomUUID()}`, profile_id: input.profile_id, pack_id: input.pack_id,
    release_id: input.release_id, at: new Date().toISOString(), minutes: input.minutes,
    exercises_completed: input.exercises_completed, focus: input.focus,
  };
  await storePut(STORE_LISTENING, event);
  return event;
}
export async function storageEstimate(): Promise<{ usage: number; quota: number } | null> {
  if (typeof navigator === "undefined" || !navigator.storage?.estimate) return null;
  const estimate = await navigator.storage.estimate();
  return { usage: Number(estimate.usage ?? 0), quota: Number(estimate.quota ?? 0) };
}
export async function requestPersistentStorage(): Promise<boolean> {
  try { return !!(await navigator.storage?.persist?.()); } catch { return false; }
}
async function openAssetCache(): Promise<Cache> {
  if (typeof caches === "undefined") throw new Error("Offline media storage is unavailable in this browser.");
  return caches.open(ASSET_CACHE);
}
async function validCached(cache: Cache, asset: OfflineAsset): Promise<boolean> {
  const response = await cache.match(cacheKeyForAsset(asset));
  if (!response) return false;
  if (response.headers.get("X-BirdAhead-SHA256") !== asset.sha256) return false;
  if (Number(response.headers.get("Content-Length") ?? 0) !== Number(asset.bytes)) return false;
  return true;
}
async function putAsset(cache: Cache, asset: OfflineAsset, bytes: ArrayBuffer): Promise<void> {
  const headers = new Headers({
    "Content-Type": asset.content_type || "application/octet-stream",
    "Content-Length": String(bytes.byteLength), "X-BirdAhead-SHA256": asset.sha256,
    "Cache-Control": "public, max-age=31536000, immutable",
  });
  await cache.put(cacheKeyForAsset(asset), new Response(bytes, { status: 200, headers }));
}


/** Download/resume one pack. Completed assets are persisted after every file,
 * so an interrupted tab or connection resumes with the missing assets. */
export async function downloadPack(
  pack: OfflinePackDefinition,
  onProgress?: (progress: OfflineProgress) => void,
  signal?: AbortSignal,
  fetcher: typeof fetch = fetch,
): Promise<StoredPack> {
  const existing = await getPack(pack.id);
  const completed = new Set(existing?.completed_assets ?? []);
  const cache = await openAssetCache(); const total = pack.assets.length; const bytesTotal = pack.bytes;
  let bytesDone = pack.assets.filter((asset) => completed.has(asset.id)).reduce((sum, asset) => sum + asset.bytes, 0);
  const persist = async (status: StoredPack["status"]) => {
    const state: StoredPack = { ...pack, status, completed_assets: [...completed], updated_at: new Date().toISOString() };
    await storePut(STORE_PACKS, state);
    onProgress?.({ pack_id: pack.id, completed: completed.size, total, bytes_done: bytesDone, bytes_total: bytesTotal });
    return state;
  };
  await persist("downloading");
  for (const asset of pack.assets) {
    if (signal?.aborted) throw new DOMException("Download paused.", "AbortError");
    if (completed.has(asset.id) && await validCached(cache, asset)) continue;
    if (completed.has(asset.id)) completed.delete(asset.id);
    const response = await fetcher(asset.media_url, { credentials: "same-origin", cache: "no-store", signal });
    if (!response.ok) throw new Error(`Could not download ${asset.id} (${response.status}).`);
    const bytes = await response.arrayBuffer();
    if (bytes.byteLength !== Number(asset.bytes)) throw new Error(`The download size for ${asset.id} did not match the catalog.`);
    if (await sha256Bytes(bytes) !== asset.sha256) throw new Error(`The download integrity check failed for ${asset.id}.`);
    await putAsset(cache, asset, bytes);
    completed.add(asset.id); bytesDone += asset.bytes;
    await persist("downloading");
  }
  return persist("complete");
}
/** Remove references, then reclaim only assets no remaining pack needs. */
export async function deletePack(id: string): Promise<number> {
  await storeDelete(STORE_PACKS, id);
  const remaining = await listPacks();
  const neededPaths = new Set(remaining.flatMap((pack) => pack.assets.map((asset) => new URL(asset.media_url, typeof location === "undefined" ? "http://localhost" : location.origin).pathname)));
  const removed = new Set<string>();
  if (typeof caches !== "undefined") {
    const cache = await caches.open(ASSET_CACHE);
    for (const request of await cache.keys()) {
      const url = new URL(request.url);
      if ((url.pathname.startsWith("/media/public/") || url.pathname.startsWith("/narration/")) && !neededPaths.has(url.pathname)) {
        await cache.delete(request); removed.add(url.pathname);
      }
    }
  }
  return removed.size;
}
export async function missingAssets(pack: StoredPack): Promise<string[]> {
  const cache = await openAssetCache(); const missing: string[] = [];
  for (const asset of pack.assets) if (!(await validCached(cache, asset))) missing.push(asset.id);
  return missing;
}
export async function verifyInstalledPack(pack: StoredPack): Promise<boolean> {
  return (await missingAssets(pack)).length === 0;
}


export function offlineQuestions(
  packs: Array<{ assets: OfflineAsset[]; species: Array<Pick<OfflineSpecies, "code" | "name">> }>,
  kind: "photo" | "audio", attempts: OfflineAttempt[] = [], limit = 10, random: () => number = Math.random,
): OfflineQuestion[] {
  const byAsset = new Map<string, OfflineAsset>();
  for (const pack of packs) for (const asset of pack.assets) if (asset.kind === kind && asset.media_url.startsWith("/media/public/")) byAsset.set(asset.id, asset);
  const species = new Map<string, string>();
  for (const pack of packs) for (const row of pack.species) species.set(row.code, row.name);
  const weak = new Map<string, number>(); const seen = new Map<string, number>();
  for (const attempt of attempts) {
    seen.set(attempt.asset_id, (seen.get(attempt.asset_id) ?? 0) + 1);
    if (attempt.outcome !== "correct") weak.set(attempt.species_code, (weak.get(attempt.species_code) ?? 0) + 1);
  }
  const pool = [...byAsset.values()].sort((a, b) =>
    (weak.get(b.species_code) ?? 0) - (weak.get(a.species_code) ?? 0)
    || (seen.get(a.id) ?? 0) - (seen.get(b.id) ?? 0) || a.id.localeCompare(b.id));
  const codes = [...new Set(pool.map((asset) => asset.species_code))];
  return pool.slice(0, limit).map((asset) => {
    const options = [asset.species_code, ...codes.filter((code) => code !== asset.species_code).sort(() => random() - 0.5).slice(0, 3)];
    return {
      id: `q:${crypto.randomUUID()}`, asset_id: asset.id, species_code: asset.species_code,
      name: species.get(asset.species_code) ?? asset.species_code, kind,
      media_url: cacheKeyForAsset(asset), options: options.sort(() => random() - 0.5).map((code) => ({ code, name: species.get(code) ?? code })),
      credit: asset, bbox: asset.target_bbox_xyxy ?? null,
    };
  });
}
function guestHistoryAppend(attempt: OfflineAttempt, name: string): void {
  try {
    if (typeof localStorage === "undefined") return;
    const key = "birdahead-guest-history-v1";
    const rows = JSON.parse(localStorage.getItem(key) ?? "[]") as unknown[];
    rows.push({ species_code: attempt.species_code, name, asset_id: attempt.asset_id, kind: attempt.kind, mode: attempt.mode, outcome: attempt.outcome, choice: attempt.choice, at: attempt.at });
    localStorage.setItem(key, JSON.stringify(rows.slice(-500)));
  } catch { /* optional */ }
}
/** Record a local event and, for a signed-in learner, a profile-bound queue row. */
export async function recordOfflineAttempt(input: {
  profile_id: string | null; release_id: string; question: OfflineQuestion; choice: string; mode: "choice" | "recall";
}): Promise<OfflineAttempt> {
  const outcome: OfflineAttempt["outcome"] = input.choice === "unknown" || input.choice === "insufficient" ? "uncertain"
    : input.mode === "recall" ? (input.choice === "known" ? "correct" : "incorrect")
    : input.choice === input.question.species_code ? "correct" : "incorrect";
  const at = new Date().toISOString();
  const attempt: OfflineAttempt = {
    event_id: `offline:${crypto.randomUUID()}`, profile_id: input.profile_id, release_id: input.release_id,
    session_id: `offline:${crypto.randomUUID()}`, asset_id: input.question.asset_id, species_code: input.question.species_code,
    kind: input.question.kind, mode: input.mode, choice: input.choice, outcome, at, synced: false, sync_error: null,
  };
  await storePut(STORE_ATTEMPTS, attempt);
  if (input.profile_id) await storePut(STORE_QUEUE, attempt); else guestHistoryAppend(attempt, input.question.name);
  return attempt;
}
export async function syncOfflineAttempts(profileId: string, fetcher: typeof fetch = fetch): Promise<{ accepted: number; duplicates: number; rejected: number }> {
  const queue = await listQueue(profileId);
  if (!queue.length) return { accepted: 0, duplicates: 0, rejected: 0 };
  const response = await fetcher("/api/offline/sync", {
    method: "POST", credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-BirdAhead-Request": "1" },
    body: JSON.stringify({ profile_id: profileId, attempts: queue.map((row) => ({ event_id: row.event_id, asset_id: row.asset_id, kind: row.kind, mode: row.mode, choice: row.choice, at: row.at, release_id: row.release_id })) }),
  });
  if (response.status === 401) throw Object.assign(new Error("Sign in again to sync offline practice."), { status: 401 });
  const body = await response.json().catch(() => ({})) as { accepted?: string[]; duplicates?: string[]; rejected?: Array<{ event_id: string; code: string }>; error?: string };
  if (!response.ok) throw new Error(body.error ?? "Offline sync failed.");
  const accepted = body.accepted ?? []; const duplicates = body.duplicates ?? []; const rejected = body.rejected ?? [];
  const remove = new Set([...accepted, ...duplicates, ...rejected.map((row) => row.event_id)]);
  for (const eventId of remove) {
    const attempt = await storeGet<OfflineAttempt>(STORE_ATTEMPTS, eventId);
    await storeDelete(STORE_QUEUE, eventId);
    if (attempt) await storePut(STORE_ATTEMPTS, { ...attempt, synced: accepted.includes(eventId) || duplicates.includes(eventId), sync_error: rejected.find((row) => row.event_id === eventId)?.code ?? null });
  }
  return { accepted: accepted.length, duplicates: duplicates.length, rejected: rejected.length };
}

